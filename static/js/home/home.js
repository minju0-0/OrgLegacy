/* Home: the two modals opened from the page header.
   1. Accession number: eight cells (4 + 4), auto-advance, paste, backspace, arrows.
      Redeem opens the confirmation dialog on top. Joining is not wired (no flow exists yet).
   2. Charter: validates the form and says plainly that chartering is not connected yet. */
(function () {
  var root = document.querySelector('[data-accession]');
  if (!root) return;
  var dlg = root.closest('dialog');
  var cells = Array.prototype.slice.call(root.querySelectorAll('[data-acc-cell]'));
  var form = root.querySelector('#accession-form');
  var btn = root.querySelector('#accession-submit'), fb = root.querySelector('#accession-feedback');
  var HINT = 'Paste works too.';
  var clean = function (s) { return String(s).toUpperCase().replace(/[^A-Z0-9]/g, ''); };
  function code() { return cells.map(function (c) { return c.value; }).join(''); }
  function say(text, kind) { fb.textContent = text; fb.className = 'form-feedback' + (kind ? ' is-' + kind : ''); }
  function shake(c) { c.classList.remove('is-shake'); void c.offsetWidth; c.classList.add('is-shake'); }
  function sync() {
    cells.forEach(function (c) { c.classList.toggle('is-filled', !!c.value); });
    var done = code().length === cells.length; btn.disabled = !done;
    say(done ? 'Ready to redeem.' : HINT, done ? 'ok' : '');
  }
  function reset() { cells.forEach(function (c) { c.value = ''; }); sync(); }

  cells.forEach(function (c, i) {
    c.addEventListener('input', function () {
      var raw = c.value, v = clean(raw); c.value = v.slice(-1);
      if (raw && !v) shake(c);
      if (c.value && cells[i + 1]) cells[i + 1].focus(); sync();
    });
    c.addEventListener('keydown', function (e) {
      if (e.key === 'Backspace' && !c.value && cells[i - 1]) { cells[i - 1].focus(); cells[i - 1].value = ''; sync(); e.preventDefault(); }
      else if (e.key === 'ArrowLeft' && cells[i - 1]) cells[i - 1].focus();
      else if (e.key === 'ArrowRight' && cells[i + 1]) cells[i + 1].focus();
    });
    c.addEventListener('focus', function () { c.select(); });
    c.addEventListener('paste', function (e) {
      e.preventDefault();
      var t = clean((e.clipboardData || window.clipboardData).getData('text'));
      if (t.indexOf('OL') === 0 && t.length > cells.length) t = t.slice(2);
      t.slice(0, cells.length).split('').forEach(function (ch, k) { cells[k].value = ch; });
      cells[Math.min(t.length, cells.length - 1)].focus(); sync();
    });
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var c = code();
    if (c.length < cells.length) {
      cells.forEach(function (x) { if (!x.value) shake(x); });
      say('Enter all eight characters.', 'error'); (cells.filter(function (x) { return !x.value; })[0] || cells[0]).focus(); return;
    }
    var d = document.getElementById('join-modal'); if (!d) return;
    d.querySelector('[data-join="code"]').textContent = 'OL-' + c.slice(0, 4) + '-' + c.slice(4);
    if (window.olDialog) window.olDialog.open(d); else if (d.showModal) d.showModal();
  });

  // Opening: land on the first empty cell. Closing: start clean next time.
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-dialog-open="accession-modal"]')) setTimeout(function () { (cells.filter(function (x) { return !x.value; })[0] || cells[0]).focus(); }, 60);
    if (e.target.closest('[data-join-confirm]') && window.olDialog) window.olDialog.close(dlg);   // preview: finish the whole flow
  });
  dlg.addEventListener('close', reset);
  sync();
})();

(function () {
  var panel = document.querySelector('[data-charter]');
  if (!panel) return;
  var form = panel.querySelector('#charter-form');
  var name = panel.querySelector('#charter-name'), acr = panel.querySelector('#charter-acronym'), ay = panel.querySelector('#charter-ay');
  var fb = panel.querySelector('#charter-feedback');
  function say(t, kind) { fb.textContent = t; fb.className = 'form-feedback' + (kind ? ' is-' + kind : ''); }

  acr.addEventListener('input', function () { acr.value = acr.value.toUpperCase().replace(/[^A-Z0-9]/g, ''); });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!name.value.trim()) { say('Give the organization a name.', 'error'); name.focus(); return; }
    if (!/^\d{4}\s*[-–]\s*\d{4}$/.test(ay.value.trim())) { say('Enter the A.Y. as two years, like 2026-2027.', 'error'); ay.focus(); return; }
    say('Preview only: chartering is not connected yet, so nothing was created.', '');
  });
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-dialog-open="charter-modal"]')) setTimeout(function () { name.focus(); }, 60);
  });
  panel.closest('dialog').addEventListener('close', function () { form.reset(); say('', ''); });
})();
