/** Disables the submit button on click to discourage duplicate/rapid submissions. */
document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('nhs_public_application_form');
    if (!form) {
        return;
    }
    form.addEventListener('submit', function () {
        var button = form.querySelector('button[type="submit"]');
        if (button) {
            button.disabled = true;
            button.textContent = 'Submitting…';
        }
    });
});
