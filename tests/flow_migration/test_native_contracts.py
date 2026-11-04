"""Current production paths, checked by preserved independent expected contracts."""
import pytest
from .contract_cases import TOPICS,module

@pytest.mark.parametrize('topic',TOPICS)
def test_native_contract(topic):
    module(topic).assert_native_contract()
