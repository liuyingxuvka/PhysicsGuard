"""The one way a relation refuses a value: DomainRefusal."""
from __future__ import annotations


class DomainRefusal(ValueError):
    """A relation refuses a value or parameter outside its stated domain.

    Native modules and variable declarations raise it from their range checks (a value
    below a denominator floor, an input outside a table, an efficiency above 1, an
    initial guess outside its bounds). The tool's own probes (unit-factor hints, scale
    replays, resolution samples, bounded root search) skip exactly this refusal; any
    other error reaches the caller, and the command exits 2 with its text. A custom
    module raises it to refuse a value the same way.
    """


__all__ = ["DomainRefusal"]
