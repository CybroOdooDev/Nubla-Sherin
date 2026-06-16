/* NHS Public Incident Report Form — client-side behaviour */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('nhs_public_report_form');
        if (!form) return;

        const token = (window.location.pathname.match(/\/incident\/report\/([^/]+)/) || [])[1];
        const DRAFT_KEY = 'nhs_incident_draft_' + (token || 'default');

        /* ── Person repeater ── */
        let personIndex = 1;
        const personList = document.getElementById('person_list');
        const addBtn = document.getElementById('add_person_btn');

        if (addBtn && personList) {
            addBtn.addEventListener('click', function () {
                const template = personList.querySelector('.person-row');
                if (!template) return;
                const clone = template.cloneNode(true);
                clone.dataset.index = personIndex;
                clone.querySelectorAll('input,select').forEach(function (el) {
                    el.name = el.name.replace(/_\d+$/, '_' + personIndex);
                    if (el.tagName === 'INPUT') el.value = '';
                    if (el.tagName === 'SELECT') el.selectedIndex = 0;
                });
                // Add remove button
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'btn btn-outline-danger btn-sm mt-1';
                removeBtn.textContent = 'Remove';
                removeBtn.addEventListener('click', function () {
                    clone.remove();
                    saveDraft();
                });
                clone.appendChild(removeBtn);
                personList.appendChild(clone);
                personIndex++;
            });
        }

        /* ── Anonymous toggle ── */
        const anonCheck = document.getElementById('anonymous_check');
        const reporterSection = document.getElementById('reporter_section');
        if (anonCheck && reporterSection) {
            anonCheck.addEventListener('change', function () {
                reporterSection.style.display = this.checked ? 'none' : 'block';
                saveDraft();
            });
        }

        /* ── Draft autosave ── */
        function getFormData() {
            const data = {};
            new FormData(form).forEach(function (val, key) {
                if (key !== 'csrf_token') data[key] = val;
            });
            return data;
        }

        function saveDraft() {
            try {
                localStorage.setItem(DRAFT_KEY, JSON.stringify(getFormData()));
            } catch (e) { /* storage unavailable */ }
        }

        function loadDraft() {
            try {
                const raw = localStorage.getItem(DRAFT_KEY);
                if (!raw) return;
                const data = JSON.parse(raw);
                Object.keys(data).forEach(function (key) {
                    const el = form.elements[key];
                    if (!el) return;
                    if (el.type === 'checkbox') {
                        el.checked = data[key] === 'on' || data[key] === true;
                    } else {
                        el.value = data[key];
                    }
                });
            } catch (e) { /* corrupted draft — ignore */ }
        }

        loadDraft();

        form.addEventListener('input', saveDraft);
        form.addEventListener('change', saveDraft);

        /* Clear draft on successful submit */
        form.addEventListener('submit', function () {
            try { localStorage.removeItem(DRAFT_KEY); } catch (e) {}
        });
    });
})();
