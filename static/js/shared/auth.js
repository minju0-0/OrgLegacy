/* Auth pages: open the password-requirements panel when a password field gains focus. */
(function () {
  var rules = document.getElementById('password-rules-details');
  if (!rules) return;
  document.querySelectorAll('input[type="password"]').forEach(function (i) {
    i.addEventListener('focus', function () { rules.open = true; });
  });
})();
