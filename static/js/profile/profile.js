/*
 * Profile feature behavior: avatar URL preview, bio character counter,
 * and an asynchronous (AJAX) form submission that swaps in the
 * server-rendered result without a full page reload.
 *
 * Field ids (id_avatar_url, id_bio) are Django's default
 * "id_<field name>" ids for ProfileDetailsForm — see
 * apps/profile/forms.py.
 */

function bindProfileEvents() {
    // Avatar preview logic
    const avatarInput = document.getElementById('id_avatar_url');
    const avatarImg = document.getElementById('avatar-preview');
    const avatarFallback = document.getElementById('avatar-fallback');

    if (avatarInput && avatarImg && avatarFallback) {
        const updateAvatar = () => {
            const url = avatarInput.value.trim();
            if (url) {
                avatarImg.src = url;
            } else {
                avatarImg.classList.add('hidden');
                avatarFallback.classList.remove('hidden');
            }
        };
        avatarInput.addEventListener('input', updateAvatar);
        if (avatarInput.value.trim()) updateAvatar();
    }

    // Bio character counter logic
    const bioInput = document.getElementById('id_bio');
    const bioCountEl = document.getElementById('bio-count');
    const bioCounterContainer = document.getElementById('bio-counter');
    const MAX_LENGTH = 300;

    if (bioInput && bioCountEl) {
        const updateCounter = () => {
            const len = bioInput.value.length;
            bioCountEl.textContent = len;
            if (len > MAX_LENGTH) {
                bioCounterContainer.classList.add('limit-exceeded');
            } else {
                bioCounterContainer.classList.remove('limit-exceeded');
            }
        };
        bioInput.addEventListener('input', updateCounter);
        updateCounter();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    bindProfileEvents();

    const form = document.getElementById('profile-form');

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('save-profile-btn');
            const feedback = document.getElementById('inline-save-feedback');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = 'Recording changes...';
            feedback.textContent = '';

            try {
                const formData = new FormData(form);
                const res = await fetch(window.location.href, {
                    method: 'POST',
                    body: formData,
                });
                const html = await res.text();
                const doc = new DOMParser().parseFromString(html, 'text/html');

                const newForm = doc.getElementById('profile-form');
                const hasErrors = newForm && newForm.querySelector('.text-warm-crimson');

                if (hasErrors) {
                    form.innerHTML = newForm.innerHTML;
                    bindProfileEvents();
                    feedback.textContent = 'Please correct the indicated fields above.';
                    feedback.className = 'text-xs font-serif italic text-warm-crimson min-h-[1.25rem]';
                } else {
                    form.innerHTML = newForm.innerHTML;
                    bindProfileEvents();

                    const newFeedback = document.getElementById('inline-save-feedback');
                    if (newFeedback) {
                        newFeedback.textContent = 'Changes recorded to institutional profile.';
                        newFeedback.className = 'text-xs font-serif italic text-warm-moss min-h-[1.25rem]';
                    }

                    if (typeof showToast === 'function') {
                        showToast('Profile changes recorded successfully.');
                    }
                }
            } catch (err) {
                feedback.textContent = 'Unable to save changes. Please try again.';
                feedback.className = 'text-xs font-serif italic text-warm-crimson min-h-[1.25rem]';
            } finally {
                const newBtn = document.getElementById('save-profile-btn');
                if (newBtn) {
                    newBtn.disabled = false;
                    newBtn.textContent = originalText;
                }
            }
        });
    }
});
