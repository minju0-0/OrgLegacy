/* Site behaviour, loaded on every page: dialogs and the mobile menu drawer, toasts,
   password visibility, tabs, focus helpers.
   Vanilla, no dependencies. Dialog and toast motion is CSS, driven by [data-state] and .is-leaving. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var EXIT_MS = 200;

  /* ---------- Dialogs (native <dialog>: focus trap, inert page, Esc) ---------- */
  // Remember what was pressed. Safari does not focus a button on click, so document.activeElement alone
  // would be <body> and nothing could be given back focus when the dialog closes.
  var lastPressed = null;
  document.addEventListener('click', function (e) { lastPressed = e.target.closest ? e.target.closest('button, a[href], [role="menuitem"]') : null; }, true);

  function restoreFocus(d) {
    var o = d._opener; d._opener = null;
    if (!o || o === document.body || !o.isConnected) return;
    if (o.getClientRects().length === 0) {                       // opener is hidden (an item in a closed menu): use the menu's button
      var m = o.closest('[data-menu]'); o = m && m.querySelector('.menu__trigger');
    }
    if (o && o.focus) o.focus({ preventScroll: true });
  }

  function openDialog(d) {
    if (!d || d.open || !d.showModal) return;
    d._opener = lastPressed && lastPressed.isConnected ? lastPressed : document.activeElement;
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
    d.addEventListener('close', function () { d.removeAttribute('data-state'); restoreFocus(d); });
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
    t.innerHTML = '<svg class="icon" aria-hidden="true" focusable="false"><use href="#ol-' + TOAST_ICON[type] + '"></use></svg>' +
      '<p class="toast__msg"></p>' +
      '<button type="button" class="toast__close" data-toast-close aria-label="Dismiss notification"><svg class="icon icon--sm" aria-hidden="true" focusable="false"><use href="#ol-x"></use></svg></button>';
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


/* =====================================================================
   Connection layer. The UI is finished; logic plugs in here.

   OL.register('area:verb', function (el, detail) {...})  handle a [data-action] click
   OL.default('area:verb', fn)                            built-in behaviour used when nothing is registered
   OL.search.connect(function (query) { return groups })  results for the search box (sync or Promise)

   A [data-action] with no handler and no default says "That isn't connected yet." instead of doing nothing.
   Names in use are listed in docs/HOME.md.
   ===================================================================== */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var OL = window.OL = window.OL || {};
  var handlers = {}, defaults = {};

  OL.register = function (name, fn) { handlers[name] = fn; };
  OL.default = function (name, fn) { defaults[name] = fn; };
  OL.has = function (name) { return !!handlers[name]; };
  /* OL.run(name, el, detail, onDone, onError): run a handler for a dialog or form.
     Registered: a returned Promise resolves to onDone(result) or rejects to onError(message). Returns true.
     Not registered: shows "That isn't connected yet." and returns false, so the caller keeps its dialog open. */
  OL.run = function (name, el, detail, onDone, onError) {
    if (!OL.has(name)) { OL.act(name, el, detail); return false; }
    Promise.resolve(OL.act(name, el, detail)).then(onDone).catch(function (err) { onError((err && err.message) || 'Something went wrong. Try again.'); });
    return true;
  };
  OL.act = function (name, el, detail) {
    var fn = handlers[name] || defaults[name];
    if (fn) return fn(el, detail || {});
    if (window.olToast) window.olToast("That isn't connected yet.", 'info');
  };

  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-action]');
    if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return;
    e.preventDefault();
    var detail = {}; Array.prototype.forEach.call(el.attributes, function (a) {
      if (a.name.indexOf('data-') === 0 && a.name !== 'data-action') detail[a.name.slice(5).replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); })] = a.value;
    });
    var menu = el.closest('[data-menu]'); if (menu) closeMenu(menu, false);
    OL.act(el.getAttribute('data-action'), el, detail);
  });

  /* ---------- Menu (the "more actions" button on cards and rows) ---------- */
  function closeMenu(m, focus) {
    var t = $('.menu__trigger', m), p = $('.menu__panel', m); if (!p || p.hidden) return;
    p.hidden = true; t.setAttribute('aria-expanded', 'false');
    var host = m.closest('.card'); if (host) host.classList.remove('is-menu-open');
    if (focus) t.focus();
  }
  function openMenu(m) {
    $$('[data-menu]').forEach(function (o) { if (o !== m) closeMenu(o, false); });
    var t = $('.menu__trigger', m), p = $('.menu__panel', m); p.hidden = false; t.setAttribute('aria-expanded', 'true');
    var host = m.closest('.card'); if (host) host.classList.add('is-menu-open');
    var first = $('.menu__item', p); if (first) first.focus();
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest('.menu__trigger');
    if (t) { var m = t.closest('[data-menu]'); if ($('.menu__panel', m).hidden) openMenu(m); else closeMenu(m, true); return; }
    if (!e.target.closest('[data-menu]')) $$('[data-menu]').forEach(function (m) { closeMenu(m, false); });
  });
  document.addEventListener('keydown', function (e) {
    var m = e.target.closest && e.target.closest('[data-menu]'); if (!m) return;
    var items = $$('.menu__item', m), i = items.indexOf(document.activeElement);
    if (e.key === 'Escape') { closeMenu(m, true); }
    else if (e.key === 'ArrowDown' && !$('.menu__panel', m).hidden) { e.preventDefault(); items[(i + 1) % items.length].focus(); }
    else if (e.key === 'ArrowUp' && !$('.menu__panel', m).hidden) { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
    else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && e.target.classList.contains('menu__trigger')) { e.preventDefault(); openMenu(m); }
    else if (e.key === 'Tab') closeMenu(m, false);
  });

  /* ---------- Popovers (notifications). Non-modal: Esc and outside click close it. ---------- */
  function setPopover(id, open) {
    var p = document.getElementById(id); if (!p) return;
    var t = $('[data-popover-open="' + id + '"]'); p.hidden = !open; if (t) t.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) { var f = $('button:not([disabled]), a[href]', p); if (f) f.focus(); }
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-popover-open]');
    if (t) { var id = t.getAttribute('data-popover-open'), p = document.getElementById(id); setPopover(id, p.hidden); return; }
    $$('[data-popover]').forEach(function (p) { if (!p.hidden && !p.contains(e.target)) setPopover(p.id, false); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    $$('[data-popover]').forEach(function (p) { if (!p.hidden) { setPopover(p.id, false); var t = $('[data-popover-open="' + p.id + '"]'); if (t) t.focus(); } });
  });

  /* ---------- Search ---------- */
  var provider = null, seq = 0, timer = null;
  function paint(state, text, groups) {
    $$('[data-search-body]').forEach(function (b) {
      $('[data-search-state]', b).textContent = text || '';
      $('[data-search-state]', b).hidden = !text;
      var box = $('[data-search-results]', b); box.innerHTML = '';
      (groups || []).forEach(function (g) {
        if (!g.items || !g.items.length) return;
        var s = document.createElement('div'); s.className = 'srch__group';
        var label = document.createElement('p'); label.className = 'srch__label'; label.textContent = g.label; s.appendChild(label);
        g.items.forEach(function (it) {
          var el = document.createElement(it.href ? 'a' : 'button');
          if (it.href) el.href = it.href; else { el.type = 'button'; el.setAttribute('data-action', 'search:open'); el.setAttribute('data-id', it.id == null ? '' : it.id); el.setAttribute('data-kind', g.label); }
          el.className = 'srch__item'; el.setAttribute('role', 'option');
          var t = document.createElement('span'); t.className = 'srch__title'; t.textContent = it.title; el.appendChild(t);
          if (it.meta) { var m = document.createElement('span'); m.className = 'srch__meta'; m.textContent = it.meta; el.appendChild(m); }
          s.appendChild(el);
        });
        box.appendChild(s);
      });
    });
    $$('[data-search-input]').forEach(function (i) { i.setAttribute('aria-expanded', state === 'results' ? 'true' : 'false'); });
  }
  OL.search = {
    connect: function (fn) { provider = fn; },
    run: function (q) {
      q = (q || '').trim();
      if (q.length < 2) { paint('idle', 'Search organizations, events, suppliers and handover notes.'); return; }
      if (!provider) { paint('off', "Search isn't connected yet."); return; }
      var mine = ++seq; paint('loading', 'Searching\u2026');
      Promise.resolve().then(function () { return provider(q); }).then(function (groups) {
        if (mine !== seq) return;
        var n = (groups || []).reduce(function (a, g) { return a + (g.items ? g.items.length : 0); }, 0);
        if (!n) paint('empty', 'No results for \u201c' + q + '\u201d.'); else paint('results', '', groups);
      }).catch(function () { if (mine === seq) paint('error', "Search isn't available right now. Try again in a moment."); });
    }
  };
  function panelFor(input) { var root = input.closest('[data-search]'); return root && $('[data-search-panel]', root); }
  document.addEventListener('input', function (e) {
    var i = e.target.closest && e.target.closest('[data-search-input]'); if (!i) return;
    $$('[data-search-input]').forEach(function (o) { if (o !== i) o.value = i.value; });
    var p = panelFor(i); if (p) p.hidden = false;
    clearTimeout(timer); timer = setTimeout(function () { OL.search.run(i.value); }, 180);
  });
  document.addEventListener('focusin', function (e) {
    var i = e.target.closest && e.target.closest('[data-search-input]'); if (!i) return;
    var p = panelFor(i); if (p) { p.hidden = false; OL.search.run(i.value); }
  });
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-search]')) return;
    $$('[data-search-panel]').forEach(function (p) { p.hidden = true; });
  });
  document.addEventListener('keydown', function (e) {
    var i = e.target.closest && e.target.closest('[data-search-input]');
    if (i && e.key === 'Escape') {
      var p = panelFor(i);
      if (p) { p.hidden = true; i.blur(); }                                                    // desktop: close the results
      else if (i.value) { e.preventDefault(); i.value = ''; OL.search.run(''); }               // phone sheet: first Esc clears, second closes the dialog
    }
    if (i && e.key === 'ArrowDown') { var f = $('.srch__item', i.closest('[data-search]')); if (f) { e.preventDefault(); f.focus(); } }
    var it = e.target.closest && e.target.closest('.srch__item');
    if (it && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      var all = $$('.srch__item', it.closest('[data-search]')), n = all.indexOf(it) + (e.key === 'ArrowDown' ? 1 : -1);
      e.preventDefault(); if (n < 0) { $('[data-search-input]', it.closest('[data-search]')).focus(); } else if (all[n]) all[n].focus();
    }
    if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey && !/^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || '')) && !e.target.isContentEditable) {
      var box = $$('.topbar__search [data-search-input]').filter(function (x) { return x.offsetParent !== null; })[0];
      if (box) { e.preventDefault(); box.focus(); }
    }
  });
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-dialog-open="search-sheet"]')) setTimeout(function () { var i = $('#search-sheet [data-search-input]'); if (i) i.focus(); }, 80);
  });
})();

/* ---- Auth pages: open the password-requirements panel when a password field gains focus (no-op elsewhere) ---- */
(function () {
  var rules = document.getElementById('password-rules-details');
  if (!rules) return;
  document.querySelectorAll('input[type="password"]').forEach(function (i) {
    i.addEventListener('focus', function () { rules.open = true; });
  });
})();
