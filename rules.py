"""Pluggable policies for a number-line visualization "variant".

Three independent questions define a variant, each answered by its own tiny
strategy so a new sequence can mix and match without touching simulation.py
or renderer.py:

  StepRule        - given step n, where do we move to next?
  OrientationRule - given step n and the move, is the arc drawn above or
                    below the line?
  ColorRule       - given the arc's orientation and actual move direction,
                    which of the two configured colors does it use?

For the default variant (AlternatingParityRule), orientation and movement
direction coincide by construction (odd n always moves right), which is why
color-by-orientation and color-by-direction look identical there. They
diverge for a rule like Recaman's, where the move direction depends on
runtime state (already-visited positions) rather than on the parity of n -
that's exactly why orientation and coloring are kept as separate policies
here instead of being derived from a single "moved right?" flag.
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

    n odd  -> pos + n
    n even -> pos - n
    """

    def next_position(self, n: int, pos: int, visited: frozenset[int]) -> int:
        return pos + n if n % 2 == 1 else pos - n


class RecamanRule(StepRule):
    """Recaman's sequence: try subtracting n first.

    Use pos - n if that's non-negative and hasn't been visited yet;
    otherwise fall back to pos + n.
    """

    def next_position(self, n: int, pos: int, visited: frozenset[int]) -> int:
        left = pos - n
        if left >= 0 and left not in visited:
            return left
        return pos + n


DEFAULT_RULE = AlternatingParityRule()


class OrientationRule(ABC):
    """Decides whether an arc is drawn above or below the line."""

    @abstractmethod
    def is_above(self, n: int, start: int, end: int) -> bool:
        raise NotImplementedError


class DirectionOrientation(OrientationRule):
    """The default: arc goes above when the move was to the right."""

    def is_above(self, n: int, start: int, end: int) -> bool:
        return end > start


class AlternatingOrientation(OrientationRule):
    """Arc side alternates by step parity, regardless of move direction.

    Odd steps above, even steps below - the convention used by the classic
    Recaman's-sequence visualizations, which keeps successive arcs visually
    separated even though the sequence can move in either direction on any
    step.
    """

    def is_above(self, n: int, start: int, end: int) -> bool:
        return n % 2 == 1


DEFAULT_ORIENTATION = DirectionOrientation()


class ColorRule(ABC):
    """Decides which of the two configured colors ('a' or 'b') an arc uses."""

    @abstractmethod
    def color_key(self, is_above: bool, moved_right: bool) -> str:
        raise NotImplementedError


class SideColorRule(ColorRule):
    """The default: color follows which side the arc is drawn on."""

    def color_key(self, is_above: bool, moved_right: bool) -> str:
        return "a" if is_above else "b"


class ClockwiseColorRule(ColorRule):
    """Color by the arc's rotational direction, not by which side it's on.

    A half-circle between two points can be traced two ways: over the top or
    under the bottom. Tracing it from the move's start to its end, the path
    is clockwise exactly when "which side" agrees with "which way moved":
    above-and-moved-right, or below-and-moved-left. Everything else -
    above-and-moved-left, or below-and-moved-right - is counter-clockwise.
    """

    def color_key(self, is_above: bool, moved_right: bool) -> str:
        clockwise = is_above == moved_right
        return "a" if clockwise else "b"


DEFAULT_COLOR_RULE = SideColorRule()


# Named bundles of (StepRule, OrientationRule, ColorRule) plus the StyleConfig
# field overrides each needs, so arcs.py only has to pick one name. Add a new
# entry here for a new sequence/visualization instead of touching renderer.py
# or simulation.py.
VARIANTS: dict[str, dict] = {
    "default": {
        "description": "Odd n moves right (arc above), even n moves left (arc below).",
        "rule": DEFAULT_RULE,
        "orientation": DEFAULT_ORIENTATION,
        "color_rule": DEFAULT_COLOR_RULE,
        "style": {},
    },
    "recaman": {
        "description": "Recaman's sequence: try pos-n (if non-negative and unvisited), else pos+n.",
        "rule": RecamanRule(),
        "orientation": AlternatingOrientation(),
        "color_rule": ClockwiseColorRule(),
        "style": {
            "viewport_width": 40.0,
            "viewport_height": 16.9,  # fills the full figure width for the default figsize/margins
            "color_a_label": "Clockwise-arc",
            "color_b_label": "Counter-clockwise-arc",
            "show_smallest_missing": True,
        },
    },
}
