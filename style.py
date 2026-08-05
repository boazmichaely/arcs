"""Visual configuration, kept separate so colors/sizes can be changed in one place."""

from dataclasses import dataclass


# Zoom pivot modes (code-configurable; not yet exposed in the settings UI).
ZOOM_PIVOT_ORIGIN = "origin"
ZOOM_PIVOT_CURSOR = "cursor"


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

    # Arc size labels are shown only while current_step <= this value.
    # Undo back under the limit and labels reappear. Set very high to always label.
    max_step_to_render_arc_size: int = 10

    # Mouse-wheel / Up-Down zoom. Pivot is code-configurable only for now.
    zoom_pivot: str = ZOOM_PIVOT_ORIGIN  # or ZOOM_PIVOT_CURSOR

    # Base per-step zoom speed (>1) used right at the default/auto-fit view.
    # 1.05 means each zoom step changes the view size by 5%.
    zoom_factor: float = 1.05

    # Zoom damping: the *effective* zoom speed shrinks smoothly (continuously,
    # not in tiers) the further the view is from the default auto-fit view, so
    # a held key/scroll doesn't blow past content once you're already zoomed
    # way out - e.g. at damping=0.6, a view 8x the default size zooms at
    # roughly 1/3 the speed it would right at the default view. This depends
    # only on *distance* from the default view, not on which direction you're
    # currently pressing, so zooming in from a far-zoomed-out view is just as
    # damped as zooming out further from there - zoom-in and zoom-out share
    # the same speed curve. 0 disables damping (constant speed everywhere).
    # See ArcRenderer._zoom_speed_factor for the formula.
    zoom_damping: float = 0.6

    # Practically unlimited zoom range (only guards against float overflow/underflow),
    # so deep zoom at large step counts keeps working - that's when it looks best,
    # since it reads as a smoothly receding/advancing spiral.
    zoom_scale_min: float = 1e-9
    zoom_scale_max: float = 1e9
