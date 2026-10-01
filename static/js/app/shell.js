/* App-screen behaviour (Home, Settings, Profile): dialogs and the mobile menu
   drawer, toasts, password visibility, tabs, focus helpers. Vanilla, no deps.
   Dialog and toast motion is CSS, driven by [data-state] and .is-leaving. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var EXIT_MS = 200;

  /* ---------- Dialogs (native <dialog>: focus trap, inert page, Esc) ---------- */
  function openDialog(d) {
    if (!d || d.open || !d.showModal) return;
    d.showModal();
    requestAnimationFrame(function () { requestAnimationFrame(function () { d.setAttribute('data-state', 'open'); }); });
  }
  function closeDialog(d) {
    if (!d || !d.open) return;
    d.setAttribute('data-state', 'closed');
    setTimeout(function () { if (d.open) d.close(); }, EXIT_MS);
  }
  window.olDialog = { open: openDialog, close: closeDialog };

  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-dialog-open]');
    if (opener) { openDialog(document.getElementById(opener.getAttribute('data-dialog-open'))); return; }
    var closer = e.target.closest('[data-dialog-close]');
    if (closer) { closeDialog(closer.closest('dialog')); return; }
    var d = e.target;
    if (d.matches && d.matches('dialog.overlay')) { closeDialog(d); return; }            // backdrop click
    var d2 = e.target.closest('dialog.app-menu-drawer');
    if (d2 && e.target.closest('a')) closeDialog(d2);                                    // navigating away
  });
  $$('dialog.overlay').forEach(function (d) {
    d.addEventListener('cancel', function (e) { e.preventDefault(); closeDialog(d); });  // Esc
    d.addEventListener('close', function () { d.removeAttribute('data-state'); });
  });
  if (window.matchMedia) {
    window.matchMedia('(min-width: 900px)').addEventListener('change', function (m) {
      if (m.matches) closeDialog(document.getElementById('app-menu'));
    });
  }

  /* ---------- Toasts ---------- */
  function dismiss(t) { t.classList.add('is-leaving'); setTimeout(function () { t.remove(); }, EXIT_MS); }
  function wire(t) {
    var x = $('[data-toast-close]', t);
    if (x) x.addEventListener('click', function () { dismiss(t); });
    setTimeout(function () { if (t.isConnected) dismiss(t); }, t.getAttribute('role') === 'alert' ? 9000 : 6000);
  }
  $$('[data-toast]').forEach(wire);
  var TOAST_ICON = { success: 'check-circle', error: 'warning-circle', danger: 'warning-circle', warning: 'warning', info: 'info' };
  window.olToast = function (msg, type) {
    var box = $('#toast-region'); if (!box) return;
    type = TOAST_ICON[type] ? type : 'info';
    var t = document.createElement('div');
    t.className = 'toast toast--' + type;
    t.setAttribute('role', type === 'error' ? 'alert' : 'status');
    t.setAttribute('data-toast', '');
    t.innerHTML = '<svg class="icon" aria-hidden="true" focusable="false"><use href="#ap-' + TOAST_ICON[type] + '"></use></svg>' +
      '<p class="toast__msg"></p>' +
      '<button type="button" class="toast__close" data-toast-close aria-label="Dismiss notification"><svg class="icon icon--sm" aria-hidden="true" focusable="false"><use href="#ap-x"></use></svg></button>';
    $('.toast__msg', t).textContent = msg;
    box.appendChild(t); wire(t);
  };
  window.showToast = function (msg, type) { window.olToast(msg, type === 'error' ? 'error' : 'success'); };  // name used by the feature scripts

  /* ---------- Password visibility (delegated: forms are re-rendered after AJAX saves) ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.pwd-toggle'); if (!b) return;
    var i = document.getElementById(b.getAttribute('data-target')) || $('input', b.parentElement); if (!i) return;
    var show = i.type === 'password';
    i.type = show ? 'text' : 'password';
    b.setAttribute('aria-pressed', show ? 'true' : 'false');
    b.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });

  /* ---------- Focus helper ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-focus-target]'); if (!b) return;
    var t = $(b.getAttribute('data-focus-target')); if (t) t.focus();
  });

  /* ---------- Tabs: role=tablist, arrows / Home / End, #hash, opens the panel that holds errors ---------- */
  $$('[data-tabs]').forEach(function (root) {
    var tabs = $$('[role="tab"]', root);
    var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute('aria-controls')); });
    function select(name, focus, push) {
      var found = false;
      tabs.forEach(function (t, i) {
        var on = t.getAttribute('data-tab') === name; found = found || on;
        t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1;
        if (panels[i]) panels[i].hidden = !on;
        if (on && focus) t.focus();
      });
      if (found && push && history.replaceState) history.replaceState(null, '', '#' + name);
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(t.getAttribute('data-tab'), false, true); });
      t.addEventListener('keydown', function (e) {
        var n = null;
        if (e.key === 'ArrowRight') n = (i + 1) % tabs.length;
        else if (e.key === 'ArrowLeft') n = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') n = 0; else if (e.key === 'End') n = tabs.length - 1;
        if (n === null) return; e.preventDefault(); select(tabs[n].getAttribute('data-tab'), true, true);
      });
    });
    var start = null;
    panels.forEach(function (p, i) { if (!start && p && p.querySelector('[data-field-error], .alert--danger')) start = tabs[i].getAttribute('data-tab'); });
    var hash = (location.hash || '').slice(1);
    if (!start && hash && tabs.some(function (t) { return t.getAttribute('data-tab') === hash; })) start = hash;
    if (start) select(start, false, false);
    window.addEventListener('hashchange', function () { var h = location.hash.slice(1); if (tabs.some(function (t) { return t.getAttribute('data-tab') === h; })) select(h, false, false); });
  });
})();
