/* Auth pages: open the password-requirements panel when a password field gains focus.
   Password visibility toggle lives in app.js (data-pw-toggle). No page-switch animation by design. */
(function () {
  var rules = document.getElementById('password-rules-details');
  if (!rules) return;
  Array.prototype.forEach.call(document.querySelectorAll('input[type="password"]'), function (i) {
    i.addEventListener('focus', function () { rules.open = true; });
  });
})();