from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]/'src'/'pdiag'/'static'
out=Path(__file__).resolve().parent
html=(root/'index.html').read_text().replace('<html lang="en">','<html lang="en" data-theme="dark">')
css=(root/'app.css').read_text()+'\n'+(out/'design.css').read_text()
js=(root/'app.js').read_text().replace('pdiag-units','pdiag-996-design-units')
# Replace instrument builders; retain the API client, diagnostics, and route lifecycle.
for name,next_marker in [('buildTach','function drawBands'),('setNeedle','// Readings arrive'),('buildDial','function drawDial')]:
    js=re.sub(r'function '+name+r'\([^)]*\) \{.*?(?='+re.escape(next_marker)+')','',js,flags=re.S)
js=js.rsplit('init();',1)[0]
js=js.replace('targetRpm = msg.values.rpm;', 'targetRpm = Number.isFinite(msg.values.rpm) ? msg.values.rpm : 0;')
js=js.replace('$("#rpm-num").textContent = text;', '$("#rpm-num").textContent = lastValues.rpm == null ? "–" : text;')
# Digital RPM and needles share the same frame and a shorter response time.
js=js.replace('const NEEDLE_TAU = 0.18;', 'const NEEDLE_TAU = 0.10;')
js=js.replace('const text = fmt(Math.round(shownRpm / 10) * 10);', 'const text = lastValues.rpm == null ? "–" : fmt(Math.round(shownRpm));')
js=js.replace('  easeDials(dt);', '  easeDials(dt);\n  digitalSpeed(dialState["g-speed"]?.shown ?? null);')
js=js.replace('  st.val.textContent = v == null ? "–" : fmt(v, 0);', '  const text = v == null ? "–" : fmt(v, 0);\n  if (st.val.textContent !== text) st.val.textContent = text;')
html=re.sub(r'<link[^>]*>\n','',html)
html=html.replace('<title>pdiag</title>','<title>996 · Instrument panel</title>\n<style>'+css+'</style>')
html=html.replace('<div class="car">','<div class="car"><div class="wordmark" aria-hidden="true">911</div><div>')
html=html.replace('  </div>\n  <div id="link-state"','  </div></div>\n  <div id="link-state"',1)
html=html.replace('>Live</a>','>Instruments</a>').replace('>Porsche data</a>','>DME data</a>').replace('>Car info</a>','>Vehicle</a>')
controls = '<div class="cockpit-actions" aria-label="Instrument controls"><div id="unit-slot"></div><button class="btn" id="night-btn" aria-pressed="false" title="Dim the instruments">Night</button><button class="btn" id="focus-btn" aria-pressed="false" title="Focus on the instruments (Escape to exit)">⛶ <span class="focus-label">Focus</span></button></div>'
html=html.replace('<nav class="tabs"', '<div class="nav-bar"><nav class="tabs"')
html=html.replace('</nav>', '</nav>'+controls+'</div>', 1)
html=html.replace('<button type="button" class="btn" id="codes-btn">Read again</button>', '<div class="code-actions"><button type="button" class="btn" id="codes-btn">Read again</button><button type="button" class="btn danger-btn" id="clear-codes-btn" disabled aria-describedby="clear-codes-note">Clear fault codes</button></div>')
html=html.replace('<div id="codes-body"', '<p class="clear-codes-note" id="clear-codes-note">Code clearing is not enabled on the current read-only connection.</p><div id="codes-body"')
html=html.replace('<div class="cluster">','<div class="instrument-stage"><div class="cluster">')
html=html.replace('      <div class="readouts"', '''      <div class="cluster-footer"><span class="data-fresh" id="freshness">Waiting for telemetry</span><span class="center-mark">911 · Type 996</span><span>Engine telemetry</span></div></div>
      <div class="telemetry-head"><h3>Engine at a glance</h3><span>Live readings · recent history</span></div><div class="readouts"''')
html=html.replace('<h3 id="all-h">Everything the engine computer reports</h3>', '<div class="telemetry-head"><h3 id="all-h">All engine readings</h3><span>Current values · updates live</span></div>')
html=html.replace('<dl class="all" id="all"><dt>Waiting for the first readings…</dt><dd></dd></dl>', '<table class="data-table" aria-labelledby="all-h"><thead><tr><th scope="col">Reading</th><th scope="col">Current value</th></tr></thead><tbody id="all"><tr><td colspan="2">Waiting for the first readings…</td></tr></tbody></table>')
html=html.replace('The colored marks around the dial are the six over-rev ranges. They fill in when the engine has recorded ignitions there.','996-inspired instruments, showing the values available from your engine computer. Auxiliary dials display intake temperature and engine load.')
dialog = """<dialog id="clear-dialog" aria-labelledby="clear-title" aria-describedby="clear-description">
  <h2 id="clear-title">Clear engine fault codes?</h2>
  <p id="clear-description">This erases stored emissions codes and freeze-frame data, and resets emissions readiness monitors. It does not repair the underlying fault.</p>
  <p>Park the car, turn the engine off, and leave the ignition on. The backend checks engine speed and road speed before clearing.</p>
  <p class="scope-note">Standard engine emissions codes only. Other modules and manufacturer-specific faults may remain.</p>
  <div class="dialog-actions"><button class="btn" id="clear-cancel" autofocus>Cancel</button><button class="btn danger-btn" id="clear-confirm">Clear engine codes</button></div>
</dialog>"""
html=html.replace('</main>', '</main>'+dialog)
html=html.replace('<div id="codes-body"', '<p id="clear-result" class="clear-result" role="status" hidden></p><div id="codes-body"')
controls_js=(out/'clear-controls.js').read_text()
instrument_js=(out/'instruments.js').read_text().rsplit('init();',1)[0]+controls_js+'\ninit().then(loadClearCapabilities);\n'
html=html.replace('<script src="app.js"></script>','<script>\n'+js+'\n'+instrument_js+'\n</script>')
(out/'dashboard-996.html').write_text(html)
# A separate JS extraction for syntax verification only.
(out/'check.js').write_text(js+'\n'+instrument_js)
print('Built standalone dashboard-996.html')
