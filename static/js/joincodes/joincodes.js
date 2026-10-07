/* Join codes (issuing): Copy, Cancel, the Make-a-code form, and the Home share dialog's "Make a new code".

     joincode:copy     (el, {code})        copy "OL-XXXX-XXXX"
     joincode:revoke   (el, {url, code})   open the cancel confirmation
     share:regenerate  (el, {org})         Home share dialog -> POST -> {code, expires} (home.js shows it)
   Making a code is a form post. The form below only adapts its own fields to what the chosen role allows;
   the server enforces the same rules (apps/joincodes/forms.py). */
(function () {
  'use strict';
  var OL = window.OL; if (!OL) return;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  OL.register('joincode:copy', function (el, d) {
    var done = function () { if (window.olToast) window.olToast('Join code copied.', 'success'); };
    var fail = function () { if (window.olToast) window.olToast("Couldn't copy. Select the code and copy it by hand.", 'error'); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(d.code).then(done, fail); else fail();
  });

  OL.register('joincode:revoke', function (el, d) {
    var dlg = $('#joincode-revoke-modal'); if (!dlg) return;
    $('#joincode-revoke-form', dlg).action = d.url;
    $('[data-revoke="code"]', dlg).textContent = d.code;
    window.olDialog.open(dlg);
  });

  // Home: Executives share one live code. "Make a new code" replaces it (the server cancels the earlier one).
  OL.register('share:regenerate', function (el, d) {
    return OL.post('/organizations/' + encodeURIComponent(d.org) + '/join-codes/quick/', {});
  });

  /* The form: a Committee Head code needs a committee, works once, and lives hours. */
  var form = $('[data-joincode-form]');
  if (form) {
    var role = $('select[name="role"]', form), committee = $('select[name="committee"]', form);
    var uses = $('select[name="max_uses"]', form), hours = $('select[name="hours"]', form);
    var list = function (a) { return (a || '').split(',').filter(Boolean); };
    var headHours = list(form.getAttribute('data-head-hours')), memberHours = list(form.getAttribute('data-member-hours'));
    var note = $('[data-head-note]', form), usesRow = $('[data-field="uses"]', form), cRow = $('[data-field="committee"]', form);

    function adapt() {
      var head = role.value === 'COMMITTEE_HEAD', allowed = head ? headHours : memberHours;
      Array.prototype.forEach.call(hours.options, function (o) { var ok = allowed.indexOf(o.value) !== -1; o.hidden = !ok; o.disabled = !ok; });
      if (allowed.indexOf(hours.value) === -1) hours.value = head ? allowed[allowed.length - 1] : (allowed.indexOf('168') !== -1 ? '168' : allowed[0]);
      if (head) { uses.value = '1'; }
      if (usesRow) usesRow.hidden = head;
      if (note) note.hidden = !head;
      if (committee && cRow) {
        var first = committee.options[0];                      // "All committees" only makes sense for a Member code
        if (first && first.value === '') { first.hidden = head; first.disabled = head; if (head && committee.value === '') committee.selectedIndex = Math.min(1, committee.options.length - 1); }
      }
    }
    if (role) { role.addEventListener('change', adapt); adapt(); }
  }

  // The server sent the page back with a mistake: reopen the dialog the person was using.
  var again = $('dialog[data-open-on-load]');
  if (again) window.olDialog.open(again);
})();
