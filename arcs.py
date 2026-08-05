#!/usr/bin/env python3
"""Render half-circle arcs above/below a number line, one step at a time.

Rule (see rules.py for the pluggable policy):
    Start at 0. For step n = 1, 2, 3, ...
      n odd  -> move right n steps, draw the arc above the line.
      n even -> move left n steps, draw the arc below the line.

Usage:
    python arcs.py            # start interactive, at step 0
    python arcs.py 25         # pre-run 25 steps, show the result, then stay interactive

Controls (once the plot window has focus):
    Right / Space / Enter (no digits typed)  -> advance by the remembered increment (starts at 1)
    digits (any length)                        -> build up a step count (e.g. 25)
    Enter (with digits typed)                  -> advance that many steps, and remember it as
                                                   the increment for future advance/undo
    Backspace                                  -> remove the last typed digit
    Left                                       -> undo by the remembered increment
    Up / Down arrow keys                       -> zoom in / out (same as mouse wheel;
                                                   pivot is code-configurable, default: origin)
    Mouse wheel                                -> zoom in / out
    Shift + Down / Shift + Up                  -> decrease / increase zoom speed
    C  (or the Colors button on the figure)    -> choose above/below arc colors
    Q / Escape                                 -> quit

The plot title always shows the live zoom speed and zoom scale alongside the
step/position info.
"""

import argparse
import sys

import matplotlib.pyplot as plt

from renderer import ArcRenderer
from rules import DEFAULT_RULE
from simulation import Simulation
from style import StyleConfig


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "n",
        type=int,
        nargs="?",
        default=None,
        help="Optional number of steps to run immediately before showing the window.",
    )
    parser.add_argument(
        "--max-label-step",
        type=int,
        default=None,
        help="Hide arc-size labels once current step exceeds this (default: 10).",
    )
    parser.add_argument(
        "--above-color",
        default=None,
        help="Initial color for arcs above the line (default: black).",
    )
    parser.add_argument(
        "--below-color",
        default=None,
        help="Initial color for arcs below the line (default: black).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    style = StyleConfig()
    if args.max_label_step is not None:
        style.max_step_to_render_arc_size = args.max_label_step
    if args.above_color:
        style.above_color = args.above_color
    if args.below_color:
        style.below_color = args.below_color

    sim = Simulation(rule=DEFAULT_RULE)
    if args.n:
        sim.advance(args.n)

    renderer = ArcRenderer(sim, style=style)

    def on_key(event) -> None:
        key = event.key

        if key in ("q", "escape"):
            plt.close(renderer.fig)
            return

        if key in ("c", "C"):
            renderer.open_color_settings()
            return

        if key == "up":
            renderer.zoom_at("up", None, None)
            return

        if key == "down":
            renderer.zoom_at("down", None, None)
            return

        if key == "shift+up":
            renderer.adjust_zoom_factor(0.01)
            return

        if key == "shift+down":
            renderer.adjust_zoom_factor(-0.01)
            return

        if key and key.isdigit():
            renderer.input_buffer += key
            renderer.redraw(preserve_zoom=True)
            return

        if key == "backspace":
            renderer.input_buffer = renderer.input_buffer[:-1]
            renderer.redraw(preserve_zoom=True)
            return

        if key in ("enter", "return"):
            if renderer.input_buffer:
                renderer.step_increment = int(renderer.input_buffer)
                renderer.input_buffer = ""
            sim.advance(renderer.step_increment)
            renderer.redraw()
            return

        if key in ("right", " ", "space"):
            renderer.input_buffer = ""
            sim.advance(renderer.step_increment)
            renderer.redraw()
            return

        if key == "left":
            renderer.input_buffer = ""
            sim.undo(renderer.step_increment)
            renderer.redraw()
            return

        # Unrecognized key: print it so an unexpected key string (e.g. a
        # backend reporting punctuation/modifiers differently) is easy to see
        # instead of the key silently doing nothing.
        print(f"[unhandled key] {key!r}", file=sys.stderr)

    def on_scroll(event) -> None:
        if event.inaxes != renderer.ax:
            return
        direction = "up" if event.button == "up" else "down"
        renderer.zoom_at(direction, event.xdata, event.ydata)

    renderer.fig.canvas.mpl_connect("key_press_event", on_key)
    renderer.fig.canvas.mpl_connect("scroll_event", on_scroll)
    renderer.redraw()
    plt.show()


if __name__ == "__main__":
    main()
