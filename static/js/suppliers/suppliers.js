/* Suppliers: reopen the Add or Edit dialog when the server sent the page back with a mistake in it.
   Opening it normally is data-dialog-open in the markup and needs no script. */
(function () {
  'use strict';
  var again = document.querySelector('dialog[data-open-on-load]');
  if (again && window.olDialog) window.olDialog.open(again);
})();
