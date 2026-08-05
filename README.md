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

Arc-size labels show the signed step (`n` above, `-n` below). Labels are hidden
once the current step exceeds `max_step_to_render_arc_size` (default **10**);
undo back under that limit and they reappear.

## Credit

This project's rendering style (alternating semicircular arcs above/below a
number line) is inspired by the classic visualization of
[Recamán's sequence](https://en.wikipedia.org/wiki/Recam%C3%A1n%27s_sequence)
(OEIS [A005132](https://oeis.org/A005132)), invented by Colombian mathematician
Bernardo Recamán Santos. The arc-drawing method is credited to mathematician
Edmund Harriss, and it was popularized by Numberphile's 2018 video
["The Slightly Spooky Recamán Sequence"](https://www.youtube.com/watch?v=FGC5TdIiT9U).

The rule implemented here (alternate right/left by a fixed odd/even parity, no
"avoid negatives or repeats" fallback) is a simpler relative of Recamán's
actual rule - see the [Design](#design) section below for how to swap in a
true Recamán `StepRule` later.

## Install

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (cmd.exe):

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python arcs.py            # start interactive, at step 0
python arcs.py 25         # pre-run 25 steps, show the result, then stay interactive
python arcs.py --max-label-step 20
python arcs.py --above-color blue --below-color red
```

(On Windows use `python` the same way, once the venv above is activated.)

## Controls

Click the plot window to give it focus, then:

| Key(s) | Action |
| --- | --- |
| `Right` / `Space` / `Enter` (no digits typed) | Advance by the remembered increment (starts at 1) |
| Digit keys (`0`-`9`, any length) | Build a multi-digit step count (e.g. type `2` then `5` for 25) |
| `Enter` (with digits typed) | Advance that many steps, and remember that count as the increment |
| `Backspace` | Remove the last typed digit |
| `Left` | Undo by the remembered increment |
| `Up` / `Down` | Zoom in / out (pivot: origin by default; change `StyleConfig.zoom_pivot` in code) |
| Mouse wheel | Same zoom as `Up` / `Down` |
| `[` / `]` | Decrease / increase the base zoom factor, live |
| `-` / `=` | Decrease / increase zoom-out damping, live |
| `C` or the **Colors** button | Choose above-arc and below-arc colors |
| `Q` / `Escape` | Quit |

The remembered increment is shown in the plot title. Typing a number and
confirming it with `Enter` updates that increment for both future advances
*and* undos, so e.g. typing `5` + `Enter` moves forward 5 steps, and every
subsequent bare `Enter`/`Right`/`Space` moves 5 more, or `Left` undoes 5,
until you type a new number.

### Zoom sensitivity

The per-step zoom factor (`StyleConfig.zoom_factor`, default `1.08`) shrinks
smoothly and continuously as you zoom further out - each step changes it
*less* the farther the view is from the default auto-fit, so a held key
doesn't blow past content once you're already zoomed way out.

A blue debug line under the plot always shows the live `zoom_scale`,
`effective_factor`, base `zoom_factor`, and `zoom_out_damping`. Press
`[` / `]` to tune the base factor and `-` / `=` to tune the damping while
watching the numbers and the zoom feel change, then bake whatever you land on
into `StyleConfig` in `style.py` (or just tell me the values and I'll set
them as the defaults):

- `zoom_factor` - the base per-step factor right at the default view.
- `zoom_out_damping` - how strongly zoomed-out steps slow down (`0` disables
  damping and uses a constant `zoom_factor` everywhere).

### Matplotlib toolbar

These buttons affect the **view**, not the step simulation:

| Button | What it does |
| --- | --- |
| Home | Reset zoom/pan to the last auto-fit view |
| Back / Forward | Undo / redo zoom-pan history |
| Pan (cross arrows) | Click-drag to pan |
| Zoom (magnifier) | Drag a rectangle to zoom |
| Configure subplots | `wspace` / `hspace` - spacing between panes in a **multi-plot** grid. This app has one axes, so changing them has no effect. |
| Save | Save the figure; suggested name is `Number_Line_Arcs-<n>.png` where `n` is the last rendered step |

On the default **macosx** backend, that toolbar is native and fixed by matplotlib - you cannot add custom icons to it without switching to a Qt or Tk backend (which also need those libraries installed). Arc colors therefore live on the figure as a **Colors** button (and the `C` key), not on the toolbar.

Step advance / undo is only via the keyboard controls above.

### Colors

Press `C` or click **Colors**. On macOS this opens the system color picker (no tkinter required). If that is unavailable, a small swatch window is used instead.

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
- `style.py` - `StyleConfig` centralizes colors, label cutoff, and zoom
  pivot (`ZOOM_PIVOT_ORIGIN` by default; set to `ZOOM_PIVOT_CURSOR` in code
  to zoom toward the mouse).

To try a different rule (e.g. a Recaman-sequence-style "try left, fall back to
right, no repeats" policy), add a new `StepRule` subclass in `rules.py` and
pass it into `Simulation(rule=...)` - no changes needed elsewhere.
