/* Profile: saves the details form over fetch and swaps in the server-rendered result,
   so the page does not reload. Falls back to a normal POST if JS is off. */
(function () {
  var form = document.getElementById('profile-form');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var btn = document.getElementById('save-profile-btn');
    var feedback = document.getElementById('inline-save-feedback');
    var label = btn.textContent;
    btn.disabled = true; btn.textContent = 'Saving…'; feedback.textContent = ''; feedback.className = 'form-feedback';

    try {
      var res = await fetch(window.location.href, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      var doc = new DOMParser().parseFromString(await res.text(), 'text/html');
      var fresh = doc.getElementById('profile-form');
      if (!fresh) { window.location.href = res.url; return; }

      form.innerHTML = fresh.innerHTML;
      var note = document.getElementById('inline-save-feedback');
      if (fresh.querySelector('.field--invalid, .alert--danger')) {
        note.textContent = 'Please correct the fields marked above.'; note.className = 'form-feedback is-error';
        var bad = form.querySelector('.field--invalid input'); if (bad) bad.focus();
      } else {
        note.textContent = 'Saved.'; note.className = 'form-feedback is-ok';
        if (window.olToast) window.olToast('Your profile has been updated.', 'success');
        // keep the name and email in the page header in step with what was saved
        var d = doc.querySelector('.profile-head');
        var h = document.querySelector('.profile-head');
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
})();
