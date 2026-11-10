/* Members: the hooks behind Remove and Leave on the roster, and the Home leave dialog.

     member:remove     (el, {url, name})   open the confirmation for one person (roster)
     member:leave      (el)                open the leave confirmation (roster)
     org:leave-confirm (el, {org})         Home "Leave organization" dialog -> POST, then Home
   Removing and leaving are form posts from their dialogs, so a failed request never leaves the page half changed. */
(function () {
  'use strict';
  var OL = window.OL; if (!OL) return;
  var $ = function (s, r) { return (r || document).querySelector(s); };

  OL.register('member:remove', function (el, d) {
    var dlg = $('#member-remove-modal'); if (!dlg) return;
    $('#member-remove-form', dlg).action = d.url;
    $('[data-member="name"]', dlg).textContent = d.name;
    window.olDialog.open(dlg);
  });

  OL.register('member:leave', function () { var dlg = $('#member-leave-modal'); if (dlg) window.olDialog.open(dlg); });

  // Home: the dialog is already there; this is what its "Leave organization" button does.
  OL.register('org:leave-confirm', function (el, d) {
    return OL.post('/organizations/' + encodeURIComponent(d.org) + '/members/leave/', {})
      .then(function (r) { window.location.assign(r.url); });   // the confirmation toast is queued server-side
  });
})();
