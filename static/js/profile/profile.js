/* Profile screen.
   Works as is:   saving the details form without a page reload; the photo dialog up to Save
                  (choose or drop a file, it is checked and previewed).
   Needs logic:   register with OL.register (see docs/PROFILE_SETTINGS.md)
     profile:avatar-save    (el, {file})   upload the File; resolve to close, reject(Error('message')) to show it
     profile:avatar-remove  (el)           remove the photo
     org:open               (el, {org})    open an organization from the shelf or the ledger */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };

  /* ---------------- Save the details form over fetch ---------------- */
  var form = document.getElementById('profile-form');
  if (form) form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var btn = document.getElementById('save-profile-btn');
    var feedback = document.getElementById('inline-save-feedback');
    var label = btn.textContent;
    btn.disabled = true; btn.textContent = 'Saving\u2026'; feedback.textContent = ''; feedback.className = 'form-feedback';

    try {
      var res = await fetch(window.location.href, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      var doc = new DOMParser().parseFromString(await res.text(), 'text/html');
      var fresh = doc.getElementById('profile-form');
      if (!fresh) { window.location.href = res.url; return; }

      form.innerHTML = fresh.innerHTML;
      var note = document.getElementById('inline-save-feedback');
      if (fresh.querySelector('.field--invalid, .alert--danger')) {
        note.textContent = 'Please correct the fields marked above.'; note.className = 'form-feedback is-error';
        var bad = form.querySelector('.field--invalid input, .field--invalid textarea, .field--invalid select'); if (bad) bad.focus();
      } else {
        note.textContent = 'Saved.'; note.className = 'form-feedback is-ok';
        if (window.olToast) window.olToast('Your profile has been updated.', 'success');
        // keep the header and the topbar in step with what was saved
        var d = doc.querySelector('.profile-head'), h = document.querySelector('.profile-head');
        if (d && h) h.innerHTML = d.innerHTML;
        var tb = doc.querySelector('.topbar__user'), cur = document.querySelector('.topbar__user');
        if (tb && cur) cur.innerHTML = tb.innerHTML;
      }
    } catch (err) {
      feedback.textContent = 'Unable to save changes. Please try again.'; feedback.className = 'form-feedback is-error';
    } finally {
      var b = document.getElementById('save-profile-btn');
      if (b) { b.disabled = false; b.textContent = label; }
    }
  });

  /* ---------------- Photo dialog ---------------- */
  var root = $('[data-avatar]'); if (!root) return;
  var dlg = root.closest('dialog'), input = $('[data-avatar-input]', root), save = $('[data-avatar-save]', root);
  var fb = $('[data-avatar-feedback]', root), preview = $('[data-avatar-preview]', root), drop = $('[data-avatar-drop]', root);
  var HINT = 'You can also drop a photo here.', MAX = 2 * 1024 * 1024, OK = ['image/jpeg', 'image/png', 'image/webp'];
  var file = null, url = null, original = preview.innerHTML;
  function say(t, kind) { fb.textContent = t; fb.className = 'form-feedback' + (kind ? ' is-' + kind : ''); }

  function setFile(f) {
    if (!f) return;
    if (OK.indexOf(f.type) === -1) { say('Use a JPG, PNG or WebP photo.', 'error'); return; }
    if (f.size > MAX) { say('That photo is ' + (f.size / 1048576).toFixed(1) + ' MB. The limit is 2 MB.', 'error'); return; }
    file = f; if (url) URL.revokeObjectURL(url); url = URL.createObjectURL(f);
    preview.innerHTML = '<img class="avatar__img" alt="">'; $('img', preview).src = url;
    say(f.name, 'ok'); save.disabled = false;
  }
  function reset() {
    file = null; if (url) { URL.revokeObjectURL(url); url = null; }
    preview.innerHTML = original; input.value = ''; save.disabled = true; say(HINT, '');
  }

  input.addEventListener('change', function () { setFile(input.files && input.files[0]); });
  ['dragenter', 'dragover'].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.add('is-drag'); }); });
  ['dragleave', 'drop'].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.remove('is-drag'); if (t === 'drop') setFile(e.dataTransfer.files && e.dataTransfer.files[0]); }); });

  save.addEventListener('click', function () {
    if (!file) return;
    save.disabled = true;
    var kept = OL.run('profile:avatar-save', save, { file: file }, function () { window.olDialog.close(dlg); }, function (m) { say(m, 'error'); save.disabled = false; });
    if (!kept) save.disabled = false;     // not connected: toast shown, the chosen photo stays
  });
  var rm = $('[data-avatar-remove]', root);
  if (rm) rm.addEventListener('click', function () {
    OL.run('profile:avatar-remove', rm, {}, function () { window.olDialog.close(dlg); }, function (m) { say(m, 'error'); });
  });
  dlg.addEventListener('close', reset);
})();
