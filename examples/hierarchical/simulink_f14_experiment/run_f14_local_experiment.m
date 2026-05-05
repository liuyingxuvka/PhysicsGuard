function run_f14_local_experiment()
%RUN_F14_LOCAL_EXPERIMENT Copy and run MATLAB's local f14 Simulink example.
%
% This is a local experiment, not a PhysicsGuard Simulink adapter. It copies
% the built-in f14 example to this directory, modifies only the copied model,
% logs a small set of system/subsystem/controller signals, and writes a JSON
% snapshot consumed by build_physicsguard_audits.py.

rootDir = fileparts(mfilename('fullpath'));
modelsDir = fullfile(rootDir, 'models');
outputsDir = fullfile(rootDir, 'outputs');
if ~exist(modelsDir, 'dir')
    mkdir(modelsDir);
end
if ~exist(outputsDir, 'dir')
    mkdir(outputsDir);
end

baselinePath = fullfile(modelsDir, 'f14_pg_baseline.slx');
faultPath = fullfile(modelsDir, 'f14_pg_fault_gain2_sign.slx');

openExample('simulink/AddBlockFromAnotherModelExample', 'supportingFile', 'f14');
cleanup = onCleanup(@() localCloseIfLoaded('f14'));
save_system('f14', baselinePath);
localCloseIfLoaded('f14_pg_baseline');
clear cleanup;
copyfile(baselinePath, faultPath, 'f');

nominalKq = 0.8156;
faultKq = -nominalKq;

baseline = localRunAndCollect(baselinePath, 'f14_pg_baseline', nominalKq);
fault = localRunAndCollect(faultPath, 'f14_pg_fault_gain2_sign', faultKq);

snapshot = struct();
snapshot.experiment = 'simulink_f14_progressive_bughunt';
snapshot.model_source = 'MATLAB built-in f14 example copied locally';
snapshot.fault_description = 'Controller/Gain2 pitch-rate feedback gain sign reversed in copied model.';
snapshot.nominal_Kq = nominalKq;
snapshot.fault_Kq = faultKq;
snapshot.stop_time_s = 10.0;
snapshot.clean = baseline;
snapshot.fault = fault;

jsonPath = fullfile(outputsDir, 'f14_signal_snapshot.json');
fid = fopen(jsonPath, 'w');
if fid < 0
    error('Could not open JSON output path: %s', jsonPath);
end
fprintf(fid, '%s', jsonencode(snapshot, PrettyPrint=true));
fclose(fid);
fprintf('Wrote %s\n', jsonPath);
end

function result = localRunAndCollect(modelPath, modelName, gainValue)
load_system(modelPath);
cleanup = onCleanup(@() localCloseIfLoaded(modelName));

set_param([modelName '/Controller/Gain2'], 'Gain', num2str(gainValue, '%.16g'));
save_system(modelName);

set_param(modelName, 'StopTime', '10', 'SignalLogging', 'on', 'SignalLoggingName', 'logsout');

localMarkLine(modelName, 'Controller/Gain2', 'in', 1, 'pg_q_gain_input');
localMarkLine(modelName, 'Controller/Gain2', 'out', 1, 'pg_q_gain_output');
localMarkLine(modelName, 'Controller', 'out', 1, 'pg_controller_command');
localMarkLine(modelName, sprintf('Actuator\nModel'), 'out', 1, 'pg_actuator_deflection');
localMarkLine(modelName, 'alpha (rad)', 'in', 1, 'pg_alpha_rad');
localMarkLine(modelName, 'Nz Pilot (g)', 'in', 1, 'pg_nz_pilot_g');

simOut = sim(modelName, 'ReturnWorkspaceOutputs', 'on');
logs = simOut.logsout;

result = struct();
result.model_file = modelPath;
result.model_name = modelName;
result.Kq_in_model = gainValue;
result.signals = struct();
result.signals.q_gain_input_final = localFinalLoggedValue(logs, 'pg_q_gain_input');
result.signals.q_gain_output_final = localFinalLoggedValue(logs, 'pg_q_gain_output');
result.signals.controller_command_final = localFinalLoggedValue(logs, 'pg_controller_command');
result.signals.actuator_deflection_final = localFinalLoggedValue(logs, 'pg_actuator_deflection');
result.signals.alpha_rad_final = localFinalLoggedValue(logs, 'pg_alpha_rad');
result.signals.nz_pilot_g_final = localFinalLoggedValue(logs, 'pg_nz_pilot_g');
result.signals.q_gain_nominal_expected_output_final = 0.8156 * result.signals.q_gain_input_final;
result.signals.q_gain_nominal_residual_final = result.signals.q_gain_output_final - 0.8156 * result.signals.q_gain_input_final;
result.signals.q_gain_actual_residual_final = result.signals.q_gain_output_final - gainValue * result.signals.q_gain_input_final;
end

function localMarkLine(modelName, blockPath, portKind, portIndex, signalName)
ph = get_param([modelName '/' blockPath], 'PortHandles');
if strcmp(portKind, 'in')
    line = get_param(ph.Inport(portIndex), 'Line');
elseif strcmp(portKind, 'out')
    line = get_param(ph.Outport(portIndex), 'Line');
else
    error('Unknown port kind: %s', portKind);
end
if line < 0
    error('No line exists for %s %s port %d', blockPath, portKind, portIndex);
end
set_param(line, 'Name', signalName);
Simulink.sdi.markSignalForStreaming(line, 'on');
end

function value = localFinalLoggedValue(logs, signalName)
for idx = 1:logs.numElements
    element = logs.get(idx);
    if strcmp(element.Name, signalName)
        value = double(element.Values.Data(end));
        return;
    end
end
error('Logged signal not found: %s', signalName);
end

function localCloseIfLoaded(modelName)
if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
end
