"""The one way a relation refuses a value: DomainRefusal."""
from __future__ import annotations


class DomainRefusal(ValueError):
    """A relation refuses a value or parameter outside its stated domain.

    Native modules and variable declarations raise it from their range checks (a value
    below a denominator floor, an input outside a table, an efficiency above 1, an
    initial guess outside its bounds). Unit-factor hints, scale replays and resolution
    samples skip exactly this refusal; any
    other error reaches the caller, and the command exits 2 with its text. Bounded
    root sampling also treats division by zero and overflow at a sample point as
    undefined, leaving the variable unobserved. Other arithmetic errors propagate.
    A custom module raises DomainRefusal to refuse a value the same way.
    """


__all__ = ["DomainRefusal"]
