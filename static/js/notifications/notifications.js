/* Notifications: the bell hook, loaded on every app page.

     notifications:mark-all-read   (el)   mark them read on the server, then clear the badge and the unread rows
   Opening a row is a plain link (notifications:go marks it read), so notifications:open-item is never needed.
   "View all notifications" has no page yet and still answers "That isn't connected yet." */
(function () {
  'use strict';
  var OL = window.OL; if (!OL) return;

  OL.register('notifications:mark-all-read', function (el) {
    return OL.post('/notifications/read-all/', {}).then(function () {
      document.querySelectorAll('.note-row.is-unread').forEach(function (r) { r.classList.remove('is-unread'); });
      document.querySelectorAll('.note-row .sr-only').forEach(function (s) { s.remove(); });
      var badge = document.querySelector('.topbar__badge'); if (badge) badge.remove();
      var bell = document.querySelector('.topbar__bell'); if (bell) bell.setAttribute('aria-label', 'Notifications');
      el.disabled = true;
    }).catch(function (err) { if (window.olToast) window.olToast(err.message, 'error'); });
  });
})();
