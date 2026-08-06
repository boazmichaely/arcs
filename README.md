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

The default rule here (alternate right/left by a fixed odd/even parity, no
"avoid negatives or repeats" fallback) is a simpler relative of Recamán's
actual rule. Run with `--variant recaman` for the real thing - see
[Variants](#variants) below.

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
python arcs.py                    # start interactive, at step 0
python arcs.py 25                 # pre-run 25 steps, show the result, then stay interactive
python arcs.py --max-label-step 20
python arcs.py --color-a blue --color-b red
python arcs.py 30 --variant recaman
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
| `Shift+Down` / `Shift+Up` | Decrease / increase zoom speed, live |
| `Shift+Left` / `Shift+Right` | Pan the viewport left / right (only variants with a fixed-width viewport, e.g. `recaman`) |
| `C` or the **Colors** button | Choose the two arc colors |
| `Q` / `Escape` | Quit |

The remembered increment is shown in the plot title. Typing a number and
confirming it with `Enter` updates that increment for both future advances
*and* undos, so e.g. typing `5` + `Enter` moves forward 5 steps, and every
subsequent bare `Enter`/`Right`/`Space` moves 5 more, or `Left` undoes 5,
until you type a new number.

### Zoom sensitivity

`zoom speed` is how much the view size changes per `Up`/`Down`/scroll press,
shown in the title as a percentage (default `+5.0%/press`, from
`StyleConfig.zoom_factor = 1.05`). Tune it live with `Shift+Up`/`Shift+Down`
and watch the title, then tell me what felt right and I'll set it as the
default in `style.py`.

## Variants

`--variant` bundles a movement rule with an arc-orientation rule and a
coloring rule (see [Design](#design)):

| `--variant` | Movement | Arc side (above/below) | Color |
| --- | --- | --- | --- |
| `default` | Odd `n` right, even `n` left | Follows movement direction | Follows arc side |
| `recaman` | Recamán's sequence: try `pos - n` (if non-negative and unvisited), else `pos + n` | Alternates by step parity (odd above, even below), independent of movement | Follows rotational direction: **clockwise** if arc side agrees with movement direction (above-and-right, or below-and-left), **counter-clockwise** otherwise |

`recaman` also uses a fixed-width, pannable viewport (`Shift+Left`/`Right`)
instead of always fitting the whole line, since the sequence can range far
wider than it is tall.

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

A variant is three independent, pluggable policies, all defined in
`rules.py`, plus any `StyleConfig` overrides it needs:

- `StepRule` - given step `n`, the current position, and the set of
  positions visited so far, where do we move to next? (`AlternatingParityRule`,
  `RecamanRule`)
- `OrientationRule` - given the move, is the arc drawn above or below the
  line? (`DirectionOrientation`: follows movement direction; `AlternatingOrientation`:
  follows step parity)
- `ColorRule` - given the arc's orientation and actual move direction, which
  of the two configured colors (`StyleConfig.color_a` / `color_b`) does it
  use? (`SideColorRule`: by orientation; `ClockwiseColorRule`: by rotational
  direction)

`rules.py`'s `VARIANTS` dict bundles a named triple of these plus style
overrides (e.g. `recaman`'s fixed-width viewport) - `arcs.py --variant`
just looks up a name in it.

`simulation.py` and `renderer.py` are policy-agnostic: `Simulation` calls
whatever `StepRule`/`OrientationRule` it was given and stores the results on
each `Step`; `ArcRenderer` calls whatever `ColorRule` it was given. Neither
needs to change when adding a new variant.

To add another variant, add the new rule(s) to `rules.py` and a new entry to
`VARIANTS` - no changes needed in `simulation.py` or `renderer.py`.
