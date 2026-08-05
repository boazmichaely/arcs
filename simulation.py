"""Simulation state: step history, visited set, and the growing/zooming line bounds.

This module knows nothing about matplotlib and nothing about which StepRule
produced a position. It only replays whatever rule it was given and keeps
track of history, so it works unchanged no matter how the rule is defined.
"""

from dataclasses import dataclass, field

from rules import StepRule, DEFAULT_RULE

INITIAL_BOUND = 5
BOUND_GROWTH = 5


@dataclass(frozen=True)
class Step:
    n: int
    start: int
    end: int

    @property
    def is_above(self) -> bool:
        """Arcs are placed above the line when the move was to the right."""
        return self.end > self.start

    @property
    def radius(self) -> float:
        return abs(self.end - self.start) / 2

    @property
    def center(self) -> float:
        return (self.start + self.end) / 2


class Simulation:
    """Holds the full step history for a run and derives view bounds from it."""

    def __init__(self, rule: StepRule = DEFAULT_RULE):
        self.rule = rule
        self.steps: list[Step] = []
        self._visited: set[int] = {0}

    @property
    def current_position(self) -> int:
        return self.steps[-1].end if self.steps else 0

    @property
    def current_step(self) -> int:
        return len(self.steps)

    def advance(self, count: int = 1) -> None:
        for _ in range(count):
            n = len(self.steps) + 1
            pos = self.current_position
            new_pos = self.rule.next_position(n, pos, frozenset(self._visited))
            self.steps.append(Step(n=n, start=pos, end=new_pos))
            self._visited.add(new_pos)

    def undo(self, count: int = 1) -> None:
        count = min(count, len(self.steps))
        for _ in range(count):
            removed = self.steps.pop()
            # Only drop the visited position if nothing else still needs it
            # (positions can, in general, be revisited by later rules).
            if not any(s.end == removed.end for s in self.steps) and removed.end != 0:
                self._visited.discard(removed.end)

    def bounds(self) -> tuple[int, int]:
        """The current [line_min, line_max].

        Grows by BOUND_GROWTH on *both* sides at once whenever either side is
        exceeded, so the line stays centered/symmetric at every step instead
        of momentarily growing lopsided on the step that triggered it.
        """
        line_min, line_max = -INITIAL_BOUND, INITIAL_BOUND
        for step in self.steps:
            while step.end < line_min or step.end > line_max:
                line_min -= BOUND_GROWTH
                line_max += BOUND_GROWTH
        return line_min, line_max

    def max_radius(self) -> float:
        if not self.steps:
            return 0.0
        return max(step.radius for step in self.steps)
