/* Event logs: the hooks behind Edit and Delete on a log.

     eventlog:edit    (el, {url, what, lessons})   open the edit dialog with this log's words in it
     eventlog:delete  (el, {url})                  open the delete confirmation
   Adding a log is a plain form post and needs no script. */
(function () {
  'use strict';
  var OL = window.OL; if (!OL) return;
  var $ = function (s, r) { return (r || document).querySelector(s); };

  OL.register('eventlog:edit', function (el, d) {
    var dlg = $('#eventlog-edit-modal'), form = $('#eventlog-edit-form', dlg);
    form.action = d.url;
    $('textarea[name="what_happened"]', form).value = d.what || '';
    $('textarea[name="challenges_lessons"]', form).value = d.lessons || '';
    window.olDialog.open(dlg);
  });

  OL.register('eventlog:delete', function (el, d) {
    var dlg = $('#eventlog-delete-modal');
    $('#eventlog-delete-form', dlg).action = d.url;
    window.olDialog.open(dlg);
  });
})();
