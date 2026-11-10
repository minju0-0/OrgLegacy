/* Home screen behaviour.

   Works on its own (no backend needed):  filtering, sorting, the join-code cells, validation,
   the share dialog (copy), the leave dialog, the retry button.
   Needs your logic (register with OL.register, see docs/HOME.md):
     join:preview       (el, {code}) -> {summary}        optional: what the code is for, shown before Confirm
     join:submit        (el, {code})                     join with a code
     org:create         (el, {name, acronym, academicYear})
     org:open           (el, {org})                      only when a card has no url
     org:view-years     (el, {org})
     org:leave-confirm  (el, {org})
     share:regenerate   (el, {org})  -> {code, expires}
     attention:act, attention:view-all, activity:view-all
   A handler may return a Promise. Resolve = the dialog closes. Reject(new Error('message')) = the message shows in the dialog. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var OL = window.OL;

  var connected = OL.run;   // shared contract: see core.js

  /* ---------------- 1. Join code ---------------- */
  (function () {
    var root = $('[data-accession]'); if (!root) return;
    var dlg = root.closest('dialog');
    var cells = $$('[data-acc-cell]', root), form = $('#accession-form', root);
    var btn = $('#accession-submit', root), fb = $('#accession-feedback', root);
    var HINT = 'Paste works too.';
    var clean = function (s) { return String(s).toUpperCase().replace(/[^A-Z0-9]/g, ''); };
    var code = function () { return cells.map(function (c) { return c.value; }).join(''); };
    function say(t, kind) { fb.textContent = t; fb.className = 'form-feedback' + (kind ? ' is-' + kind : ''); }

    // Invalid-cell feedback. WAAPI so a repeat keypress restarts cleanly; reduced motion gets only the red border.
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function shake(c) {
      c.classList.add('is-invalid'); clearTimeout(c._t); c._t = setTimeout(function () { c.classList.remove('is-invalid'); }, 700);
      if (still || !c.animate) return;
      c.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-3px)', offset: 0.25 }, { transform: 'translateX(3px)', offset: 0.75 }, { transform: 'translateX(0)' }], { duration: 220, easing: 'cubic-bezier(0.23, 1, 0.32, 1)' });
    }
    function sync() {
      cells.forEach(function (c) { c.classList.toggle('is-filled', !!c.value); });
      var done = code().length === cells.length; btn.disabled = !done;
      say(done ? 'Ready to join.' : HINT, done ? 'ok' : '');
    }
    function reset() { cells.forEach(function (c) { c.value = ''; }); sync(); }

    cells.forEach(function (c, i) {
      c.addEventListener('input', function () {
        var raw = c.value, v = clean(raw); c.value = v.slice(-1);
        if (raw && !v) shake(c);
        if (c.value && cells[i + 1]) cells[i + 1].focus(); sync();
      });
      c.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !c.value && cells[i - 1]) { cells[i - 1].focus(); cells[i - 1].value = ''; sync(); e.preventDefault(); }
        else if (e.key === 'ArrowLeft' && cells[i - 1]) cells[i - 1].focus();
        else if (e.key === 'ArrowRight' && cells[i + 1]) cells[i + 1].focus();
      });
      c.addEventListener('focus', function () { c.select(); });
      c.addEventListener('paste', function (e) {
        e.preventDefault();
        var t = clean((e.clipboardData || window.clipboardData).getData('text'));
        if (t.indexOf('OL') === 0 && t.length > cells.length) t = t.slice(2);
        t.slice(0, cells.length).split('').forEach(function (ch, k) { cells[k].value = ch; });
        cells[Math.min(t.length, cells.length - 1)].focus(); sync();
      });
    });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var c = code();
      if (c.length < cells.length) { cells.forEach(function (x) { if (!x.value) shake(x); }); say('Enter all eight characters.', 'error'); (cells.filter(function (x) { return !x.value; })[0] || cells[0]).focus(); return; }
      var d = $('#join-modal'); $('[data-join="code"]', d).textContent = 'OL-' + c.slice(0, 4) + '-' + c.slice(4);
      var summary = $('[data-join="summary"]', d), base = summary ? summary.textContent : '';
      if (!OL.has('join:preview')) { OL_open(d); return; }
      // join:preview resolves {summary}: "You are about to join [Org] as [Role] in [Committee]. Confirm?" Reject to show why not.
      btn.disabled = true;
      Promise.resolve(OL.act('join:preview', form, { code: c })).then(function (p) {
        btn.disabled = false; if (summary) summary.textContent = (p && p.summary) || base; OL_open(d);
      }).catch(function (err) { btn.disabled = false; say((err && err.message) || 'That code is not valid.', 'error'); });
    });

    // Confirm: hand the code to your logic. Resolve closes both dialogs; reject shows the message under the cells.
    document.addEventListener('click', function (e) {
      var ok = e.target.closest('[data-join-confirm]'); if (!ok) return;
      var join = ok.closest('dialog');
      var done = function () { OL_close(join); OL_close(dlg); };
      var fail = function (m) { OL_close(join); say(m, 'error'); };
      if (!connected('join:submit', form, { code: code() }, done, fail)) OL_close(join);   // not connected: toast, keep the code on screen
    });
    document.addEventListener('click', function (e) {
      if (e.target.closest('[data-dialog-open="accession-modal"]')) setTimeout(function () { (cells.filter(function (x) { return !x.value; })[0] || cells[0]).focus(); }, 60);
    });
    dlg.addEventListener('close', reset);
    sync();
  })();

  /* ---------------- 2. Create an organization ---------------- */
  (function () {
    var panel = $('[data-charter]'); if (!panel) return;
    var dlg = panel.closest('dialog'), form = $('#charter-form', panel);
    var name = $('#charter-name', panel), acr = $('#charter-acronym', panel), ay = $('#charter-ay', panel), fb = $('#charter-feedback', panel);
    function say(t, kind) { fb.textContent = t; fb.className = 'form-feedback' + (kind ? ' is-' + kind : ''); }
    acr.addEventListener('input', function () { acr.value = acr.value.toUpperCase().replace(/[^A-Z0-9]/g, ''); });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!name.value.trim()) { say('Give the organization a name.', 'error'); name.focus(); return; }
      if (!/^\d{4}\s*[-\u2013]\s*\d{4}$/.test(ay.value.trim())) { say('Enter the A.Y. as two years, like 2026-2027.', 'error'); ay.focus(); return; }
      say('', '');
      var detail = { name: name.value.trim(), acronym: acr.value, academicYear: ay.value.replace(/\s*[\u2013]\s*/, '-').trim() };
      connected('org:create', form, detail, function () { OL_close(dlg); }, function (m) { say(m, 'error'); });
    });
    document.addEventListener('click', function (e) { if (e.target.closest('[data-dialog-open="charter-modal"]')) setTimeout(function () { name.focus(); }, 60); });
    dlg.addEventListener('close', function () { form.reset(); say('', ''); });
  })();

  /* ---------------- 3. Share a join code ---------------- */
  (function () {
    var panel = $('[data-share]'); if (!panel) return;
    var dlg = panel.closest('dialog'), cells = $$('[data-share-cell]', panel), note = $('[data-share="note"]', panel);
    var copyBtn = $('[data-share-copy]', panel), current = '', orgId = '';
    var fmt = function (c) { return 'OL-' + c.slice(0, 4) + '-' + c.slice(4); };

    function set(o) {   // OL.share.set({code, expires}): call after you make a new code
      current = (o && o.code ? String(o.code).toUpperCase().replace(/[^A-Z0-9]/g, '') : '').slice(0, 8);
      cells.forEach(function (c, i) { c.textContent = current[i] || '\u00b7'; c.classList.toggle('is-filled', !!current[i]); });
      var ready = current.length === 8; panel.setAttribute('data-state', ready ? 'ready' : 'empty'); copyBtn.disabled = !ready;
      note.textContent = ready ? ((o && o.expires) || 'Anyone with this code can join.') : 'There is no active code yet. Make one to start inviting people.';
    }
    window.OL.share = { set: set };

    OL.default('org:share-code', function (el, d) {
      orgId = d.org || ''; $('[data-share="org"]', panel).textContent = d.orgName || 'this organization';
      set({ code: d.code, expires: d.expires }); OL_open(dlg);
    });
    OL.default('share:copy', function () {
      if (current.length !== 8) return;
      var text = fmt(current), done = function () {
        var l = $('span', copyBtn), old = l.textContent; l.textContent = 'Copied'; if (window.olToast) window.olToast('Join code copied.', 'success');
        setTimeout(function () { l.textContent = old; }, 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { window.olToast && window.olToast("Couldn't copy. Select the code and copy it by hand.", 'error'); });
      else { window.olToast && window.olToast("Couldn't copy. Select the code and copy it by hand.", 'error'); }
    });
    // Regenerate: your handler returns {code, expires} (or a Promise of it)
    document.addEventListener('click', function (e) {
      var b = e.target.closest('[data-action="share:regenerate"]'); if (!b || !OL.has('share:regenerate')) return;   // not connected: the global handler shows the toast
      e.stopPropagation(); e.preventDefault();                                                                      // we run the handler here, so the global one must not run it again
      b.disabled = true;
      Promise.resolve(OL.act('share:regenerate', b, { org: orgId })).then(set).catch(function (err) { note.textContent = (err && err.message) || 'Could not make a new code.'; }).then(function () { b.disabled = false; });
    }, true);
  })();

  /* ---------------- 4. Leave an organization ---------------- */
  (function () {
    var dlg = $('#leave-modal'); if (!dlg) return;
    var orgId = '';
    OL.default('org:leave', function (el, d) { orgId = d.org || ''; $('[data-leave="org"]', dlg).textContent = d.orgName || 'this organization'; OL_open(dlg); });
    document.addEventListener('click', function (e) {
      var b = e.target.closest('[data-leave-confirm]'); if (!b) return;
      e.stopPropagation(); e.preventDefault();                                                                      // this handler owns the click
      if (!OL.has('org:leave-confirm')) { OL.act('org:leave-confirm', b, { org: orgId }); OL_close(dlg); return; }
      Promise.resolve(OL.act('org:leave-confirm', b, { org: orgId })).then(function () { OL_close(dlg); }).catch(function (err) { window.olToast && window.olToast((err && err.message) || 'Could not leave. Try again.', 'error'); });
    }, true);
  })();

  OL.default('home:retry', function () { location.reload(); });

  /* ---------------- 5. Filter the organizations by status, and sort them (finding one by name is the top bar search) ---------------- */
  (function () {
    var grid = $('[data-org-grid]'); if (!grid) return;
    var cards = $$('[data-org-card]', grid), none = $('[data-no-match]');
    var sort = $('[data-sort]'), segs = $$('[data-filter]');
    var state = { status: 'all', sort: 'recent' };

    $$('[data-count]').forEach(function (c) {
      var k = c.getAttribute('data-count'); c.textContent = k === 'all' ? cards.length : cards.filter(function (x) { return x.getAttribute('data-status') === k; }).length;
    });
    function apply() {
      var shown = 0;
      cards.forEach(function (c) {
        var ok = state.status === 'all' || c.getAttribute('data-status') === state.status;
        c.hidden = !ok; if (ok) shown++;
      });
      var by = { recent: function (a, b) { return a.getAttribute('data-order') - b.getAttribute('data-order'); },
                 name: function (a, b) { return a.getAttribute('data-name').localeCompare(b.getAttribute('data-name')); },
                 ay: function (a, b) { return b.getAttribute('data-ay').localeCompare(a.getAttribute('data-ay')) || by.name(a, b); } };
      cards.slice().sort(by[state.sort]).forEach(function (c) { grid.appendChild(c); });
      grid.hidden = shown === 0; if (none) none.hidden = shown !== 0;
      document.dispatchEvent(new CustomEvent('ol:filter', { detail: { status: state.status, sort: state.sort, shown: shown } }));
    }
    if (sort) sort.addEventListener('change', function () { state.sort = sort.value; apply(); });
    segs.forEach(function (b) { b.addEventListener('click', function () {
      state.status = b.getAttribute('data-filter'); segs.forEach(function (o) { o.setAttribute('aria-pressed', o === b ? 'true' : 'false'); }); apply();
    }); });
    var clear = $('[data-clear-filters]'); if (clear) clear.addEventListener('click', function () {
      state = { status: 'all', sort: state.sort }; segs.forEach(function (o) { o.setAttribute('aria-pressed', o.getAttribute('data-filter') === 'all' ? 'true' : 'false'); }); apply();
    });
  })();

  /* ---------------- Preview only: a demo search so every search state can be reviewed ---------------- */
  (function () {
    var home = $('[data-home][data-preview]'); if (!home) return;
    var pool = {
      'Events': [['Leadership summit', 'JPCS, A.Y. 2026-2027'], ['Freshmen welcome', 'JPCS, A.Y. 2025-2026'], ['Foundation day booth', 'CSC, A.Y. 2025-2026']],
      'Suppliers': [['Print Hub', 'Printing, 4 out of 5'], ['Cebu Sound Rentals', 'Sound system, 5 out of 5']],
      'Handover notes': [['Logistics handover', 'CDS, A.Y. 2025-2026'], ['Events committee handover', 'CSC, A.Y. 2025-2026']]
    };
    OL.search.connect(function (query) {
      var t = query.toLowerCase(), g = [];
      if (t === 'zzz') throw new Error('demo error');
      var orgs = $$('[data-org-card]').filter(function (c) { return c.getAttribute('data-name').indexOf(t) !== -1; }).map(function (c) { return { id: c.getAttribute('data-org'), title: $('.org__name', c).textContent.trim(), meta: c.getAttribute('data-ay') }; });
      if (orgs.length) g.push({ label: 'Organizations', items: orgs });
      Object.keys(pool).forEach(function (k) { var it = pool[k].filter(function (r) { return r[0].toLowerCase().indexOf(t) !== -1; }).map(function (r, i) { return { id: k + i, title: r[0], meta: r[1] }; }); if (it.length) g.push({ label: k, items: it }); });
      return new Promise(function (res) { setTimeout(function () { res(g); }, 350); });
    });
  })();

  /* helpers: the shared dialog API */
  function OL_open(d) { window.olDialog.open(d); }
  function OL_close(d) { window.olDialog.close(d); }
})();
