// Shared Pyodide bootstrap for the arcs browser demo.
// Each page sets `window.ARCS_VARIANT` before loading this script.
(function () {
  const RAW_BASE = "https://raw.githubusercontent.com/boazmichaely/arcs/main/";
  const SOURCE_FILES = ["style.py", "colors.py", "rules.py", "simulation.py", "renderer.py", "arcs.py"];
  const variant = window.ARCS_VARIANT || "spiral";
  const statusEl = document.getElementById("status");

  async function main() {
    document.pyodideMplTarget = document.getElementById("mpl-target");

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
})();
