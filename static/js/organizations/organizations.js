/* Organizations: the hooks that open and create organizations.
   Loaded on Home and Profile (where these buttons live) and on the organization page.

     org:create       (el, {name, acronym, academicYear})   Home "Create an organization" dialog
     org:open         (el, {org})                           Profile shelf and ledger, search results
     org:view-years   (el, {org})                           Home card menu: the A.Y. shelf on the organization page

   Each returns a Promise or navigates. Reject with Error('message') to show the message in the dialog. */
(function () {
  'use strict';
  var OL = window.OL;
  if (!OL) return;

  OL.register('org:create', function (el, d) {
    return OL.post('/organizations/create/', { name: d.name, acronym: d.acronym, academicYear: d.academicYear })
      .then(function (r) { window.location.assign(r.url); });   // the success toast is queued server-side and shows on the next page
  });

  OL.register('org:open', function (el, d) { window.location.assign('/organizations/' + encodeURIComponent(d.org) + '/'); });
  OL.register('org:view-years', function (el, d) { window.location.assign('/organizations/' + encodeURIComponent(d.org) + '/#years'); });
})();
