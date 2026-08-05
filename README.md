# arcs

Renders perfect half-circle arcs above and below a number line, following this rule:

- Start at 0.
- For step `n = 1, 2, 3, ...`:
  - if `n` is odd, move **right** `n` steps and draw the arc **above** the line.
  - if `n` is even, move **left** `n` steps and draw the arc **below** the line.

The line starts as `[-5, 5]`. Whenever a step would land outside the current
view, the line grows by 5 on each side (10 total), and the view zooms out so
the whole line and every arc drawn so far stay visible. Arcs are true circles
(the plot uses a 1:1 aspect ratio), and the window is freely resizable.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python arcs.py            # start interactive, at step 0
python arcs.py 25         # pre-run 25 steps, show the result, then stay interactive
```

## Controls

Click the plot window to give it focus, then:

| Key(s) | Action |
| --- | --- |
| `Right` / `Space` / `Enter` (no digits typed) | Advance by the remembered increment (starts at 1) |
| `0`-`9` | Build up a step count to jump by |
| `Enter` (with digits typed) | Advance that many steps, and remember that count as the increment |
| `Backspace` | Remove the last typed digit |
| `Left` | Undo by the remembered increment |
| `Q` / `Escape` | Quit |

The remembered increment is shown in the plot title. Typing a number and
confirming it with `Enter` updates that increment for both future advances
*and* undos, so e.g. typing `5` + `Enter` moves forward 5 steps, and every
subsequent bare `Enter`/`Right`/`Space` moves 5 more, or `Left` undoes 5,
until you type a new number.

## Design

The movement rule is intentionally decoupled from everything else:

- `rules.py` - `StepRule` is the pluggable policy that decides the next
  position for step `n`, given the current position and the set of positions
  visited so far. `AlternatingParityRule` (odd -> right, even -> left) is the
  only rule implemented today.
- `simulation.py` - `Simulation` holds step history and derives the growing
  view bounds. It is rule-agnostic: it just calls whatever `StepRule` it was
  given.
- `renderer.py` - `ArcRenderer` draws the number line, ticks, arcs, and
  markers. It derives "arc above" vs. "arc below" from the actual direction
  of movement (moved right -> above, moved left -> below), not from the
  parity of `n`, so it never needs to change when the rule changes.
- `style.py` - `StyleConfig` centralizes colors and sizing (arc colors default
  to the same value, but are independently configurable).

To try a different rule (e.g. a Recaman-sequence-style "try left, fall back to
right, no repeats" policy), add a new `StepRule` subclass in `rules.py` and
pass it into `Simulation(rule=...)` - no changes needed elsewhere.
