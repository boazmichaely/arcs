"""Matplotlib rendering for a Simulation. Knows nothing about which StepRule
or OrientationRule produced the steps, only about each Step's derived
is_above/moved_right/radius/center properties, and calls whatever ColorRule
it was given to turn those into a color.
"""

from __future__ import annotations

import math
from contextlib import contextmanager

import matplotlib as mpl
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
    "R: reset zoom to auto-fit   |   Colors / C: arc colors   |   Q / Esc: quit"
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
        # Manual zoom on top of the auto-fit baseline. Reset by reset_zoom()
        # (also triggered by R) and whenever the step set changes.
        self.zoom_scale = 1.0
        # True once the view has been manually positioned - via Shift+Left/
        # Right, or via the matplotlib toolbar's own Pan/Zoom/Home/Back/
        # Forward tools (detected through _on_external_view_change below) -
        # so a fixed-width viewport (e.g. recaman) stops auto-tracking a
        # computed position and instead leaves the view exactly where it
        # was left. R (reset_zoom) releases this latch again.
        self._manual_pan = False
        # Guards ax.set_xlim/ylim calls we make ourselves (redraw, zoom_at,
        # pan_by, apply_view_limits) so the xlim_changed callback below can
        # tell those apart from an *external* change (toolbar pan/zoom/home)
        # and only treat the latter as taking manual control of the view.
        self._suspend_view_tracking_depth = 0

        self._disable_default_keymaps()

        # Leave room at the top for the Colors button (macosx toolbar cannot host custom icons).
        self.fig, self.ax = plt.subplots(figsize=(9, 4))
        self.fig.subplots_adjust(top=0.88, bottom=0.14)
        self.fig.canvas.manager.set_window_title("Number Line Arcs")
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.callbacks.connect("xlim_changed", self._on_external_view_change)
        self._install_save_filename()
        self._install_colors_button()

    @contextmanager
    def _suspend_view_change_tracking(self):
        """Wrap our own view-limit changes so they don't look external."""
        self._suspend_view_tracking_depth += 1
        try:
            yield
        finally:
            self._suspend_view_tracking_depth -= 1

    def _on_external_view_change(self, _ax) -> None:
        """Fires on *any* xlim change, including the toolbar's own Pan, Zoom,
        Home, and Back/Forward tools - not just our own code (see
        _suspend_view_change_tracking). Only meaningful for a fixed-width
        viewport (e.g. recaman); the default variant has no manual-pan
        concept and keeps always auto-fitting around the origin."""
        if self._suspend_view_tracking_depth > 0:
            return
        if self.style.viewport_width is not None:
            self._manual_pan = True

    @staticmethod
    def _disable_default_keymaps() -> None:
        """Clear matplotlib's default key bindings so only our on_key handler runs.

        By default matplotlib binds e.g. 'left'/'right' to its own Back/Forward
        view-history navigation and 'r'/'h' to Home (reset view) - all keys we
        reuse for our own pan/zoom/undo. Both handlers fire on the same press,
        so matplotlib's navigation was silently fighting our tracked zoom/pan
        state (e.g. a manual zoom snapping back to a stale toolbar Home/Back
        view). Clearing every keymap.* default avoids the collision entirely.
        """
        for name in list(mpl.rcParams):
            if name.startswith("keymap."):
                mpl.rcParams[name] = []

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
        zoom = f"  |  zoom speed: {speed_pct:+.1f}%/press (scale={self.effective_zoom_scale():.3g})"
        return f"Step {step}   Position {pos}   |  increment: {self.step_increment}{typed}{zoom}"

    def _auto_fit_scale(self) -> float:
        """Minimum scale (>= 1) needed to fit every step so far without clipping.

        Only meaningful for a fixed-shape viewport: viewport_width/height
        describe a constant *shape* (matching the figure, so it always uses
        the full window), but the sequence's horizontal spread and the
        tallest arc's radius only grow, so scaling that shape up (width and
        height together, to keep circles circular) just enough keeps
        everything visible without ever needing to shrink the box away from
        the full window width. A no-op (1.0) for the auto-fit-everything
        default variant, which already never clips.
        """
        style = self.style
        sim = self.simulation
        if style.viewport_width is None or style.viewport_height is None:
            return 1.0
        line_min, line_max = sim.position_range()
        width_needed = (line_max - line_min) * (1 + style.padding_fraction)
        height_needed = 2 * sim.max_radius() * (1 + style.padding_fraction)
        scale_w = width_needed / style.viewport_width
        scale_h = height_needed / style.viewport_height
        return max(1.0, scale_w, scale_h)

    def effective_zoom_scale(self) -> float:
        """The zoom_scale actually applied: manual zoom on top of the auto-fit baseline."""
        return self.zoom_scale * self._auto_fit_scale()

    def _auto_pan_center(self) -> float:
        """Where the viewport should be centered when the user hasn't manually panned.

        Left-aligned on the leftmost visited position (0 for a sequence that
        never goes negative, e.g. Recaman's) rather than centered on the
        content's midpoint, so any extra room from auto-fit's scale-up goes
        to the right - where the sequence actually grows - instead of being
        wasted symmetrically on a side nothing ever visits.
        """
        line_min, _ = self.simulation.position_range()
        half_w = self.style.viewport_width / 2 * self._auto_fit_scale()
        return line_min + half_w

    def default_limits(self, *, manual_center_x: float | None = None) -> tuple[tuple[float, float], tuple[float, float]]:
        """The auto-fit baseline view (scale and center included).

        Normally this auto-fits the whole line and every arc, so the height
        comes from the tallest arc anywhere in the run. If
        style.viewport_width/viewport_height are set, this instead returns
        a window with a fixed *shape* (matching the figure, so it always
        uses the full width) scaled up by _auto_fit_scale().         Centered by _auto_pan_center() unless self._manual_pan is set and
        the caller passed the view's actual current center
        (manual_center_x) - see redraw(), which reads that from the axes
        directly rather than a separately tracked variable, so it stays in
        sync with pans made via the toolbar too.
        """
        style = self.style
        sim = self.simulation

        if style.viewport_width is not None:
            auto_scale = self._auto_fit_scale()
            half_w = style.viewport_width / 2 * auto_scale
            half_h = (style.viewport_height if style.viewport_height is not None else style.viewport_width) / 2
            half_h *= auto_scale
            center = manual_center_x if (self._manual_pan and manual_center_x is not None) else self._auto_pan_center()
            return (center - half_w, center + half_w), (-half_h, half_h)

        line_min, line_max = sim.bounds()
        x_pad = (line_max - line_min) * style.padding_fraction
        max_radius = sim.max_radius()
        y_extent = max(max_radius, 1.0)
        y_pad = y_extent * style.padding_fraction
        return (line_min - x_pad, line_max + x_pad), (-(y_extent + y_pad), y_extent + y_pad)

    def apply_view_limits(self, *, manual_center_x: float | None = None) -> None:
        """Apply the auto-fit baseline scaled by the user's manual zoom, around the configured pivot."""
        (x0, x1), (y0, y1) = self.default_limits(manual_center_x=manual_center_x)
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
        with self._suspend_view_change_tracking():
            self.ax.set_xlim(cx - half_w, cx + half_w)
            self.ax.set_ylim(cy - half_h, cy + half_h)
            self.ax.set_aspect("equal", adjustable="box")

    def pan_by(self, direction: int) -> None:
        """Slide the *actual current* view left (-1) or right (+1). No-op otherwise.

        Reads/writes ax.get_xlim() directly (not a separately tracked
        center), so this composes correctly whether the view got to its
        current position via us or via the toolbar's own Pan/Zoom tools.
        """
        if self.style.viewport_width is None:
            return
        self._manual_pan = True
        x0, x1 = self.ax.get_xlim()
        step = (x1 - x0) * self.style.pan_step_fraction
        with self._suspend_view_change_tracking():
            self.ax.set_xlim(x0 + direction * step, x1 + direction * step)
        self._refresh_title()
        self.fig.canvas.draw_idle()

    def _refresh_title(self) -> None:
        self.ax.set_title(self.status_line(), fontsize=self.style.status_fontsize)

    def zoom_at(self, direction: str, cursor_x: float | None, cursor_y: float | None) -> None:
        """Zoom in ('up') or out ('down'), pivoting on the *actual current* view.

        Always scales ax.get_xlim()/get_ylim() directly rather than
        recomputing a baseline from tracked state, so this respects
        wherever the view currently is - including a pan done via the
        toolbar's own Pan tool, not just our Shift+Left/Right.
        """
        factor = self.style.zoom_factor
        if direction == "up":
            self.zoom_scale /= factor
        else:
            self.zoom_scale *= factor
        # Clamp only against float overflow/underflow, not against "useful" zoom -
        # deep zoom at large step counts is where this looks best.
        self.zoom_scale = min(max(self.zoom_scale, self.style.zoom_scale_min), self.style.zoom_scale_max)

        ax = self.ax
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()

        if self.style.viewport_width is None and self.style.zoom_pivot != ZOOM_PIVOT_CURSOR:
            # Deliberate: the default variant always zooms toward the true
            # origin (the "moving spiral" effect), regardless of any pan.
            px, py = 0.0, 0.0
        elif cursor_x is not None and cursor_y is not None:
            px, py = cursor_x, cursor_y
        else:
            # No cursor (keyboard zoom): pivot on whatever's currently
            # centered on screen, so it doesn't snap away from a pan.
            px, py = (x0 + x1) / 2, (y0 + y1) / 2

        f = 1 / factor if direction == "up" else factor
        with self._suspend_view_change_tracking():
            ax.set_xlim(px + (x0 - px) * f, px + (x1 - px) * f)
            ax.set_ylim(py + (y0 - py) * f, py + (y1 - py) * f)
            ax.set_aspect("equal", adjustable="box")
        self._refresh_title()
        self.fig.canvas.draw_idle()

    def reset_zoom(self) -> None:
        """Reset manual zoom and release the manual-pan latch, back to full auto-fit."""
        self.zoom_scale = 1.0
        self._manual_pan = False
        self.apply_view_limits()
        self._refresh_title()
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

        # Capture the actual displayed center *before* clearing wipes it -
        # it may reflect a pan we never explicitly tracked (Shift+Left/Right,
        # or the toolbar's own Pan tool), which we want to keep respecting.
        manual_center_x = sum(ax.get_xlim()) / 2 if style.viewport_width is not None else None

        with self._suspend_view_change_tracking():
            ax.clear()
        # ax.clear() silently drops all registered callbacks, so re-attach
        # ours every time or external-view-change detection would only ever
        # work before the very first redraw().
        ax.callbacks.connect("xlim_changed", self._on_external_view_change)

        if not preserve_zoom:
            self.zoom_scale = 1.0
            # _manual_pan is deliberately *not* reset here: once the user has
            # taken manual control of the view (Shift+Left/Right, or the
            # toolbar's Pan/Zoom/Home/Back/Forward tools), it should keep
            # respecting that instead of snapping back to auto-tracking on
            # every step. Only reset_zoom() (R) releases the latch.

        self.apply_view_limits(manual_center_x=manual_center_x)

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
