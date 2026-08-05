"""Matplotlib rendering for a Simulation. Knows nothing about which StepRule
produced the steps, only about (start, end) pairs and their derived
above/below/radius/center properties.
"""

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Arc

from simulation import Simulation
from style import StyleConfig

CONTROLS_TEXT = (
    "Right / Space / Enter: advance by increment   |   type digits + Enter: advance that many "
    "and remember it as the increment   |   Backspace: edit typed count   |   "
    "Left: undo by increment   |   Q / Esc: quit"
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

        self.fig, self.ax = plt.subplots(figsize=(9, 4))
        self.fig.canvas.manager.set_window_title("Number Line Arcs")
        self.ax.set_aspect("equal", adjustable="box")

    def status_line(self) -> str:
        pos = self.simulation.current_position
        step = self.simulation.current_step
        typed = f"  |  typed: {self.input_buffer}" if self.input_buffer else ""
        return f"Step {step}   Position {pos}   |  increment: {self.step_increment}{typed}"

    def redraw(self) -> None:
        ax = self.ax
        style = self.style
        sim = self.simulation
        ax.clear()

        line_min, line_max = sim.bounds()
        max_radius = sim.max_radius()

        x_pad = (line_max - line_min) * style.padding_fraction
        y_extent = max(max_radius, 1.0)
        y_pad = y_extent * style.padding_fraction

        ax.set_xlim(line_min - x_pad, line_max + x_pad)
        ax.set_ylim(-(y_extent + y_pad), y_extent + y_pad)
        ax.set_aspect("equal", adjustable="box")

        # The number line itself.
        ax.axhline(0, color=style.line_color, linewidth=1.2, zorder=1)

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

            label_y = step.radius * (1.12 if step.is_above else -1.12)
            va = "bottom" if step.is_above else "top"
            ax.text(
                step.center,
                label_y,
                str(step.n),
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
