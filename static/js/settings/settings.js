/*
 * Settings feature behavior: password strength meter, password match
 * indicator, danger-zone delete confirmation gate (with the six DELETE
 * slots), and an asynchronous password-change submission.
 * Show/hide password and the tabs live in js/app/shell.js.
 *
 * Field ids (id_new_password1, id_new_password2, id_confirm) are
 * Django's default "id_<field name>" ids — see apps/settings/forms.py.
 */

function bindSettingsEvents() {
    // Password validation & strength
    const newPwd1 = document.getElementById('id_new_password1');
    const newPwd2 = document.getElementById('id_new_password2');
    const matchIndicator = document.getElementById('pwd-match-indicator');

    const updateStrength = (val) => {
        const hasLen = val.length >= 8;
        const hasNum = /\d/.test(val);
        const hasLetter = /[a-zA-Z]/.test(val);
        const hasUpper = /[A-Z]/.test(val);
        const hasSpecial = /[^a-zA-Z0-9]/.test(val);

        let score = 0;
        if (val.length > 0) score++;
        if (hasLen) score++;
        if (hasLen && hasNum && hasLetter) score++;
        if (hasLen && hasNum && hasUpper && hasSpecial) score++;

        const bars = [
            document.getElementById('pwd-str-1'),
            document.getElementById('pwd-str-2'),
            document.getElementById('pwd-str-3'),
            document.getElementById('pwd-str-4')
        ];
        const text = document.getElementById('pwd-str-text');
        const labels = ['pending input', 'Weak', 'Moderate', 'Good', 'Strong'];

        bars.forEach((b, i) => {
            if (!b) return;
            b.className = 'pwd-strength-bar' + (i < score ? ' is-on-' + score : '');
        });
        if (text) text.textContent = `Password strength: ${labels[score]}`;
    };

    const checkMatch = () => {
        if (!newPwd1 || !newPwd2 || !matchIndicator) return;
        const p1 = newPwd1.value;
        const p2 = newPwd2.value;

        if (p2.length > 0) {
            if (p1 === p2) {
                matchIndicator.textContent = 'Passwords match.';
                matchIndicator.className = 'match is-ok';
            } else {
                matchIndicator.textContent = 'Passwords do not match.';
                matchIndicator.className = 'match is-bad';
            }
        } else {
            matchIndicator.textContent = '';
            matchIndicator.className = 'match';
        }
    };

    if (newPwd1) {
        newPwd1.addEventListener('input', (e) => {
            updateStrength(e.target.value);
            checkMatch();
        });
        updateStrength(newPwd1.value);
    }
    if (newPwd2) {
        newPwd2.addEventListener('input', checkMatch);
    }

    // Danger zone confirmation validation
    const deleteInput = document.getElementById('id_confirm');
    const deleteBtn = document.getElementById('delete-account-btn');
    if (deleteInput && deleteBtn) {
        deleteInput.setAttribute('autocomplete', 'off');
        deleteInput.setAttribute('spellcheck', 'false');
        const slots = document.querySelectorAll('#confirm-slots .confirm-slot');
        const checkDeleteEligibility = () => {
            const val = deleteInput.value;
            deleteBtn.disabled = val.trim() !== 'DELETE';
            slots.forEach((slot, i) => {
                const ch = val.charAt(i);
                slot.textContent = ch;
                slot.classList.toggle('is-filled', !!ch);
            });
        };
        deleteInput.addEventListener('input', checkDeleteEligibility);
        checkDeleteEligibility();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    bindSettingsEvents();

    const pwdForm = document.getElementById('password-form');
    if (pwdForm) {
        pwdForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('save-pwd-btn');
            const feedback = document.getElementById('pwd-feedback-area');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = 'Updating...';
            feedback.textContent = '';

            try {
                const formData = new FormData(pwdForm);
                const res = await fetch(window.location.href, {
                    method: 'POST',
                    body: formData,
                });
                const html = await res.text();
                const doc = new DOMParser().parseFromString(html, 'text/html');

                const newForm = doc.getElementById('password-form');
                if (!newForm) { window.location.href = res.url; return; }
                const hasErrors = newForm.querySelector('.field--invalid, .alert--danger');

                if (hasErrors) {
                    pwdForm.innerHTML = newForm.innerHTML;
                    bindSettingsEvents();
                    const fresh = document.getElementById('pwd-feedback-area');
                    if (fresh) {
                        fresh.textContent = 'Please correct the issues indicated above.';
                        fresh.className = 'form-feedback is-error';
                    }
                    const firstBad = pwdForm.querySelector('.field--invalid input');
                    if (firstBad) firstBad.focus();
                } else {
                    pwdForm.reset();
                    pwdForm.innerHTML = newForm.innerHTML;
                    bindSettingsEvents();

                    const newFeedback = document.getElementById('pwd-feedback-area');
                    if (newFeedback) {
                        newFeedback.textContent = 'Password has been updated successfully.';
                        newFeedback.className = 'form-feedback is-ok';
                    }

                    if (typeof showToast === 'function') {
                        showToast('Password updated.');
                    }
                }
            } catch (err) {
                feedback.textContent = 'Unable to update password. Please try again.';
                feedback.className = 'form-feedback is-error';
            } finally {
                const newBtn = document.getElementById('save-pwd-btn');
                if (newBtn) {
                    newBtn.disabled = false;
                    newBtn.textContent = originalText;
                }
            }
        });
    }
});


/* ---------------------------------------------------------------------------
   Notification preferences and data export.
   Works as is:  the switches, dirty tracking, Reset, and the export button states.
   Needs logic:  register with OL.register (see docs/PROFILE_SETTINGS.md)
     settings:save-notifications  (el, {prefs: {key: {in_app, email}}})   resolve = saved, reject(Error('message'))
     account:export               (el)  resolve to {url} when the file is ready, or to anything else for "on its way"
     security:*                   see the Security tab
--------------------------------------------------------------------------- */
(function () {
    'use strict';
    var $ = function (s, r) { return (r || document).querySelector(s); };

    /* ---- Notification preferences ---- */
    var form = document.getElementById('notif-form');
    if (form) {
        var boxes = Array.prototype.slice.call(form.querySelectorAll('input[type="checkbox"]'));
        var save = $('[data-notif-save]', form), reset = $('[data-notif-reset]', form), fb = document.getElementById('notif-feedback');
        var UNSAVED = 'You have unsaved changes.';
        var say = function (t, kind) { fb.textContent = t; fb.className = 'form-feedback' + (kind ? ' is-' + kind : ''); };
        var dirty = function () { return boxes.some(function (b) { return b.checked !== b.defaultChecked; }); };
        var sync = function () {
            var d = dirty(); save.disabled = !d; reset.disabled = !d;
            if (d) say(UNSAVED, ''); else if (fb.textContent === UNSAVED) say('', '');
        };
        boxes.forEach(function (b) { b.addEventListener('change', sync); });
        reset.addEventListener('click', function () { boxes.forEach(function (b) { b.checked = b.defaultChecked; }); sync(); });
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!dirty()) return;
            var prefs = {};
            boxes.forEach(function (b) { var p = b.name.split(':'); (prefs[p[0]] = prefs[p[0]] || {})[p[1]] = b.checked; });
            save.disabled = true; reset.disabled = true;
            var kept = OL.run('settings:save-notifications', form, { prefs: prefs },
                function () { boxes.forEach(function (b) { b.defaultChecked = b.checked; }); say('Saved.', 'ok'); if (window.olToast) window.olToast('Notification preferences saved.', 'success'); sync(); },
                function (m) { say(m, 'error'); save.disabled = false; reset.disabled = false; });
            if (!kept) sync();       // not connected: the toast was shown, the changes stay
        });
    }

    /* ---- Data export: idle, preparing, ready ---- */
    var box = $('[data-export]');
    if (box) {
        var btn = $('[data-export-btn]', box), label = $('span', btn), status = $('[data-export-status]', box), idleText = label.textContent;
        btn.addEventListener('click', function () {
            btn.disabled = true; label.textContent = 'Preparing\u2026'; box.setAttribute('data-state', 'busy'); status.textContent = '';
            var back = function () { btn.disabled = false; label.textContent = idleText; box.setAttribute('data-state', 'idle'); };
            var kept = OL.run('account:export', btn, {},
                function (res) {
                    back(); label.textContent = 'Request a new copy'; box.setAttribute('data-state', 'ready');
                    status.textContent = '';
                    if (res && res.url) {
                        var a = document.createElement('a'); a.href = res.url; a.className = 'link-arrow'; a.setAttribute('download', ''); a.textContent = 'Download your data';
                        status.appendChild(a);
                    } else status.textContent = 'Your copy is on its way.';
                },
                function (m) { back(); box.setAttribute('data-state', 'error'); status.textContent = m; });
            if (!kept) back();
        });
    }
})();
