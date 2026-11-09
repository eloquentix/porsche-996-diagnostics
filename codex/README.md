# Separate 996 instrument panel

Live dashboard: http://127.0.0.1:8999/#live

The self-contained solution is `dashboard-996.html`. Its HTML, CSS, JavaScript, and SVG instruments are all embedded. No external fonts, images, frameworks, or build dependencies are required.

`serve.py` serves the separate dashboard on port 8999 and forwards only the original app's read-only API endpoints to http://127.0.0.1:8998. Keep the original pdiag server running. The original project files are not modified.

Start or restart:

    uv run python codex/run_backend.py --port /dev/cu.usbserial-XXXX ui --http-port 8998 --no-browser
    python3 codex/serve.py

Optional animated preview, explicitly labelled as simulated:

    http://127.0.0.1:8999/?demo=1#live

Opening the HTML directly from disk also enters the labelled design preview. Use the served live URL for actual telemetry.

Controls: US/metric units, Night lighting, Focus mode (Escape exits), expandable engine readings, and the original diagnostic tabs. Signal loss dims held values and displays a reconnecting state. Fuel level and oil pressure are not fabricated; the auxiliary gauges show intake temperature and engine load.

The supporting `design.css`, `instruments.js`, and `build.py` allow rebuilding the single HTML file from the existing pdiag interface. They are not needed to run it. Built by a second AI agent (OpenAI Codex) as a design exploration of pdiag; kept here as a separate front end.

Validation: JavaScript syntax and Python compilation passed; the live proxy status endpoint and live browser readings were verified. US/metric, Night, and Focus controls were exercised in the browser. Original frontend SHA-256 hashes remained unchanged.

Derived from pdiag; GPL-3.0-or-later. See LICENSE.
