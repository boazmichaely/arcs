"""Matplotlib rendering for a Simulation. Knows nothing about which StepRule
produced the steps, only about (start, end) pairs and their derived
above/below/radius/center properties.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Arc
from matplotlib.widgets import Button

from colors import ask_arc_colors
from simulation import Simulation
from style import ZOOM_PIVOT_CURSOR, StyleConfig

CONTROLS_TEXT = (
    "Right / Space / Enter: advance by increment   |   type digits + Enter: set increment & advance   |   "
    "Backspace: edit typed count   |   Left: undo by increment   |   "
    "Up / Down / Scroll: zoom   |   Colors / C: arc colors   |   Q / Esc: quit"
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
    def __init__(self, simulation: Simulation, style: StyleConfig | None = None):
        self.simulation = simulation
        self.style = style or StyleConfig()
        self.input_buffer = ""
        # Remembered step count: used for advance/undo whenever no digits are
        # currently typed, and updated whenever a typed number is confirmed
        # with Enter.
        self.step_increment = 1
        # User zoom relative to the auto-fit view. Reset whenever the step set changes.
        self.zoom_scale = 1.0

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
        return f"Step {step}   Position {pos}   |  increment: {self.step_increment}{typed}"

    def default_limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Auto-fit limits that show the whole line and every arc."""
        style = self.style
        sim = self.simulation
        line_min, line_max = sim.bounds()
        max_radius = sim.max_radius()
        x_pad = (line_max - line_min) * style.padding_fraction
        y_extent = max(max_radius, 1.0)
        y_pad = y_extent * style.padding_fraction
        return (
            (line_min - x_pad, line_max + x_pad),
            (-(y_extent + y_pad), y_extent + y_pad),
        )

    def apply_view_limits(self) -> None:
        """Apply auto-fit limits scaled by zoom_scale around the configured pivot."""
        (x0, x1), (y0, y1) = self.default_limits()
        scale = self.zoom_scale
        # Zoom in => smaller window => scale < 1. Pivot stays fixed.
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        # For origin pivot, center the view on (0, 0) rather than the midpoint of
        # the auto-fit box (which is already ~0 for this rule, but stay explicit).
        if self.style.zoom_pivot != ZOOM_PIVOT_CURSOR:
            cx, cy = 0.0, 0.0
        half_w = (x1 - x0) / 2 * scale
        half_h = (y1 - y0) / 2 * scale
        self.ax.set_xlim(cx - half_w, cx + half_w)
        self.ax.set_ylim(cy - half_h, cy + half_h)
        self.ax.set_aspect("equal", adjustable="box")

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
            self.fig.canvas.draw_idle()
            return

        self.apply_view_limits()
        self.fig.canvas.draw_idle()

    def reset_zoom(self) -> None:
        self.zoom_scale = 1.0
        self.apply_view_limits()
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
        """Prompt for above/below arc colors and redraw."""
        above, below = ask_arc_colors(self.style.above_color, self.style.below_color)
        self.style.above_color = above
        self.style.below_color = below
        self.redraw(preserve_zoom=True)

    def redraw(self, *, preserve_zoom: bool = False) -> None:
        ax = self.ax
        style = self.style
        sim = self.simulation
        ax.clear()

        if not preserve_zoom:
            self.zoom_scale = 1.0

        self.apply_view_limits()

        # The number line itself.
        ax.axhline(0, color=style.line_color, linewidth=1.2, zorder=1)

        line_min, line_max = sim.bounds()
        tick_step = _nice_tick_step(line_max - line_min)
        first_tick = math.floor(line_min / tick_step) * tick_step
        ticks = []
        t = first_tick
        while t <= line_max + 1e-9:
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
            color = style.above_color if step.is_above else style.below_color
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
                label = str(step.n) if step.is_above else f"-{step.n}"
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
