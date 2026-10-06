/* Staggered scroll reveal. Content is visible by default; the .js class
   (set in <head>) is what opts elements into the hidden start state. */
(function () {
  var els = document.querySelectorAll('[data-reveal]');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) {
    els.forEach(function (el) { el.classList.add('in'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -6% 0px' });
  els.forEach(function (el, i) {
    if (!el.style.getPropertyValue('--i')) el.style.setProperty('--i', i % 5);
    io.observe(el);
  });
})();

/* Landing top bar: mobile menu toggle and a section highlight that follows the scroll. */
(() => {
  const nav = document.querySelector('.lp-nav');
  if (!nav) return;
  const btn = nav.querySelector('.lp-nav__toggle');
  const links = [...nav.querySelectorAll('.lp-nav__links a')];
  const setOpen = (open) => { nav.classList.toggle('is-open', open); if (btn) btn.setAttribute('aria-expanded', String(open)); };
  if (btn) btn.addEventListener('click', () => setOpen(!nav.classList.contains('is-open')));
  links.forEach((a) => a.addEventListener('click', () => setOpen(false)));
  document.addEventListener('click', (e) => { if (!nav.contains(e.target)) setOpen(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && nav.classList.contains('is-open')) { setOpen(false); if (btn) btn.focus(); } });
  const byId = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]));
  const io = new IntersectionObserver((entries) => entries.forEach((en) => {
    if (!en.isIntersecting) return;
    links.forEach((a) => a.removeAttribute('aria-current'));
    const a = byId.get(en.target.id);
    if (a) a.setAttribute('aria-current', 'true');
  }), { rootMargin: '-45% 0px -50% 0px' });
  byId.forEach((_, id) => { const el = document.getElementById(id); if (el) io.observe(el); });
})();