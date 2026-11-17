/* Shell hooks loaded on every app page:
     notifications:mark-all-read   (el)   mark them read on the server, then clear the badge and the unread rows
     notifications:view-all        (el)   load all recent notifications into the popover list
     OL.search.connect             (fn)   connect the topbar search and mobile search sheet to /search/
*/
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

  OL.register('notifications:view-all', function (el) {
    el.disabled = true;
    return fetch('/notifications/all/', { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { if (!r.ok) throw new Error('Could not load notifications.'); return r.json(); })
      .then(function (data) {
        var list = document.querySelector('#bell-panel .popover__list');
        if (list && data && Array.isArray(data.notifications)) {
          list.innerHTML = '';
          data.notifications.forEach(function (n) {
            var li = document.createElement('li');
            li.className = 'note-row' + (n.unread ? ' is-unread' : '');
            var a = document.createElement('a');
            a.className = 'note-row__link';
            a.href = n.url || '/home/';
            var text = document.createElement('span');
            text.className = 'note-row__text';
            if (n.unread) {
              var sr = document.createElement('span');
              sr.className = 'sr-only';
              sr.textContent = 'Unread: ';
              text.appendChild(sr);
            }
            text.appendChild(document.createTextNode(n.text || ''));
            var meta = document.createElement('span');
            meta.className = 'note-row__meta';
            var org = document.createElement('span');
            org.textContent = n.org || '';
            var ago = document.createElement('span');
            ago.className = 't-mono';
            ago.textContent = n.ago || '';
            meta.appendChild(org);
            meta.appendChild(ago);
            a.appendChild(text);
            a.appendChild(meta);
            li.appendChild(a);
            list.appendChild(li);
          });
        }
        var foot = el.closest('.popover__foot');
        if (foot) foot.hidden = true;
      })
      .catch(function (err) { el.disabled = false; if (window.olToast) window.olToast(err.message, 'error'); });
  });

  if (OL.search && !document.querySelector('[data-home][data-preview]')) {
    OL.search.connect(function (query) {
      return fetch('/search/?q=' + encodeURIComponent(query), {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      }).then(function (r) {
        if (!r.ok) throw new Error('Search failed');
        return r.json();
      });
    });
  }
})();
