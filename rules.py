"""Step rules: pluggable policies that decide the next position on the number line.

A StepRule only answers one question: given step n, the current position, and
the set of positions already visited, where do we go next? Everything else
(bookkeeping, zoom/bounds, above-vs-below arc placement, rendering) lives
elsewhere and never needs to change when the rule changes.

Arc placement is derived from the actual direction of movement (moved right ->
arc above, moved left -> arc below), not from the parity of n. That keeps the
renderer and simulation fully rule-agnostic, even for rules whose direction
depends on runtime state (e.g. a Recaman-style "try left, fall back to right"
rule) rather than on whether n is odd or even.
"""

from abc import ABC, abstractmethod


class StepRule(ABC):
    """Base class for a movement policy."""

    @abstractmethod
    def next_position(self, n: int, pos: int, visited: frozenset[int]) -> int:
        """Return the next position for step n.

        Args:
            n: the current step number (1, 2, 3, ...).
            pos: the current position before this step.
            visited: every position reached so far, including the start (0).
        """
        raise NotImplementedError


class AlternatingParityRule(StepRule):
    """The default rule: odd n moves right, even n moves left.

    n odd  -> pos + n (arc drawn above)
    n even -> pos - n (arc drawn below)
    """

    def next_position(self, n: int, pos: int, visited: frozenset[int]) -> int:
        return pos + n if n % 2 == 1 else pos - n


DEFAULT_RULE = AlternatingParityRule()
