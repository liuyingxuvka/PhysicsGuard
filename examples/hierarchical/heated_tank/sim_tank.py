"""Synthetic 'external simulator' for a heated water tank (ground truth, not PhysicsGuard).

Tank: area 0.5 m2, gravity outflow through an orifice, constant inflow, electric heater,
ambient loss. Fault: at t >= 600 s one of two heater elements fails, so the real heat is
half the commanded power; the exported 'heater power' column is the COMMAND (kW).
Exports non-SI columns on purpose (L/s, degC, kW) to exercise signal mapping.
"""
import csv, math, sys
out = sys.argv[1]
fault = sys.argv[2] if len(sys.argv) > 2 else "heater_half"
A, rho, cp, g = 0.5, 1000.0, 4186.0, 9.81
CdA = 0.001 / math.sqrt(2 * g * 1.0)
UA, eta, Vsup = 20.0, 0.98, 400.0
dt, N = 10.0, 120
h, T = 1.0, 300.0
rows = []
for k in range(N + 1):
    t = k * dt
    Vin = 0.001 if t < 900 else 0.0006         # inflow step at 900 s (second operating point)
    Tin = 288.15
    Tamb = 293.15
    Pcmd = 20000.0
    frac = 0.5 if (fault == "heater_half" and t >= 600) else 1.0
    Pact = Pcmd * frac
    I = Pact / Vsup
    Vout = CdA * math.sqrt(2 * g * h)
    rows.append(dict(time_s=t, level_m=round(h, 6), inflow_Lps=round(Vin * 1000, 6),
                     outflow_m3s=round(Vout, 9), T_in_C=round(Tin - 273.15, 4),
                     T_tank_C=round(T - 273.15, 5), T_amb_C=round(Tamb - 273.15, 4),
                     P_heater_cmd_kW=round(Pcmd / 1000, 4), I_heater_A=round(I, 4),
                     U_heater_V=Vsup))
    # explicit Euler step
    V = A * h
    m = rho * V
    Qloss = UA * (T - Tamb)
    dT = (Vin * rho * cp * (Tin - T) + eta * Pact - Qloss) / (m * cp)
    h = h + (Vin - Vout) / A * dt
    T = T + dT * dt
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(f"wrote {len(rows)} rows to {out}")
