"""Color-picker helpers that work without tkinter (common on Homebrew / venv Python).

Order of attempts:
1. tkinter colorchooser (when present)
2. macOS native \"choose color\" via osascript
3. A small matplotlib swatch window (always available)
"""

from __future__ import annotations

import subprocess
import sys


def _normalize_hex(color: str) -> str:
    color = color.strip()
    if not color.startswith("#") and len(color) == 6:
        color = "#" + color
    return color


def _ask_tkinter(title: str, initial: str) -> str | None:
    try:
        import tkinter as tk
        from tkinter import colorchooser
    except ImportError:
        return None

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        result = colorchooser.askcolor(color=initial, title=title, parent=root)
    finally:
        root.destroy()
    if not result or not result[1]:
        return None
    return result[1]


def _ask_osascript(title: str, initial: str) -> str | None:
    """macOS native color picker. Returns #rrggbb or None.

    AppleScript's `choose color` has no title/prompt parameter of its own, so
    two calls in a row look identical with no indication of which value is
    being set. We precede it with a `display dialog` naming what's being
    picked, so it reads as one guided step instead of two unlabeled pickers.
    """
    if sys.platform != "darwin":
        return None

    # Convert #rrggbb (or a named color) to 16-bit RGB for AppleScript.
    try:
        from matplotlib.colors import to_rgb

        r, g, b = to_rgb(initial)
        ri, gi, bi = int(r * 65535), int(g * 65535), int(b * 65535)
    except ValueError:
        ri = gi = bi = 0

    safe_title = title.replace('"', "'")
    script = (
        'tell application "System Events" to activate\n'
        f'display dialog "Next: pick a color for {safe_title}." '
        f'with title "{safe_title}" buttons {{"Cancel", "Choose Color…"}} '
        'default button 2\n'
        f"set theColor to choose color default color {{{ri}, {gi}, {bi}}}\n"
        "set r to item 1 of theColor\n"
        "set g to item 2 of theColor\n"
        "set b to item 3 of theColor\n"
        'return (r as text) & "," & (g as text) & "," & (b as text)\n'
    )
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    parts = proc.stdout.strip().split(",")
    if len(parts) != 3:
        return None
    try:
        r, g, b = (int(p.strip()) for p in parts)
    except ValueError:
        return None
    return f"#{r // 256:02x}{g // 256:02x}{b // 256:02x}"


# A compact palette for the matplotlib fallback.
_SWATCHES = [
    "black",
    "dimgray",
    "gray",
    "crimson",
    "tab:red",
    "tab:orange",
    "tab:green",
    "tab:blue",
    "tab:purple",
    "navy",
    "teal",
    "gold",
]


def _ask_swatches(title: str, initial: str) -> str | None:
    """Blocking matplotlib window: click a swatch, or press Enter to keep current."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.widgets import Button

    chosen: dict[str, str | None] = {"color": None}
    fig, ax = plt.subplots(figsize=(5.2, 2.4))
    fig.canvas.manager.set_window_title(title)
    ax.set_xlim(0, len(_SWATCHES))
    ax.set_ylim(0, 2.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{title}\ncurrent: {initial}  (click a swatch, or Cancel)", fontsize=10)

    for i, name in enumerate(_SWATCHES):
        ax.add_patch(Rectangle((i + 0.1, 0.8), 0.8, 0.8, facecolor=name, edgecolor="black"))
        ax.text(i + 0.5, 0.55, name.replace("tab:", ""), ha="center", va="top", fontsize=7)

    def on_click(event) -> None:
        if event.inaxes != ax or event.xdata is None:
            return
        idx = int(event.xdata)
        if 0 <= idx < len(_SWATCHES):
            chosen["color"] = _SWATCHES[idx]
            plt.close(fig)

    cancel_ax = fig.add_axes([0.35, 0.05, 0.3, 0.15])
    cancel_btn = Button(cancel_ax, "Cancel")
    cancel_btn.on_clicked(lambda _evt: plt.close(fig))

    fig.canvas.mpl_connect("button_press_event", on_click)
    plt.show(block=True)
    return chosen["color"]


def ask_color(title: str, initial: str = "black") -> str | None:
    """Ask the user for a color. Returns a matplotlib-friendly color string, or None."""
    initial = _normalize_hex(initial) if initial.startswith("#") or len(initial) == 6 else initial

    for attempt in (_ask_tkinter, _ask_osascript, _ask_swatches):
        try:
            result = attempt(title, initial)
        except Exception as exc:  # noqa: BLE001 - fall through to next backend
            print(f"Color picker ({attempt.__name__}) failed: {exc}", file=sys.stderr)
            continue
        if result:
            return result
    return None


def ask_two_colors(label_a: str, label_b: str, color_a: str, color_b: str) -> tuple[str, str]:
    """Prompt for color A then color B; unchanged if a prompt is cancelled."""
    new_a = ask_color(f"{label_a} color", color_a) or color_a
    new_b = ask_color(f"{label_b} color", color_b) or color_b
    return new_a, new_b
