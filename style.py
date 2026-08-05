"""Visual configuration, kept separate so colors/sizes can be changed in one place."""

from dataclasses import dataclass


@dataclass
class StyleConfig:
    # Both default to the same color; change independently to tell above/below apart.
    above_color: str = "black"
    below_color: str = "black"

    line_color: str = "black"
    origin_marker_color: str = "black"
    position_marker_color: str = "crimson"

    arc_linewidth: float = 1.6
    label_fontsize: float = 8.0
    status_fontsize: float = 10.0

    padding_fraction: float = 0.12  # extra breathing room around the computed bounds
