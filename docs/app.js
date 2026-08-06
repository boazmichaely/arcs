// Shared Pyodide bootstrap for the arcs browser demo.
// Each page sets `window.ARCS_VARIANT` before loading this script.
(function () {
  const RAW_BASE = "https://raw.githubusercontent.com/boazmichaely/arcs/main/";
  const SOURCE_FILES = ["style.py", "colors.py", "rules.py", "simulation.py", "renderer.py", "arcs.py"];
  const variant = window.ARCS_VARIANT || "spiral";
  const statusEl = document.getElementById("status");

  async function main() {
    document.pyodideMplTarget = document.getElementById("mpl-target");
    setupTouchControls(variant);

    const pyodide = await loadPyodide();
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    await micropip.install(["matplotlib", "numpy"]);

    statusEl.textContent = "Fetching app source...";
    for (const name of SOURCE_FILES) {
      const resp = await fetch(RAW_BASE + name);
      if (!resp.ok) {
        throw new Error(`Failed to fetch ${name}: ${resp.status}`);
      }
      const text = await resp.text();
      pyodide.FS.writeFile("/home/pyodide/" + name, text);
    }

    statusEl.textContent = "Starting...";
    pyodide.globals.set("_arcs_variant", variant);
    await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, "/home/pyodide")

import arcs
arcs.main(["--variant", _arcs_variant])
`);
    statusEl.textContent = "";
  }

  main().catch((err) => {
    statusEl.textContent = "Failed to start: " + err;
    console.error(err);
  });

  // ---- Touch controls (no keyboard on mobile) --------------------------
  //
  // Matplotlib's browser backend turns physical keydown/keyup into the same
  // key_press/key_release events regardless of what fired them, so tapping
  // these buttons dispatches synthetic KeyboardEvents at the same element
  // real keyboard input would hit. This also gets hold-to-repeat for free,
  // since that's driven by keydown/keyup timing, not by any Python code.
  function getCanvasDiv() {
    const target = document.getElementById("mpl-target");
    return target ? target.querySelector('[tabindex="0"]') : null;
  }

  function dispatchKey(type, key, shiftKey) {
    const el = getCanvasDiv();
    if (!el) return;
    el.dispatchEvent(new KeyboardEvent(type, { key, shiftKey: !!shiftKey, bubbles: true, cancelable: true }));
  }

  function bindHold(btn, key, shiftKey) {
    let active = false;
    const press = (e) => {
      e.preventDefault();
      if (active) return;
      active = true;
      dispatchKey("keydown", key, shiftKey);
    };
    const release = () => {
      if (!active) return;
      active = false;
      dispatchKey("keyup", key, shiftKey);
    };
    btn.addEventListener("pointerdown", press);
    btn.addEventListener("pointerup", release);
    btn.addEventListener("pointerleave", release);
    btn.addEventListener("pointercancel", release);
  }

  function bindTap(btn, key) {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      dispatchKey("keydown", key, false);
      dispatchKey("keyup", key, false);
    });
  }

  function setupTouchControls(variant) {
    const style = document.createElement("style");
    style.textContent = `
      #touch-controls { display: none; }
      @media (pointer: coarse) {
        #touch-controls {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 1rem;
        }
      }
      #touch-controls button {
        flex: 1 1 auto;
        min-width: 4.5rem;
        padding: 0.9rem 0.5rem;
        font-size: 1.1rem;
        border: 1px solid #999;
        border-radius: 8px;
        background: #f7f7f7;
        touch-action: none;
        user-select: none;
      }
      #touch-controls button:active { background: #ddd; }
      #touch-controls .group { display: flex; gap: 0.5rem; width: 100%; }
    `;
    document.head.appendChild(style);

    const container = document.createElement("div");
    container.id = "touch-controls";

    function group(buttons) {
      const row = document.createElement("div");
      row.className = "group";
      for (const b of buttons) row.appendChild(b);
      container.appendChild(row);
    }

    function makeButton(label) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      return b;
    }

    const undoBtn = makeButton("\u25c0 Undo");
    const advanceBtn = makeButton("Advance \u25b6");
    bindHold(undoBtn, "ArrowLeft", false);
    bindHold(advanceBtn, "ArrowRight", false);
    group([undoBtn, advanceBtn]);

    const zoomOutBtn = makeButton("\u2212 Zoom");
    const resetBtn = makeButton("Reset");
    const zoomInBtn = makeButton("+ Zoom");
    bindHold(zoomOutBtn, "ArrowDown", false);
    bindTap(resetBtn, "r");
    bindHold(zoomInBtn, "ArrowUp", false);
    group([zoomOutBtn, resetBtn, zoomInBtn]);

    if (variant === "recaman") {
      const panLeftBtn = makeButton("\u21e4 Pan");
      const panRightBtn = makeButton("Pan \u21e5");
      bindHold(panLeftBtn, "ArrowLeft", true);
      bindHold(panRightBtn, "ArrowRight", true);
      group([panLeftBtn, panRightBtn]);
    }

    const target = document.getElementById("mpl-target");
    target.insertAdjacentElement("afterend", container);
  }
})();
