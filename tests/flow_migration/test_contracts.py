"""Every independent rule and bad-fact variant retains a direct, named destination."""
import pytest
from .contract_cases import TOPICS, cases, expected, module, mutations, states

RULES=[(topic,name) for topic in TOPICS for name in module(topic).RULE_NAMES]
BAD=[(topic,name,rule) for topic in TOPICS for name,rule in mutations(topic).items()]

@pytest.mark.parametrize('topic,name',RULES,ids=[f'{topic}:{name}' for topic,name in RULES])
def test_independent_rule(topic,name):
    m=module(topic)
    predicate=m.RULES[m.RULE_NAMES.index(name)]
    assert all(predicate(state,None) for state in states(topic)),(topic,name)

@pytest.mark.parametrize('topic,mutation,rule',BAD,ids=[f'{topic}:{name}' for topic,name,rule in BAD])
def test_rejects_original_bad_facts(topic,mutation,rule):
    m=module(topic)
    predicate=m.RULES[m.RULE_NAMES.index(rule)]
    assert any(not predicate(expected(topic,case,mutation),None) for case in cases(topic)),(topic,mutation,rule)
