"""Matplotlib rendering for a Simulation. Knows nothing about which StepRule
or OrientationRule produced the steps, only about each Step's derived
is_above/moved_right/radius/center properties, and calls whatever ColorRule
it was given to turn those into a color.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Arc
from matplotlib.widgets import Button

from colors import ask_two_colors
from rules import ColorRule, DEFAULT_COLOR_RULE
from simulation import Simulation
from style import ZOOM_PIVOT_CURSOR, StyleConfig

CONTROLS_TEXT = (
    "Right / Space / Enter: advance   |   digits + Enter: set increment & advance   |   "
    "Backspace: edit typed count   |   Left: undo   |   Up / Down / Scroll: zoom   |   "
    "Shift+Up/Down: zoom speed   |   Shift+Left/Right: pan (viewport only)   |   "
    "Colors / C: arc colors   |   Q / Esc: quit"
)


def _nice_tick_step(span: float, target_ticks: int = 10) -> float:
    """Pick a "nice" (1/2/5 x 10^k) tick spacing for the given axis span."""
    if span <= 0:
        return 1.0
    raw_step = span / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    for multiple in (1, 2, 5, 10):
        step = multiple * magnitude
        if step >= raw_step:
            return step
    return 10 * magnitude


class ArcRenderer:
    def __init__(
        self,
        simulation: Simulation,
        style: StyleConfig | None = None,
        color_rule: ColorRule = DEFAULT_COLOR_RULE,
    ):
        self.simulation = simulation
        self.style = style or StyleConfig()
        self.color_rule = color_rule
        self.input_buffer = ""
        # Remembered step count: used for advance/undo whenever no digits are
        # currently typed, and updated whenever a typed number is confirmed
        # with Enter.
        self.step_increment = 1
        # User zoom relative to the auto-fit view. Reset whenever the step set changes.
        self.zoom_scale = 1.0
        # Viewport center in data units. Only used when style.viewport_width
        # is set; otherwise the view always spans the whole line and this is
        # ignored. Starts at style.initial_pan_center and only moves via
        # explicit pan_by() calls - it does *not* auto-follow the current
        # position, so the view stays visually stable step to step instead
        # of jumping around.
        self.pan_center = self.style.initial_pan_center

        # Leave room at the top for the Colors button (macosx toolbar cannot host custom icons).
        self.fig, self.ax = plt.subplots(figsize=(9, 4))
        self.fig.subplots_adjust(top=0.88, bottom=0.14)
        self.fig.canvas.manager.set_window_title("Number Line Arcs")
        self.ax.set_aspect("equal", adjustable="box")
        self._install_save_filename()
        self._install_colors_button()

    def _install_save_filename(self) -> None:
        """Toolbar Save suggests Number_Line_Arcs-<last_step>.png."""

        def get_default_filename() -> str:
            return f"Number_Line_Arcs-{self.simulation.current_step}.png"

        self.fig.canvas.get_default_filename = get_default_filename  # type: ignore[method-assign]

    def status_line(self) -> str:
        pos = self.simulation.current_position
        step = self.simulation.current_step
        typed = f"  |  typed: {self.input_buffer}" if self.input_buffer else ""
        speed_pct = (self.style.zoom_factor - 1) * 100
        zoom = f"  |  zoom speed: {speed_pct:+.1f}%/press (scale={self.zoom_scale:.3g})"
        pan = f"  |  view center: {self.pan_center:.3g}" if self.style.viewport_width is not None else ""
        return f"Step {step}   Position {pos}   |  increment: {self.step_increment}{typed}{zoom}{pan}"

    def default_limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Baseline limits before zoom_scale is applied.

        Normally this auto-fits the whole line and every arc, so the height
        comes from the tallest arc anywhere in the run. If
        style.viewport_width/viewport_height are set, the window is a fixed
        size centered on self.pan_center instead (the whole line may be far
        too wide to show at once, e.g. Recaman's sequence) - fixed, rather
        than sized from arc radii, so the window always uses the full figure
        width regardless of content; an arc taller than viewport_height just
        clips at the edge instead of squeezing the whole view down to fit it.
        """
        style = self.style
        sim = self.simulation

        if style.viewport_width is not None:
            half_w = style.viewport_width / 2
            half_h = (style.viewport_height if style.viewport_height is not None else style.viewport_width) / 2
            x0, x1 = self.pan_center - half_w, self.pan_center + half_w
            return (x0, x1), (-half_h, half_h)

        line_min, line_max = sim.bounds()
        x_pad = (line_max - line_min) * style.padding_fraction
        max_radius = sim.max_radius()
        y_extent = max(max_radius, 1.0)
        y_pad = y_extent * style.padding_fraction
        return (line_min - x_pad, line_max + x_pad), (-(y_extent + y_pad), y_extent + y_pad)

    def apply_view_limits(self) -> None:
        """Apply the baseline limits scaled by zoom_scale around the configured pivot."""
        (x0, x1), (y0, y1) = self.default_limits()
        scale = self.zoom_scale
        # Zoom in => smaller window => scale < 1. Pivot stays fixed.
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        # For origin pivot, center the view on (0, 0) rather than the midpoint of
        # the auto-fit box (which is already ~0 for this rule, but stay explicit).
        # A fixed-width viewport has its own pan-controlled center instead -
        # there's no single "origin" to snap back to.
        if self.style.viewport_width is None and self.style.zoom_pivot != ZOOM_PIVOT_CURSOR:
            cx, cy = 0.0, 0.0
        half_w = (x1 - x0) / 2 * scale
        half_h = (y1 - y0) / 2 * scale
        self.ax.set_xlim(cx - half_w, cx + half_w)
        self.ax.set_ylim(cy - half_h, cy + half_h)
        self.ax.set_aspect("equal", adjustable="box")

    def pan_by(self, direction: int) -> None:
        """Slide a fixed-width viewport left (-1) or right (+1). No-op otherwise."""
        if self.style.viewport_width is None:
            return
        step = self.style.viewport_width * self.zoom_scale * self.style.pan_step_fraction
        self.pan_center += direction * step
        self.apply_view_limits()
        self._refresh_title()
        self.fig.canvas.draw_idle()

    def _refresh_title(self) -> None:
        self.ax.set_title(self.status_line(), fontsize=self.style.status_fontsize)

    def zoom_at(self, direction: str, cursor_x: float | None, cursor_y: float | None) -> None:
        """Zoom in ('up') or out ('down'). Pivot from StyleConfig.zoom_pivot."""
        factor = self.style.zoom_factor
        if direction == "up":
            self.zoom_scale /= factor
        else:
            self.zoom_scale *= factor
        # Clamp only against float overflow/underflow, not against "useful" zoom -
        # deep zoom at large step counts is where this looks best.
        self.zoom_scale = min(max(self.zoom_scale, self.style.zoom_scale_min), self.style.zoom_scale_max)

        if self.style.zoom_pivot == ZOOM_PIVOT_CURSOR and cursor_x is not None and cursor_y is not None:
            # Scale current limits around the cursor without recomputing auto-fit.
            ax = self.ax
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            f = 1 / factor if direction == "up" else factor
            ax.set_xlim(cursor_x + (x0 - cursor_x) * f, cursor_x + (x1 - cursor_x) * f)
            ax.set_ylim(cursor_y + (y0 - cursor_y) * f, cursor_y + (y1 - cursor_y) * f)
            # Keep zoom_scale consistent with origin-based path for later redraws.
            self._refresh_title()
            self.fig.canvas.draw_idle()
            return

        self.apply_view_limits()
        self._refresh_title()
        self.fig.canvas.draw_idle()

    def reset_zoom(self) -> None:
        self.zoom_scale = 1.0
        self.apply_view_limits()
        self.fig.canvas.draw_idle()

    def adjust_zoom_factor(self, delta: float) -> None:
        self.style.zoom_factor = max(1.001, self.style.zoom_factor + delta)
        self._refresh_title()
        self.fig.canvas.draw_idle()

    def _install_colors_button(self) -> None:
        """On-figure Colors control.

        The native macosx matplotlib toolbar is fixed by the backend (Home, Pan,
        Zoom, Save, …) and does not accept custom icons without switching to a
        Qt/Tk backend. A figure button is the portable stand-in.
        """
        btn_ax = self.fig.add_axes([0.86, 0.92, 0.12, 0.055])
        self._colors_button = Button(btn_ax, "Colors")
        self._colors_button.on_clicked(lambda _evt: self.open_color_settings())

    def open_color_settings(self) -> None:
        """Prompt for the two arc colors and redraw."""
        style = self.style
        color_a, color_b = ask_two_colors(style.color_a_label, style.color_b_label, style.color_a, style.color_b)
        style.color_a = color_a
        style.color_b = color_b
        self.redraw(preserve_zoom=True)

    def redraw(self, *, preserve_zoom: bool = False) -> None:
        ax = self.ax
        style = self.style
        sim = self.simulation
        ax.clear()

        if not preserve_zoom:
            self.zoom_scale = 1.0
            # pan_center is deliberately *not* reset here: recentering on the
            # new position every step made the view visibly jump left/right
            # each time the sequence moved. The viewport instead stays
            # wherever it is (initially 0) until the user explicitly pans
            # with Shift+Left/Right.

        self.apply_view_limits()

        # The number line itself.
        ax.axhline(0, color=style.line_color, linewidth=1.2, zorder=1)

        # Ticks are derived from the *actual current view* (post pan/zoom),
        # not the full data bounds - matplotlib expands the view to fit
        # whatever ticks you set (even with autoscale off), so ticks outside
        # the current view would silently widen it back out.
        view_min, view_max = ax.get_xlim()
        tick_step = _nice_tick_step(view_max - view_min)
        first_tick = math.ceil(view_min / tick_step) * tick_step
        ticks = []
        t = first_tick
        while t <= view_max + 1e-9:
            ticks.append(round(t, 6))
            t += tick_step
        ax.set_xticks(ticks)
        ax.set_yticks([])
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)

        # Origin marker.
        ax.plot(0, 0, marker="o", markersize=5, color=style.origin_marker_color, zorder=3)

        show_labels = sim.current_step <= style.max_step_to_render_arc_size

        # Arcs.
        for step in sim.steps:
            color_key = self.color_rule.color_key(step.is_above, step.moved_right)
            color = style.color_a if color_key == "a" else style.color_b
            theta1, theta2 = (0, 180) if step.is_above else (180, 360)
            arc = Arc(
                (step.center, 0),
                width=2 * step.radius,
                height=2 * step.radius,
                theta1=theta1,
                theta2=theta2,
                color=color,
                linewidth=style.arc_linewidth,
                zorder=2,
            )
            ax.add_patch(arc)

            if show_labels:
                # Signed by move direction (not by which side the arc is
                # drawn on) so the label always reads as "distance moved",
                # even for a rule where side and direction are independent.
                label = str(step.n) if step.moved_right else f"-{step.n}"
                label_y = step.radius * (1.12 if step.is_above else -1.12)
                va = "bottom" if step.is_above else "top"
                ax.text(
                    step.center,
                    label_y,
                    label,
                    ha="center",
                    va=va,
                    fontsize=style.label_fontsize,
                    color=color,
                )

        # Current position marker.
        ax.plot(
            sim.current_position,
            0,
            marker="o",
            markersize=7,
            color=style.position_marker_color,
            zorder=4,
        )

        ax.set_title(self.status_line(), fontsize=style.status_fontsize)
        self.fig.suptitle("")
        self._draw_controls_footer()

        self.fig.canvas.draw_idle()

    def _draw_controls_footer(self) -> None:
        for txt in getattr(self, "_footer_texts", []):
            txt.remove()
        self._footer_texts = [
            self.fig.text(0.5, 0.02, CONTROLS_TEXT, ha="center", va="bottom", fontsize=8, color="gray")
        ]
