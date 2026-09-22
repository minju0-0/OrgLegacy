/*
 * Settings feature behavior: show/hide password toggles, password
 * strength meter, password match indicator, danger-zone delete
 * confirmation gate, and an asynchronous password-change submission.
 *
 * Field ids (id_new_password1, id_new_password2, id_confirm) are
 * Django's default "id_<field name>" ids — see apps/settings/forms.py.
 */

function bindSettingsEvents() {
    // Show/Hide password toggles
    const toggles = document.querySelectorAll('.pwd-toggle');
    toggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const input = toggle.parentElement.querySelector('input');
            if (!input) return;
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            toggle.textContent = isPassword ? 'Hide' : 'Show';
        });
    });

    // Password validation & strength
    const newPwd1 = document.getElementById('id_new_password1');
    const newPwd2 = document.getElementById('id_new_password2');
    const matchIndicator = document.getElementById('pwd-match-indicator');

    const strengthColors = ['var(--warm-linen)', 'var(--warm-crimson)', 'var(--warm-walnut)', '#3d5a45', 'var(--warm-moss)'];

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

        bars.forEach(b => { if (b) b.style.backgroundColor = 'var(--warm-linen)'; });

        for (let i = 0; i < score; i++) {
            if (bars[i]) bars[i].style.backgroundColor = strengthColors[score];
        }
        if (text) text.textContent = `Password strength: ${labels[score]}`;
    };

    const checkMatch = () => {
        if (!newPwd1 || !newPwd2 || !matchIndicator) return;
        const p1 = newPwd1.value;
        const p2 = newPwd2.value;

        if (p2.length > 0) {
            matchIndicator.classList.remove('hidden');
            if (p1 === p2) {
                matchIndicator.textContent = 'Passwords match.';
                matchIndicator.className = 'mt-1.5 text-xs font-serif italic text-warm-moss';
            } else {
                matchIndicator.textContent = 'Passwords do not match.';
                matchIndicator.className = 'mt-1.5 text-xs font-serif italic text-warm-crimson';
            }
        } else {
            matchIndicator.classList.add('hidden');
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
        const checkDeleteEligibility = () => {
            deleteBtn.disabled = deleteInput.value.trim() !== 'DELETE';
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
                const hasErrors = newForm && newForm.querySelector('.text-warm-crimson');

                if (hasErrors) {
                    pwdForm.innerHTML = newForm.innerHTML;
                    bindSettingsEvents();
                    feedback.textContent = 'Please correct the issues indicated above.';
                    feedback.className = 'text-xs font-serif italic text-warm-crimson min-h-[1.25rem]';
                } else {
                    pwdForm.reset();
                    pwdForm.innerHTML = newForm.innerHTML;
                    bindSettingsEvents();

                    const newFeedback = document.getElementById('pwd-feedback-area');
                    if (newFeedback) {
                        newFeedback.textContent = 'Password has been updated successfully.';
                        newFeedback.className = 'text-xs font-serif italic text-warm-moss min-h-[1.25rem]';
                    }

                    if (typeof showToast === 'function') {
                        showToast('Password credentials updated.');
                    }
                }
            } catch (err) {
                feedback.textContent = 'Unable to update password. Please try again.';
                feedback.className = 'text-xs font-serif italic text-warm-crimson min-h-[1.25rem]';
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
