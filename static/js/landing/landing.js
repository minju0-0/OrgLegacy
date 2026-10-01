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