/* Handover notes: reopen invalid modal on 400 and toggle committee field by scope */
(function () {
  var again = document.querySelector('dialog[data-open-on-load]');
  if (again && window.olDialog) window.olDialog.open(again);

  function setupScopeToggle(modalId, wrapId) {
    var modal = document.getElementById(modalId);
    if (!modal) return;
    var scopeSelect = modal.querySelector('select[name="scope"]');
    var commWrap = document.getElementById(wrapId);
    if (!scopeSelect || !commWrap) return;

    function update() {
      commWrap.hidden = scopeSelect.value === 'ORGANIZATION';
    }

    scopeSelect.addEventListener('change', update);
    update();
  }

  setupScopeToggle('handover-add-modal', 'handover-committee-wrap');
  setupScopeToggle('handover-edit-modal', 'handover-committee-wrap-edit');
})();
