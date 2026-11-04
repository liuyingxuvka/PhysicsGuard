"""Structural coverage is configuration; execution results remain outside the repository."""
import ast
import json
from pathlib import Path
import pytest
from .contract_cases import TOPICS,module,mutations

ROOT=Path(__file__).resolve().parents[2]
COVERAGE=json.loads((Path(__file__).with_name('coverage.json')).read_text())


def definitions(path):
    def walk(node,prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=prefix+child.name
                yield name
                yield from walk(child,name+'.')
            else:
                yield from walk(child,prefix)
    return set(walk(ast.parse(path.read_text())))


def test_all_original_rules_variants_and_bindings_have_named_destinations():
    assert {(r['topic'],r['rule']) for r in COVERAGE['rules']} == {(topic,name) for topic in TOPICS for name in module(topic).RULE_NAMES}
    assert {(r['topic'],r['variant']) for r in COVERAGE['variants']} == {(topic,name) for topic in TOPICS for name in mutations(topic)}
    assert len(COVERAGE['rules'])==48 and len(COVERAGE['bindings'])==72
    assert all(v['kind']=='ABSTRACT_bad_facts' and not v['production_source_mutation'] for v in COVERAGE['variants'])
    for item in COVERAGE['bindings']:
        path,name=item['binding'].split(':',1)
        assert name in definitions(ROOT/path),item
    assert not (ROOT/'.flowguard/models').exists()
    assert not (ROOT/'.flowguard/map.json').exists()


@pytest.mark.parametrize('route',COVERAGE['generated_system'],ids=[r['id'] for r in COVERAGE['generated_system']])
def test_original_system_route_targets_exist(route):
    # The old map asserted named ownership/existence, not an order for these functions.
    for target in route['targets']:
        path,symbol=target.split(':',1)
        assert symbol in definitions(ROOT/path),(route['id'],target)
