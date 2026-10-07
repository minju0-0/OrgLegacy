/* Join: the two hooks behind the Home "Enter join code" dialog.

     join:preview  (el, {code})   ask what the code is for. Resolves {summary}, which home.js shows in the confirm step.
     join:submit   (el, {code})   redeem it, then open the organization. Reject with Error('message') to show it under the cells. */
(function () {
  'use strict';
  var OL = window.OL; if (!OL) return;

  OL.register('join:preview', function (el, d) { return OL.post('/join/preview/', { code: d.code }); });

  OL.register('join:submit', function (el, d) {
    return OL.post('/join/redeem/', { code: d.code })
      .then(function (r) { window.location.assign(r.url); });   // the welcome toast is queued server-side
  });
})();
