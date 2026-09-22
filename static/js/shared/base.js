/*
 * Shared behavior used across every feature: the directional slide
 * transition between the Login and Register screens, and the global
 * toast helper. Lives under static/js/shared/ because both apps/login
 * and apps/register need it — a genuinely cross-cutting concern,
 * rather than something one feature should own.
 */

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('auth-split-layout');
    if (container) {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        // Handle incoming transition animation
        const incomingTransition = sessionStorage.getItem('orglegacy_auth_slide');
        if (incomingTransition && !prefersReducedMotion) {
            container.classList.add(incomingTransition === 'to-register' ? 'slide-in-from-right' : 'slide-in-from-left');
            sessionStorage.removeItem('orglegacy_auth_slide');
            setTimeout(() => {
                container.classList.remove('slide-in-from-right', 'slide-in-from-left');
            }, 350);
        }

        // Intercept navigation links between Login and Register for directional slide
        document.querySelectorAll('[data-auth-slide]').forEach(link => {
            link.addEventListener('click', (e) => {
                if (prefersReducedMotion) return;

                const targetDirection = link.getAttribute('data-auth-slide');
                e.preventDefault();
                const destination = link.href;
                sessionStorage.setItem('orglegacy_auth_slide', targetDirection);

                container.classList.add(targetDirection === 'to-register' ? 'slide-out-to-left' : 'slide-out-to-right');

                setTimeout(() => {
                    window.location.href = destination;
                }, 260);
            });
        });

        // Auto-expand password security requirements on focus
        const pwdInputs = document.querySelectorAll('input[type="password"]');
        const pwdDetails = document.getElementById('password-rules-details');
        if (pwdDetails && pwdInputs.length > 0) {
            pwdInputs.forEach(input => {
                input.addEventListener('focus', () => {
                    pwdDetails.open = true;
                });
            });
        }
    }
});

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');

    // Archival slip styling: crisp hairline border, warm paper background, classic serif type
    const isError = type === 'error';
    const borderColor = isError ? 'border-warm-crimson' : 'border-warm-espresso';
    const textColor = isError ? 'text-warm-crimson' : 'text-warm-espresso';

    toast.className = `flex items-center gap-3 bg-warm-vellum ${borderColor} ${textColor} border px-4 py-3 pointer-events-auto transform translate-y-3 opacity-0 transition-all duration-200 ease-out font-serif text-sm`;
    toast.innerHTML = `
        <span class="text-xs ${isError ? 'text-warm-crimson' : 'text-warm-walnut'} font-bold">&sect;</span>
        <span class="leading-snug">${message}</span>
    `;

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-3', 'opacity-0');
    });

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-1');
        setTimeout(() => toast.remove(), 250);
    }, 4500);
}
