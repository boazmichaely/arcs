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
    0-9                                        -> build up a step count to jump by
    Enter (with digits typed)                  -> advance that many steps, and remember it as
                                                   the increment for future advance/undo
    Backspace                                  -> remove the last typed digit
    Left                                       -> undo by the remembered increment
    Q / Escape                                 -> quit
"""

import argparse
import sys

import matplotlib.pyplot as plt

from renderer import ArcRenderer
from rules import DEFAULT_RULE
from simulation import Simulation


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "n",
        type=int,
        nargs="?",
        default=None,
        help="Optional number of steps to run immediately before showing the window.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    sim = Simulation(rule=DEFAULT_RULE)
    if args.n:
        sim.advance(args.n)

    renderer = ArcRenderer(sim)

    def on_key(event) -> None:
        key = event.key

        if key in ("q", "escape"):
            plt.close(renderer.fig)
            return

        if key and key.isdigit():
            renderer.input_buffer += key
            renderer.redraw()
            return

        if key == "backspace":
            renderer.input_buffer = renderer.input_buffer[:-1]
            renderer.redraw()
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

    renderer.fig.canvas.mpl_connect("key_press_event", on_key)
    renderer.redraw()
    plt.show()


if __name__ == "__main__":
    main()
