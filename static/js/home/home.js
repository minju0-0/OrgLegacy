/* Accession-number entry: eight cells (4 + 4), auto-advance, paste, backspace, arrows.
   Redeem opens the confirmation dialog. Joining is not wired (no flow exists yet). */
(function () {
  var root = document.querySelector('[data-accession]'); if (!root) return;
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
  sync();
})();
