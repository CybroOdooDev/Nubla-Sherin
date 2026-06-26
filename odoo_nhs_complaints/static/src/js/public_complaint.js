/** @odoo-module */
/**
 * NHS Public Complaint Submission Form
 * Handles anonymous toggle and third-party UI logic.
 */

document.addEventListener('DOMContentLoaded', function () {
    const anonymousCheckbox = document.getElementById('is_anonymous');
    const contactFields = document.getElementById('contact_fields');
    const thirdPartyRadios = document.querySelectorAll('input[name="is_third_party"]');
    const typeRadios = document.querySelectorAll('input[name="record_type"]');

    function toggleContactFields() {
        if (anonymousCheckbox && anonymousCheckbox.checked) {
            if (contactFields) contactFields.style.display = 'none';
        } else {
            if (contactFields) contactFields.style.display = '';
        }
    }

    function enforcePalsOnlyAnonymous() {
        if (!anonymousCheckbox) return;
        const selectedType = document.querySelector('input[name="record_type"]:checked');
        if (selectedType && selectedType.value === 'complaint') {
            anonymousCheckbox.checked = false;
            anonymousCheckbox.disabled = true;
            const note = document.getElementById('anonymous_note');
            if (!note) {
                const msg = document.createElement('small');
                msg.id = 'anonymous_note';
                msg.className = 'text-muted';
                msg.textContent = 'Anonymous submissions are only available for PALS concerns.';
                anonymousCheckbox.parentElement.parentElement.appendChild(msg);
            }
        } else {
            anonymousCheckbox.disabled = false;
            const note = document.getElementById('anonymous_note');
            if (note) note.remove();
        }
        toggleContactFields();
    }

    if (anonymousCheckbox) {
        anonymousCheckbox.addEventListener('change', toggleContactFields);
    }

    typeRadios.forEach(function (radio) {
        radio.addEventListener('change', enforcePalsOnlyAnonymous);
    });

    // Initialize
    toggleContactFields();
    enforcePalsOnlyAnonymous();
});
