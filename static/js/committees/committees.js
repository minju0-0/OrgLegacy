/* Committees: the hooks behind Rename and Deactivate, and reopening a dialog that the server sent back with a mistake.

     committee:rename      (el, {url, name})   open the rename dialog for one committee
     committee:deactivate  (el, {url, name})   open the confirmation for one committee
   Adding a committee and reactivating one are plain form posts and need no script. */
(function () {
  'use strict';
  var OL = window.OL; if (!OL) return;
  var $ = function (s, r) { return (r || document).querySelector(s); };

  OL.register('committee:rename', function (el, d) {
    var dlg = $('#committee-rename-modal'), form = $('#committee-rename-form', dlg);
    form.action = d.url; $('input[type="text"]', form).value = d.name;
    $('[data-committee="name"]', dlg).textContent = d.name;
    $$err(form);
    window.olDialog.open(dlg);
  });

  OL.register('committee:deactivate', function (el, d) {
    var dlg = $('#committee-deactivate-modal');
    $('#committee-deactivate-form', dlg).action = d.url;
    $('[data-committee="name"]', dlg).textContent = d.name;
    window.olDialog.open(dlg);
  });

  function $$err(form) {   // a fresh rename starts clean: drop any mistake left from the last attempt
    Array.prototype.forEach.call(form.querySelectorAll('.field__error'), function (e) { e.remove(); });
    Array.prototype.forEach.call(form.querySelectorAll('.field--invalid'), function (f) { f.classList.remove('field--invalid'); });
  }

  // The server re-drew the page with a mistake: put the person back inside the dialog they were using.
  var again = $('dialog[data-open-on-load]');
  if (again) window.olDialog.open(again);
})();
