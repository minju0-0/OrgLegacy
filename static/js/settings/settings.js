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
                        showToast('Password credentials updated.');
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
