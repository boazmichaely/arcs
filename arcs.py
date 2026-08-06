#!/usr/bin/env python3
"""Render half-circle arcs above/below a number line, one step at a time.

Default rule (see rules.py for the pluggable policies, and VARIANTS for the
other bundled sequence):
    Start at 0. For step n = 1, 2, 3, ...
      n odd  -> move right n steps, draw the arc above the line.
      n even -> move left n steps, draw the arc below the line.

Usage:
    python arcs.py                          # start interactive, at step 0
    python arcs.py 25                       # pre-run 25 steps, show the result, then stay interactive
    python arcs.py --variant recaman        # render Recaman's sequence instead
    python arcs.py --variant recaman --no-smallest-missing

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
    Shift + Left / Shift + Right               -> pan the viewport (only variants with a
                                                   fixed-width viewport, e.g. recaman)
    C                                          -> choose the two arc colors
    Q / Escape                                 -> quit

The plot title always shows the live zoom speed and zoom scale alongside the
step/position info.
"""

import argparse
import sys

import matplotlib.pyplot as plt

from renderer import ArcRenderer
from rules import VARIANTS
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
        "--variant",
        choices=sorted(VARIANTS),
        default="default",
        help="Which sequence/coloring rule to use (default: default). See rules.py VARIANTS.",
    )
    parser.add_argument(
        "--max-label-step",
        type=int,
        default=None,
        help="Hide arc-size labels once current step exceeds this (default: 10).",
    )
    parser.add_argument(
        "--color-a",
        default=None,
        help="Initial color for group-A arcs (default: blue).",
    )
    parser.add_argument(
        "--color-b",
        default=None,
        help="Initial color for group-B arcs (default: red).",
    )
    parser.add_argument(
        "--smallest-missing",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show the smallest not-yet-visited number in the status line "
        "(default: on for variants that track it, e.g. recaman).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    variant = VARIANTS[args.variant]

    style = StyleConfig(**variant["style"])
    if args.max_label_step is not None:
        style.max_step_to_render_arc_size = args.max_label_step
    if args.color_a:
        style.color_a = args.color_a
    if args.color_b:
        style.color_b = args.color_b
    if args.smallest_missing is not None:
        style.show_smallest_missing = args.smallest_missing

    sim = Simulation(rule=variant["rule"], orientation=variant["orientation"])
    if args.n:
        sim.advance(args.n)

    renderer = ArcRenderer(sim, style=style, color_rule=variant["color_rule"])

    def on_key(event) -> None:
        key = event.key

        if key in ("q", "escape"):
            plt.close(renderer.fig)
            return

        if key in ("c", "C"):
            renderer.open_color_settings()
            return

        if key in ("r", "R"):
            renderer.reset_zoom()
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

        if key == "shift+left":
            renderer.pan_by(-1)
            return

        if key == "shift+right":
            renderer.pan_by(1)
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
