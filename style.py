"""Visual configuration, kept separate so colors/sizes can be changed in one place."""

from dataclasses import dataclass


# Zoom pivot modes (code-configurable; not yet exposed in the settings UI).
ZOOM_PIVOT_ORIGIN = "origin"
ZOOM_PIVOT_CURSOR = "cursor"


@dataclass
class StyleConfig:
    # Two generic arc colors. Which arcs get which is decided by the active
    # ColorRule (rules.py) - e.g. by which side the arc is drawn on, or by
    # its rotational direction.
    color_a: str = "blue"
    color_b: str = "red"
    # Labels used only for the color-picker dialog title, so it's obvious
    # which group is being picked for the active variant.
    color_a_label: str = "Above-arc"
    color_b_label: str = "Below-arc"

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

    # Per-step zoom speed (>1) applied on every Up/Down/scroll zoom step.
    # 1.05 means each zoom step changes the view size by 5%.
    zoom_factor: float = 1.05

    # Practically unlimited zoom range (only guards against float overflow/underflow),
    # so deep zoom at large step counts keeps working - that's when it looks best,
    # since it reads as a smoothly receding/advancing spiral.
    zoom_scale_min: float = 1e-9
    zoom_scale_max: float = 1e9

    # Fixed-*shape* auto-fit viewport instead of always fitting the whole
    # line at whatever aspect ratio the content dictates. None (default)
    # keeps the original "always show everything, any shape" behavior, which
    # suits a sequence that grows roughly as fast horizontally as
    # vertically. Set both viewport_width and viewport_height for a sequence
    # (e.g. Recaman's) that can range far wider than it's tall, where a
    # square/content-shaped view would squeeze the figure's width down to
    # match - here the shape (ratio of these two) is fixed to always use the
    # full figure width, and ArcRenderer._auto_fit_scale() scales that shape
    # up (both dimensions together, to keep circles circular) just enough to
    # fit every step so far, so it reads as "zoom out to fit everything"
    # rather than "clip" or "shrink the box".
    viewport_width: float | None = None
    # Matched to viewport_width for the default figure size/margins (9x4in,
    # top=0.88/bottom=0.14) so the window exactly fills the available width
    # with no wasted margin. Retune if figsize or those margins change.
    viewport_height: float | None = None
    # Fraction of the (zoomed) viewport width moved per pan key press.
    pan_step_fraction: float = 0.2
