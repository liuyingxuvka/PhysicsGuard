"""Use the shared native driver in its command process boundary, never a copied runner."""
from pathlib import Path
import subprocess
import sys


def test_assumption_cards_apply_repeat_and_reset_through_native_binding():
    root=Path(__file__).resolve().parents[2]
    script='''from pathlib import Path
import sys
from flowguard.flow.model import load_model
from flowguard.flow.checks import check_model
from flowguard.flow.adapter import check_trace,trace_calls
root=Path(sys.argv[1])
graph=check_model(load_model(root/'.flowguard/flow/assumption_lifecycle.py',root)).graph
assert graph.complete
calls={call.action.name:call.index for call in graph.calls}
for actions in (('reset',),('reset','reset'),('apply',),('apply','apply'),('apply','reset','apply')):
    result=check_trace(graph,trace_calls(graph,[calls[name] for name in actions]))
    assert result.status=='conformant',result.to_dict()
print('actual cards: fresh and repeated reset, explicit apply, repeat and reset/reapply')
'''
    result=subprocess.run([sys.executable,'-c',script,str(root)],cwd=root,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'actual cards:' in result.stdout
