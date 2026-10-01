/* App behaviour: mobile drawer, <dialog> modals, toasts, password toggle,
   staggered reveal indices. Vanilla, no dependencies. */
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Drawer (sidebar on small screens)
  var side = $('#sidebar'), scrim = $('.scrim');
  function drawer(open) {
    if (!side) return;
    side.classList.toggle('is-open', open);
    scrim.classList.toggle('is-open', open);
    if (open) { var a = $('a', side); if (a) a.focus(); }
  }
  $$('[data-drawer-open]').forEach(function (b) { b.addEventListener('click', function () { drawer(true); }); });
  $$('[data-drawer-close]').forEach(function (b) { b.addEventListener('click', function () { drawer(false); }); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') drawer(false); });

  // Modals: <dialog id> + [data-modal-open="id"] / [data-modal-close]
  $$('[data-modal-open]').forEach(function (b) {
    b.addEventListener('click', function () { var d = document.getElementById(b.dataset.modalOpen); if (d && d.showModal) d.showModal(); });
  });
  $$('dialog.modal').forEach(function (d) {
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
    $$('[data-modal-close]', d).forEach(function (b) { b.addEventListener('click', function () { d.close(); }); });
  });

  // Toasts
  function dismiss(t) { t.classList.add('is-leaving'); setTimeout(function () { t.remove(); }, 250); }
  function wire(t) {
    var x = $('[data-toast-close]', t);
    if (x) x.addEventListener('click', function () { dismiss(t); });
    setTimeout(function () { if (t.isConnected) dismiss(t); }, 6000);
  }
  $$('.toast').forEach(wire);
  window.olToast = function (msg, type) {
    var box = $('#toasts'); if (!box) return;
    var t = document.createElement('div');
    t.className = 'toast toast--' + (type || 'info');
    t.innerHTML = '<span class="toast__dot" aria-hidden="true"></span><span></span>' +
      '<button type="button" class="iconbtn" data-toast-close aria-label="Dismiss"><svg class="i"><use href="#i-x"/></svg></button>';
    t.children[1].textContent = msg;
    box.appendChild(t); wire(t);
  };
  $$('[data-toast]').forEach(function (b) {
    b.addEventListener('click', function () { window.olToast(b.dataset.toast, b.dataset.toastType); });
  });

  // Password visibility: <button data-pw-toggle="inputId"><svg><use></svg></button>
  $$('[data-pw-toggle]').forEach(function (b) {
    b.addEventListener('click', function () {
      var i = document.getElementById(b.dataset.pwToggle); if (!i) return;
      var show = i.type === 'password';
      i.type = show ? 'text' : 'password';
      b.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      var u = $('use', b); if (u) u.setAttribute('href', show ? '#i-eye-off' : '#i-eye');
    });
  });

  // Stagger indices for .reveal children
  $$('.reveal').forEach(function (r) { $$(':scope > *', r).forEach(function (c, n) { c.style.setProperty('--n', n); }); });
})();

/* Styleguide/demo hook: [data-stamp-demo="#id"] re-presses a stamp once. */
document.querySelectorAll('[data-stamp-demo]').forEach(function (b) {
  b.addEventListener('click', function () {
    var s = document.querySelector(b.dataset.stampDemo); if (!s) return;
    s.classList.remove('is-new'); void s.offsetWidth; s.classList.add('is-new');
  });
});