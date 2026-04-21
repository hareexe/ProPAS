let cur = 0;
const TOTAL = 5;

function needsBudget() {
    const selected = document.querySelector('input[name="needs_budget"]:checked');
    return (selected?.value || 'yes') !== 'no';
}

function getVisibleSections() {
    return needsBudget() ? [0, 1, 2, 3, 4] : [0, 1, 2, 4];
}

// ─── Navigation ───────────────────────────────────────────────────────────────

function goTo(idx) {
    const visibleSections = getVisibleSections();
    if (!visibleSections.includes(idx)) {
        idx = visibleSections.includes(4) && idx >= 3 ? 4 : visibleSections[0];
    }
    idx = Math.min(Math.max(idx, 0), TOTAL - 1);

    document.querySelectorAll('.form-section').forEach((s, i) => s.classList.toggle('active', i === idx));
    document.querySelectorAll('.section-nav button').forEach((button, i) => {
        if (i === 3) {
            button.style.display = needsBudget() ? '' : 'none';
        }
        button.classList.toggle('active', i === idx);
    });

    cur = idx;

    const stepIndicator = document.getElementById('currentStep');
    const totalStepsIndicator = document.getElementById('totalSteps');
    const progressBar   = document.getElementById('progressBar');
    const currentVisibleIndex = Math.max(visibleSections.indexOf(idx), 0);
    if (stepIndicator) stepIndicator.textContent = currentVisibleIndex + 1;
    if (totalStepsIndicator) totalStepsIndicator.textContent = visibleSections.length;
    if (progressBar)   progressBar.style.width   = `${((currentVisibleIndex + 1) / visibleSections.length) * 100}%`;

    const isFirst = currentVisibleIndex === 0;
    const isLast  = currentVisibleIndex === visibleSections.length - 1;

    const btnHome    = document.getElementById('btnHome');
    const btnBack    = document.getElementById('btnBack');
    const btnNext    = document.getElementById('btnNext');
    const btnSubmit  = document.getElementById('btnSubmit');
    const btnPreview = document.getElementById('btnPreview');

    if (btnHome)    btnHome.style.display    = isFirst  ? 'inline-flex' : 'none';
    if (btnBack)    btnBack.style.display    = !isFirst ? 'inline-flex' : 'none';
    if (btnNext)    btnNext.style.display    = !isLast  ? 'inline-flex' : 'none';
    if (btnSubmit)  btnSubmit.style.display  = isLast   ? 'inline-flex' : 'none';
    if (btnPreview) btnPreview.style.display = isLast   ? 'inline-flex' : 'none';
}

function navigate(dir) {
    const visibleSections = getVisibleSections();
    const currentVisibleIndex = Math.max(visibleSections.indexOf(cur), 0);
    const nextVisibleIndex = Math.min(Math.max(currentVisibleIndex + dir, 0), visibleSections.length - 1);
    goTo(visibleSections[nextVisibleIndex]);
}

// ─── Budget ───────────────────────────────────────────────────────────────────

function addBudgetRow() { addBudgetRowWithValues(); }

function addBudgetRowWithValues(item = {}) {
    const tbody = document.getElementById('budgetRows');
    if (!tbody) return;

    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${tbody.rows.length + 1}</td>
        <td><input type="text"   class="bud-desc bud-input" placeholder="Item name" required></td>
        <td><input type="number" class="bud-qty  bud-input" min="1"  step="1"    required oninput="calcTotal()"></td>
        <td><input type="number" class="bud-unit bud-input" min="0"  step="0.01" required oninput="calcTotal()"></td>
        <td class="row-total">PHP 0.00</td>
        <td><button type="button" class="btn-danger-small"
                onclick="this.closest('tr').remove(); calcTotal(); renumberRows();">X</button></td>
    `;
    tbody.appendChild(row);

    row.querySelector('.bud-desc').value = item.description || '';
    row.querySelector('.bud-qty').value  = item.quantity  ?? 1;
    row.querySelector('.bud-unit').value = item.unit_cost ?? 0;
    calcTotal();
}

function renumberRows() {
    document.querySelectorAll('#budgetRows tr').forEach((row, i) => {
        row.cells[0].textContent = i + 1;
    });
}

function calcTotal() {
    if (!needsBudget()) {
        const totalDisplay      = document.getElementById('budgetTotal');
        const hiddenBudget      = document.getElementById('id_budget');
        const hiddenBudgetItems = document.getElementById('id_budget_items');
        if (totalDisplay)      totalDisplay.textContent = 'PHP 0.00';
        if (hiddenBudget)      hiddenBudget.value = 0;
        if (hiddenBudgetItems) hiddenBudgetItems.value = '[]';
        return;
    }

    let grandTotal = 0;
    const budgetItems = [];

    document.querySelectorAll('#budgetRows tr').forEach(row => {
        const qty  = parseFloat(row.querySelector('.bud-qty')?.value)  || 0;
        const unit = parseFloat(row.querySelector('.bud-unit')?.value) || 0;
        const desc = row.querySelector('.bud-desc')?.value?.trim()     || '';
        const total = qty * unit;
        grandTotal += total;

        budgetItems.push({ description: desc, quantity: qty, unit_cost: unit });

        const cell = row.querySelector('.row-total');
        if (cell) cell.textContent = 'PHP ' + total.toLocaleString('en-PH', { minimumFractionDigits: 2 });
    });

    const totalDisplay      = document.getElementById('budgetTotal');
    const hiddenBudget      = document.getElementById('id_budget');
    const hiddenBudgetItems = document.getElementById('id_budget_items');

    if (totalDisplay)      totalDisplay.textContent = 'PHP ' + grandTotal.toLocaleString('en-PH', { minimumFractionDigits: 2 });
    if (hiddenBudget)      hiddenBudget.value        = grandTotal;
    if (hiddenBudgetItems) hiddenBudgetItems.value   = JSON.stringify(budgetItems);
}

function toggleBudgetSection() {
    const budgetSection = document.getElementById('section-3');
    const budgetNavButton = document.getElementById('budgetNavButton');
    const budgetRequired = needsBudget();
    const budgetFields = ['id_budget', 'id_funding_source'];

    if (budgetSection) budgetSection.style.display = budgetRequired ? '' : 'none';
    if (budgetNavButton) budgetNavButton.style.display = budgetRequired ? '' : 'none';

    budgetFields.forEach(id => {
        const field = document.getElementById(id);
        if (!field) return;
        field.required = budgetRequired;
        if (!budgetRequired) field.value = id === 'id_budget' ? 0 : '';
    });

    const budgetItemsField = document.getElementById('id_budget_items');
    if (!budgetRequired && budgetItemsField) budgetItemsField.value = '[]';

    const budgetRows = document.getElementById('budgetRows');
    if (budgetRows && !budgetRequired) {
        budgetRows.innerHTML = '';
    } else if (budgetRows && budgetRequired && !budgetRows.children.length) {
        addBudgetRow();
    }

    calcTotal();
    if (!budgetRequired && cur === 3) {
        goTo(4);
        return;
    }
    goTo(cur);
}

// ─── Time helpers ─────────────────────────────────────────────────────────────

const APPROACH_TIME_PATTERN = /^\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?\s*$/i;

function normalizeTimeValue(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return '';

    const exact = raw.match(/^(\d{2}):(\d{2})$/);
    if (exact) {
        const h = Number(exact[1]), m = Number(exact[2]);
        return (h >= 0 && h <= 23 && m >= 0 && m <= 59)
            ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}` : '';
    }

    const match = raw.match(APPROACH_TIME_PATTERN);
    if (!match) return '';

    let h = Number(match[1]);
    const m        = Number(match[2] || '0');
    const meridiem = (match[3] || '').toUpperCase();

    if (meridiem) {
        if (!(h >= 1 && h <= 12 && m >= 0 && m <= 59)) return '';
        h = meridiem === 'AM' ? (h === 12 ? 0 : h) : (h === 12 ? 12 : h + 12);
    } else if (!(h >= 0 && h <= 23 && m >= 0 && m <= 59)) {
        return '';
    }

    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

function extractTimeRange(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return ['', ''];
    const match = raw.match(/^(.*?)\s*(?:-|–|—|to)\s*(.*?)$/i);
    return match ? [normalizeTimeValue(match[1]), normalizeTimeValue(match[2])] : ['', ''];
}

function formatTimeLabel(value) {
    const n = normalizeTimeValue(value);
    if (!n) return '';
    const [hs, ms] = n.split(':');
    const h = Number(hs), m = Number(ms);
    return `${h % 12 || 12}:${String(m).padStart(2,'0')} ${h >= 12 ? 'PM' : 'AM'}`;
}

function formatTimeRange(startTime, endTime, fallback = '') {
    const s = normalizeTimeValue(startTime);
    const e = normalizeTimeValue(endTime);
    return (s && e) ? `${formatTimeLabel(s)} - ${formatTimeLabel(e)}` : String(fallback ?? '').trim();
}

// ─── Approach ─────────────────────────────────────────────────────────────────

function parseLegacyApproachItems(rawValue) {
    const raw = String(rawValue ?? '').trim();
    if (!raw) return [];

    return raw.split(/\r?\n/).map(line => {
        const text = line.trim();
        if (!text) return null;
        const parts = text.split('|', 3).map(p => p.trim());
        let timeValue = '', activity = '', remarks = '';

        if (parts.length === 3)      [timeValue, activity, remarks] = parts;
        else if (parts.length === 2) [timeValue, activity]          = parts;
        else                         remarks = text;

        const [startTime, endTime] = extractTimeRange(timeValue);
        return { time: formatTimeRange(startTime, endTime, timeValue), start_time: startTime, end_time: endTime, activity, remarks };
    }).filter(Boolean);
}

function getInitialApproachItems() {
    const items = Array.isArray(window.initialApproachItems) ? window.initialApproachItems : loadJsonScriptValue('initialApproachItems', []);
    const initialText = typeof window.initialApproachText === 'string' ? window.initialApproachText : loadJsonScriptValue('initialApproachText', '');
    return items.length ? items : parseLegacyApproachItems(initialText || '');
}

function getApproachRowsData() {
    return Array.from(document.querySelectorAll('#approachRows tr')).map(row => {
        const startTime = normalizeTimeValue(row.querySelector('.approach-start')?.value);
        const endTime   = normalizeTimeValue(row.querySelector('.approach-end')?.value);
        const activity  = String(row.querySelector('.approach-activity')?.value ?? '').trim();
        const remarks   = String(row.querySelector('.approach-remarks')?.value  ?? '').trim();
        const time      = formatTimeRange(startTime, endTime);
        if (!(time || activity || remarks)) return null;
        return { time, start_time: startTime, end_time: endTime, activity, remarks };
    }).filter(Boolean);
}

function serializeApproachItems(items) {
    return items.map(item => {
        const t = formatTimeRange(item.start_time, item.end_time, item.time);
        return `${t} | ${String(item.activity ?? '').trim()} | ${String(item.remarks ?? '').trim()}`.trim();
    }).filter(Boolean).join('\n');
}

function syncApproachData() {
    const items             = getApproachRowsData();
    const hiddenApproach    = document.getElementById('id_approach');
    const hiddenApproachItems = document.getElementById('id_approach_items');
    const serialized = serializeApproachItems(items);
    if (hiddenApproach)      hiddenApproach.value      = serialized;
    if (hiddenApproachItems) hiddenApproachItems.value = JSON.stringify(items);
    const counter = document.getElementById('approach-count');
    if (counter && hiddenApproach) counter.textContent = `${hiddenApproach.value.length} / ${hiddenApproach.maxLength || 2000}`;
}

function addApproachRow() { addApproachRowWithValues(); }

function addApproachRowWithValues(item = {}) {
    const tbody = document.getElementById('approachRows');
    if (!tbody) return;

    let startTime = normalizeTimeValue(item.start_time);
    let endTime   = normalizeTimeValue(item.end_time);

    if (!(startTime && endTime) && item.time) {
        const [ls, le] = extractTimeRange(item.time);
        startTime = startTime || ls;
        endTime   = endTime   || le;
    }

    const row = document.createElement('tr');
    row.innerHTML = `
        <td>
            <div class="approach-time-range">
                <div class="approach-time-row">
                    <span class="approach-time-badge">From</span>
                    <input type="time" class="approach-input approach-input--time approach-start" required>
                </div>
                <div class="approach-time-divider"></div>
                <div class="approach-time-row">
                    <span class="approach-time-badge">To</span>
                    <input type="time" class="approach-input approach-input--time approach-end" required>
                </div>
            </div>
        </td>
        <td><input type="text" class="approach-input approach-activity" placeholder="Activity" required></td>
        <td><textarea class="approach-input approach-input--remarks approach-remarks" rows="3" placeholder="Description / remarks" required></textarea></td>
        <td><button type="button" class="btn-danger-small" onclick="this.closest('tr').remove(); syncApproachData();">X</button></td>
    `;
    tbody.appendChild(row);

    row.querySelector('.approach-start').value    = startTime;
    row.querySelector('.approach-end').value      = endTime;
    row.querySelector('.approach-activity').value = String(item.activity ?? '');
    row.querySelector('.approach-remarks').value  = String(item.remarks  ?? '');

    row.querySelectorAll('input, textarea').forEach(input => {
        input.addEventListener('input',  syncApproachData);
        input.addEventListener('change', syncApproachData);
    });
    syncApproachData();
}

// ─── UI helpers ───────────────────────────────────────────────────────────────

function countChars(el, id) {
    const counter = document.getElementById(id);
    if (counter) counter.textContent = `${el.value.length} / ${el.maxLength}`;
}

function updateSdgCount() {
    const counter = document.getElementById('unsdg-count');
    if (counter) counter.textContent = `${document.querySelectorAll('input[name="unsdg_goals"]:checked').length} selected`;
}

function updateProgress() {
    if (cur !== 0) return;
    const n = ['id_title', 'id_sponsor'].filter(id => document.getElementById(id)?.value.trim()).length;
    const bar = document.getElementById('progressBar');
    if (bar) bar.style.width = `${20 + n * 8}%`;
}

// ─── Data helpers ─────────────────────────────────────────────────────────────

const g   = id    => (document.getElementById(id) || {}).value || '';
const esc = value => String(value ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const fmt = value => Number(value || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function formatEventDate(value) {
    if (!value) return '';
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? value
        : date.toLocaleDateString('en-PH', { year: 'numeric', month: 'long', day: 'numeric' });
}

function getVenueDisplay() {
    const venue = g('id_venue');
    return venue === 'Others' ? g('id_venue_other').trim() : venue;
}

function getSelectedSdgs() {
    return Array.from(document.querySelectorAll('input[name="unsdg_goals"]:checked'))
        .map(i => i.value.trim()).filter(Boolean);
}

function toggleVenueOther() {
    const venueSelect    = document.getElementById('id_venue');
    const venueOtherField = document.getElementById('venueOtherField');
    const venueOtherInput = document.getElementById('id_venue_other');
    const showOther = venueSelect?.value === 'Others';

    if (venueOtherField) venueOtherField.style.display = showOther ? 'block' : 'none';
    if (venueOtherInput) {
        venueOtherInput.required = !!showOther;
        if (!showOther) venueOtherInput.value = '';
    }
}

// ─── Proposal data resolver ───────────────────────────────────────────────────
// Returns a plain object with all fields needed by buildDocHTML().
// When `src` is provided (e.g. window.proposalViewData on office/view pages)
// the data is read from that object; otherwise it falls back to the live DOM
// (the create-proposal form).

function resolveProposalData(src) {
    // ── Data-object path (office / view pages) ────────────────────────────────
    if (src && typeof src === 'object') {
        const approachItems = (() => {
            if (Array.isArray(src.approach_items) && src.approach_items.length)
                return src.approach_items;
            return parseLegacyApproachItems(src.approach_list || '');
        })();

        const budgetItems = Array.isArray(src.budget_items) ? src.budget_items : [];

        const venueValue  = src.venue || '';
        const venueDisplay = venueValue === 'Others'
            ? String(src.venue_other || '').trim()
            : venueValue;

        const sdgs = (() => {
            const v = src.unsdg_goals;
            if (Array.isArray(v))        return v.map(x => String(x).trim()).filter(Boolean);
            if (typeof v === 'string')   return v.split(',').map(x => x.trim()).filter(Boolean);
            return [];
        })();

        const signedRoles = (src.signed_roles && typeof src.signed_roles === 'object')
            ? src.signed_roles
            : {};

        return {
            title:          src.title          || '',
            sponsor:        src.sponsor        || '',
            event_date:     src.event_date     || '',
            venue:          venueDisplay,
            participation:  src.participation  || '',
            rationale:      src.rationale      || '',
            objectives:     src.objectives_list|| '',
            outcome:        src.expected_outcome || '',
            budget:         src.budget         || 0,
            funding_source: src.funding_source || '',
            sig_president:  src.signatory_ProjPresident || '',
            sig_adviser:    src.signatory_adviser       || '',
            sig_dept:       src.signatory_dept_head     || '',
            needs_budget:   String(src.needs_budget || 'yes') !== 'no',
            sdgs,
            approachItems,
            budgetItems,
            signedRoles,
        };
    }

    // ── Live-DOM path (create-proposal form) ──────────────────────────────────
    return {
        title:          g('id_title'),
        sponsor:        g('id_sponsor'),
        event_date:     g('id_event_date'),
        venue:          getVenueDisplay(),
        participation:  g('id_participation'),
        rationale:      g('id_rationale'),
        objectives:     g('id_objectives'),
        outcome:        g('id_outcome'),
        budget:         g('id_budget'),
        funding_source: g('id_funding_source'),
        sig_president:  g('id_sig_president'),
        sig_adviser:    g('id_sig_adviser'),
        sig_dept:       g('id_sig_dept'),
        needs_budget:   needsBudget(),
        sdgs:           getSelectedSdgs(),
        approachItems:  getApproachRowsData(),
        budgetItems:    null,   // read directly from DOM rows below
        signedRoles:    {},
    };
}

// ─── Validation ───────────────────────────────────────────────────────────────

function showFieldError(field, message, sectionIndex = null) {
    if (sectionIndex !== null) goTo(sectionIndex);
    if (field) {
        field.focus();
        field.setCustomValidity(message || ' ');
        field.reportValidity();
        field.setCustomValidity('');
        return;
    }
    if (message) alert(message);
}

function validateProposalForm() {
    toggleVenueOther();
    calcTotal();
    syncApproachData();
    const budgetRequired = needsBudget();

    const requiredFieldSections = [
        ['id_title',          0], ['id_sponsor',       0], ['id_event_date',  0],
        ['id_venue',          0], ['id_participation', 0], ['id_rationale',   1],
        ['id_approach',       1], ['id_objectives',    2], ['id_outcome',     2],
        ['id_sig_president',4],
        ['id_sig_adviser',    4], ['id_sig_dept',      4]
    ];

    if (budgetRequired) {
        requiredFieldSections.splice(9, 0, ['id_budget', 3], ['id_funding_source', 3]);
    }

    if (document.getElementById('id_venue')?.value === 'Others') {
        requiredFieldSections.splice(4, 0, ['id_venue_other', 0]);
    }

    for (const [fieldId, sectionIndex] of requiredFieldSections) {
        const field = document.getElementById(fieldId);
        if (field && !field.checkValidity()) {
            showFieldError(field, '', sectionIndex);
            return false;
        }
    }

    if (!getSelectedSdgs().length) {
        showFieldError(document.querySelector('input[name="unsdg_goals"]'), 'Select at least one UNSDG target.', 2);
        return false;
    }

    const approachRows = Array.from(document.querySelectorAll('#approachRows tr'));
    if (!approachRows.length) { goTo(1); alert('Add at least one approach schedule row.'); return false; }

    for (const row of approachRows) {
        const startInput    = row.querySelector('.approach-start');
        const endInput      = row.querySelector('.approach-end');
        const activityInput = row.querySelector('.approach-activity');
        const remarksInput  = row.querySelector('.approach-remarks');
        const startTime     = normalizeTimeValue(startInput?.value);
        const endTime       = normalizeTimeValue(endInput?.value);

        if (!startTime)           { showFieldError(startInput,    'Every approach row needs a start time.',              1); return false; }
        if (!endTime)             { showFieldError(endInput,      'Every approach row needs an end time.',               1); return false; }
        if (startTime >= endTime) { showFieldError(endInput,      'Every approach row must end after it starts.',        1); return false; }
        if (!String(activityInput?.value ?? '').trim()) { showFieldError(activityInput, 'Every approach row needs an activity.',          1); return false; }
        if (!String(remarksInput?.value  ?? '').trim()) { showFieldError(remarksInput,  'Every approach row needs a description/remarks.',1); return false; }
    }

    if (budgetRequired) {
        const budgetRows = Array.from(document.querySelectorAll('#budgetRows tr'));
        if (!budgetRows.length) { goTo(3); alert('Add at least one budget item.'); return false; }

        for (const row of budgetRows) {
            const desc = row.querySelector('.bud-desc');
            const qty  = row.querySelector('.bud-qty');
            const unit = row.querySelector('.bud-unit');
            if (!desc.value.trim())   { showFieldError(desc, 'Enter a budget item description.', 3); return false; }
            if (!qty.checkValidity()) { showFieldError(qty,  '',                                  3); return false; }
            if (!unit.checkValidity()){ showFieldError(unit, '',                                  3); return false; }
        }
    }

    return true;
}

// ─── PDF helpers ──────────────────────────────────────────────────────────────

function getPdfOptions() {
    return {
        margin: 0,
        filename: 'proposal.pdf',
        image:      { type: 'jpeg', quality: 0.98 },
        html2canvas:{ scale: 2, useCORS: true, allowTaint: false, logging: false,
                      imageTimeout: 15000, scrollX: 0, scrollY: -window.scrollY, windowWidth: 794 },
        jsPDF:      { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:  { mode: ['css', 'legacy'] }
    };
}

function getPdfLogoUrl() {
    const path = window.nwuLogoUrl || '/static/images/NWUlogo.jpg';
    try { return new URL(path, window.location.origin).href; } catch { return path; }
}

function nextRenderFrame() {
    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 200))));
}

function waitForPdfImages(container) {
    const images = Array.from(container.querySelectorAll('img'));
    if (!images.length) return Promise.resolve();
    return Promise.all(images.map(img => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return new Promise(resolve => {
            img.addEventListener('load',  resolve, { once: true });
            img.addEventListener('error', resolve, { once: true });
        });
    }));
}

async function renderPdfDocument(callback) {
    const target = document.getElementById('printTarget');
    if (!target) throw new Error('PDF render target is missing.');

    target.innerHTML = buildDocHTML();
    target.removeAttribute('style');
    Object.assign(target.style, {
        display: 'block', position: 'fixed', top: '0', left: '-9999px',
        width: '794px', zIndex: '9999', background: 'white', overflow: 'visible'
    });

    try {
        await waitForPdfImages(target);
        await nextRenderFrame();
        return await callback(target);
    } finally {
        target.innerHTML = '';
        target.removeAttribute('style');
        target.style.display = 'none';
    }
}

// ─── Signature block helper ───────────────────────────────────────────────────

function sigBlock(nameValue, label) {
    const displayName = String(nameValue ?? '').trim().toUpperCase();
    return `
        <div style="margin-bottom:24px;text-align:center;width:220px;">
          <div style="min-height:36px;padding:1px 3px;">${esc(displayName)}</div>
          <div style="border-top:1.5px solid #000;margin-bottom:4px;"></div>
          <span style="font-style:italic;font-weight:700;font-size:10pt;display:block;">${label}</span>
        </div>`;
  }

function officeSigBlock(nameValue, label, header = '') {
    const displayName = String(nameValue ?? '').trim().toUpperCase();
    return `
      <div class="sig-block${header === 'APPROVED:' ? ' sig-double' : ''}">
        ${header ? `<div class="sig-header">${header}</div>` : ''}
        <div>
          <div style="min-height:24px;text-align:center;font-weight:700;margin-bottom:4px;">${esc(displayName)}</div>
          <div class="sig-line"></div>
          <span class="sig-label">${esc(label)}</span>
        </div>
      </div>`;
}

// ─── Document HTML builder ────────────────────────────────────────────────────
// Accepts an optional `dataSrc` argument.
// • Pass window.proposalViewData (or any plain object) on office / view pages.
// • Call with no argument on the create-proposal form — falls back to live DOM.

function buildDocHTML(dataSrc) {
    const data = resolveProposalData(dataSrc ?? window.proposalViewData ?? null);
    const signedRoles = data.signedRoles || {};
    const needsBudgetSection = data.needs_budget !== false;

    /* ── Budget rows ── */
    let budgetRowsHTML = '';
    let grandTotal = 0;

    // Use resolved budget items when available (data-object path),
    // otherwise fall back to reading the live DOM table rows.
    const budgetSource = data.budgetItems;

    if (budgetSource) {
        budgetSource.forEach((item, i) => {
            const qty   = parseFloat(item.quantity)  || 0;
            const unit  = parseFloat(item.unit_cost) || 0;
            const total = qty * unit;
            grandTotal += total;
            budgetRowsHTML += `
                <tr>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:center;">${i + 1}</td>
                    <td style="border:1px solid #000;padding:4px 8px;">${esc(item.description || '')}</td>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:center;">${qty}</td>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:right;">PHP ${fmt(unit)}</td>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:right;">PHP ${fmt(total)}</td>
                </tr>`;
        });
    } else {
        document.querySelectorAll('#budgetRows tr').forEach((row, i) => {
            const desc  = row.querySelector('.bud-desc')?.value || '';
            const qty   = parseFloat(row.querySelector('.bud-qty')?.value)  || 0;
            const unit  = parseFloat(row.querySelector('.bud-unit')?.value) || 0;
            const total = qty * unit;
            grandTotal += total;
            budgetRowsHTML += `
                <tr>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:center;">${i + 1}</td>
                    <td style="border:1px solid #000;padding:4px 8px;">${esc(desc)}</td>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:center;">${qty}</td>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:right;">PHP ${fmt(unit)}</td>
                    <td style="border:1px solid #000;padding:4px 8px;text-align:right;">PHP ${fmt(total)}</td>
                </tr>`;
        });
    }

    /* ── Objectives ── */
    const objHTML = data.objectives.split('\n').filter(l => l.trim()).map((line, i) => `
        <div style="display:flex;gap:6px;margin-bottom:3px;">
            <span style="min-width:18px;">${i + 1}.</span>
            <span style="flex:1;min-height:17px;padding:1px 2px;white-space:pre-wrap;">${esc(line)}</span>
        </div>`).join('');

    /* ── Approach rows ── */
    const approachItems = data.approachItems;
    const approachRowsHTML = approachItems.map(item => `
        <tr>
          <td style="border:1px solid #000;padding:5px 8px;vertical-align:top;white-space:nowrap;">${esc(formatTimeRange(item.start_time, item.end_time, item.time))}</td>
          <td style="border:1px solid #000;padding:5px 8px;vertical-align:top;">${esc(item.activity)}</td>
          <td style="border:1px solid #000;padding:5px 8px;vertical-align:top;white-space:pre-wrap;">${esc(item.remarks)}</td>
        </tr>`).join('');

    /* ── Shared partials ── */
    const letterhead = `
    <div style="text-align:center;margin-bottom:8px;">
        <img src="${getPdfLogoUrl()}" style="display:block;height:70px;width:auto;margin:0 auto 4px;" alt="NWU Logo">
        <h2 style="font-size:12pt;font-weight:700;letter-spacing:.05em;margin:4px 0 0;">NORTHWESTERN UNIVERSITY</h2>
        <p style="font-size:9pt;margin:2px 0 4px;">Don Mariano Marcos Avenue, Laoag City, 2900, Ilocos Norte, Philippines</p>
        <hr style="border:none;border-top:2px solid #000;margin:0 0 8px;">
    </div>`;

    const pageFooter = `
      <div style="display:flex;border:1.5px solid #000;font-size:8.5pt;color:#000;margin-top:auto;">
        <div style="flex:1;border-right:1.5px solid #000;padding:4px 6px;"><strong>Issue Status:</strong> 4</div>
        <div style="flex:1;border-right:1.5px solid #000;padding:4px 6px;"><strong>Revision:</strong> 2</div>
        <div style="flex:1;border-right:1.5px solid #000;padding:4px 6px;"><strong>Date:</strong> 15 April 2025</div>
        <div style="flex:1;padding:4px 6px;"><strong>Approved by:</strong> President</div>
      </div>`;

    return `
    <style>
      @page { size: A4 portrait; margin: 20mm 18mm; }
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      html, body { width: 100%; height: 100%; }
      body { font-family: Arial, sans-serif; background: white; }
      table  { page-break-inside: auto; }
      tbody  { page-break-inside: auto; }
      tr, td, th { page-break-inside: avoid; break-inside: avoid; }
      thead  { display: table-header-group; }
      tfoot  { display: table-row-group; }
      .avoid-break { page-break-inside: avoid; break-inside: avoid-page; }

      /* ── Pages ── */
    .doc-page {
        width: 794px; margin: 0 auto;
        padding: 12mm 16mm 12mm;
        page-break-after: always;
        page-break-inside: avoid;
        display: flex; flex-direction: column;
        font-family: Arial, sans-serif; font-size: 10.5pt; color: #000;
        line-height: 1.4; background: white; text-align: justify;
    }
    .signature-page { page-break-before: always; }

      /* ── Signature grid ── */
      .sig-grid  { display: grid; grid-template-columns: 1fr 1fr; gap: 48px 24px; margin-top: 36px; }
      .sig-block { display: flex; flex-direction: column; }
      .sig-header{ font-weight: 700; margin-bottom: 36px; }
      .sig-line  { border-top: 1px solid #000; width: 220px; margin: 0 auto 4px; }
      .sig-label { text-align: center; font-style: italic; font-weight: 700;
                   font-size: 10pt; display: block; width: 220px; margin: 0 auto; }

      /* APPROVED block — two sigs stacked, aligned with "Itemized Budget" row */
      .sig-double { display: flex; flex-direction: column; gap: 32px; }
    </style>

    <!-- ═══════════════════ PAGE 1 — Proposal body ═══════════════════ -->
    <div class="doc-page">
      ${letterhead}

      <!-- Title bar -->
      <div style="display:flex;border:1.5px solid #000;margin:12px 0 14px;">
        <div style="flex:1;text-align:center;font-weight:700;font-size:11pt;
                    padding:6px 4px;border-right:1.5px solid #000;letter-spacing:.1em;">PROJECT PROPOSAL</div>
        <div style="padding:6px 12px;font-weight:700;font-size:11pt;
                    display:flex;align-items:center;white-space:nowrap;">OSA-F05A</div>
      </div>

      <!-- I -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">I.</span>
        <div style="flex:1;">
          <strong>Project Proposal Title:</strong>
          <div style="min-height:18px;padding:1px 3px;">${esc(data.title)}</div>
        </div>
      </div>

      <!-- II -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">II.</span>
        <div style="flex:1;">
          <strong>Sponsor / Organization:</strong>
          <div style="min-height:18px;padding:1px 3px;">${esc(data.sponsor)}</div>
        </div>
      </div>

      <!-- III -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">III.</span>
        <div style="flex:1;">
          <strong>Date &amp; Venue:</strong>
          <div>Date: ${esc(formatEventDate(data.event_date) || 'N/A')}</div>
          <div>Venue: ${esc(data.venue || 'N/A')}</div>
        </div>
      </div>

      <!-- IV -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">IV.</span>
        <div style="flex:1;">
          <strong>Target Participants:</strong>
          <div style="min-height:18px;padding:1px 3px;">${esc(data.participation)}</div>
        </div>
      </div>

      <!-- V -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">V.</span>
        <div style="flex:1;">
          <strong>Background / Rationale:</strong>
          <div style="white-space:pre-wrap;min-height:60px;padding:1px 3px;">${esc(data.rationale)}</div>
        </div>
      </div>

      <!-- VI -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">VI.</span>
        <div style="flex:1;">
          <strong>Objectives:</strong>
          ${objHTML || '<div style="min-height:18px;">&nbsp;</div>'}
        </div>
      </div>

      <!-- VII -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">VII.</span>
        <div style="flex:1;">
          <strong>UNSDGs:</strong>
          <div style="white-space:pre-wrap;padding:1px 3px;">${esc(data.sdgs.join(', ') || 'N/A')}</div>
        </div>
      </div>

      <!-- VIII -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">VIII.</span>
        <div style="flex:1;">
          <strong>Approach / Process:</strong>
          ${approachItems.length ? `
          <table class="avoid-break" style="width:100%;border-collapse:collapse;font-size:10pt;margin-top:8px;">
            <thead>
              <tr>
                <th style="border:1px solid #000;padding:5px 8px;text-align:left;">Time</th>
                <th style="border:1px solid #000;padding:5px 8px;text-align:left;">Activity</th>
                <th style="border:1px solid #000;padding:5px 8px;text-align:left;">Description / Remarks</th>
              </tr>
            </thead>
            <tbody>${approachRowsHTML}</tbody>
          </table>` : `
          <div style="white-space:pre-wrap;min-height:60px;padding:1px 3px;">${esc(data.rationale)}</div>`}
        </div>
      </div>

      <!-- IX -->
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">IX.</span>
        <div style="flex:1;">
          <strong>Expected Outcomes:</strong>
          <div style="white-space:pre-wrap;min-height:40px;padding:1px 3px;">${esc(data.outcome)}</div>
        </div>
      </div>

      ${needsBudgetSection ? `
      <!-- X -->
      <div class="avoid-break" style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;">X.</span>
        <div style="flex:1;">
          <strong>Budget</strong>
          <div style="margin:8px 0 4px;">
            <strong>a. Proposed Budget:</strong>
            <span style="border-bottom:1px solid #000;min-width:120px;display:inline-block;padding:1px 3px;">PHP ${fmt(data.budget)}</span>
          </div>
          <table class="avoid-break" style="width:100%;border-collapse:collapse;font-size:10pt;">
            <thead>
              <tr>
                <th style="border:1px solid #000;padding:4px 8px;">#</th>
                <th style="border:1px solid #000;padding:4px 8px;">Item</th>
                <th style="border:1px solid #000;padding:4px 8px;">Qty</th>
                <th style="border:1px solid #000;padding:4px 8px;">Unit Price</th>
                <th style="border:1px solid #000;padding:4px 8px;">Amount</th>
              </tr>
            </thead>
            <tbody>${budgetRowsHTML}</tbody>
            <tfoot>
              <tr>
                <td colspan="4" style="border:1px solid #000;padding:4px 8px;text-align:right;font-weight:700;">TOTAL</td>
                <td style="border:1px solid #000;padding:4px 8px;text-align:right;font-weight:700;">PHP ${fmt(grandTotal)}</td>
              </tr>
            </tfoot>
          </table>
          <div style="margin-top:8px;">
            <strong>c. Source of Funding:</strong>
            <span style="border-bottom:1px solid #000;min-width:200px;display:inline-block;padding:1px 3px;">${esc(data.funding_source)}</span>
          </div>
        </div>
      </div>` : ''}

      <!-- Approval signatures — right-aligned column -->
      <div style="margin-top:20px;display:flex;justify-content:flex-end;">
          <div style="display:flex;flex-direction:column;align-items:center;width:50%;">
          ${sigBlock(data.sig_president, 'President / Project Coordinator')}
          ${sigBlock(data.sig_adviser,   'Person In-Charge / Adviser')}
          ${sigBlock(data.sig_dept,      'Department / Program Head')}
          ${sigBlock(signedRoles.CAS || '', 'CAS Dean')}
        </div>
      </div>

      ${pageFooter}
    </div>

    <!-- ═══════════════════ PAGE 2 — Noted / Approved ═══════════════════ -->
    <div class="doc-page signature-page">
      ${letterhead}

      <div class="sig-grid">

        <!-- Noted -->
        ${officeSigBlock(signedRoles.OSA || '', 'Dean, Office of Student Affairs', 'Noted:')}

        <!-- Recommending Approval -->
        ${officeSigBlock(signedRoles.VPAA || '', 'Vice President, Academic Affairs', 'RECOMMENDING APPROVAL:')}

        <!-- Itemized Budget -->
        ${needsBudgetSection ? officeSigBlock(signedRoles.FINANCE || '', 'Vice President for Finance', 'Itemized Budget Reviewed by:') : ''}

        <!-- APPROVED — two sigs stacked -->
        <div class="sig-block sig-double">
          <div>
            <div class="sig-header">APPROVED:</div>
            <div style="min-height:24px;text-align:center;font-weight:700;margin-bottom:4px;">${esc(String(signedRoles.VICEPRESIDENT || '').trim().toUpperCase())}</div>
            <div class="sig-line"></div>
            <span class="sig-label">Executive Vice-President</span>
          </div>
          <div>
            <div style="min-height:24px;text-align:center;font-weight:700;margin-bottom:4px;">${esc(String(signedRoles.PRESIDENT || '').trim().toUpperCase())}</div>
            <div class="sig-line"></div>
            <span class="sig-label">President</span>
          </div>
        </div>

      </div>

      ${pageFooter}
    </div>`;
}

// ─── Preview modal ────────────────────────────────────────────────────────────

function openPreview() {
    const content = document.getElementById('previewContent');
    const modal   = document.getElementById('previewModal');
    if (content && modal) {
        content.innerHTML = buildDocHTML();
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
}

function closePreview() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
    }
}

async function downloadPDF() {
    const proposalTitle = String(window.proposalViewData?.title || g('id_title') || 'proposal').trim();
    const safeFilename = `${proposalTitle.replace(/[<>:"/\\|?*\x00-\x1F]/g, '').replace(/\s+/g, '_') || 'proposal'}.pdf`;
    const options = getPdfOptions();
    options.filename = safeFilename;

    await renderPdfDocument(container =>
        html2pdf().set(options).from(container).save()
    );
}

// ─── Init ─────────────────────────────────────────────────────────────────────

let __propasInitialized = false;

function loadProposalViewData() {
    if (window.proposalViewData) return window.proposalViewData;

    const node = document.getElementById('proposalViewData');
    if (!node) return null;

    try {
        window.proposalViewData = JSON.parse(node.textContent || 'null');
        return window.proposalViewData;
    } catch (err) {
        console.error('Failed to parse proposal preview data:', err);
        return null;
    }
}

function loadJsonScriptValue(id, fallback = null) {
    const node = document.getElementById(id);
    if (!node) return fallback;

    try {
        return JSON.parse(node.textContent || 'null');
    } catch (err) {
        console.error(`Failed to parse JSON from #${id}:`, err);
        return fallback;
    }
}

function initProPASPage() {
    if (__propasInitialized) return;
    __propasInitialized = true;

    const btnHome = document.getElementById('btnHome');
    if (btnHome) {
        btnHome.onclick = function () {
            window.location.href = this.getAttribute('data-url') || '/org-home';
        };
    }

    const btnSubmit = document.getElementById('btnSubmit');
    if (btnSubmit) {
        const defaultLabel = btnSubmit.textContent.trim();
        btnSubmit.onclick = async function () {
            if (!validateProposalForm()) return;
            if (!confirm('Submit this proposal?')) return;

            this.innerHTML = 'Uploading...';
            this.style.pointerEvents = 'none';

            try {
                const pdfBlob = await renderPdfDocument(container =>
                    html2pdf().set(getPdfOptions()).from(container).output('blob')
                );

                const formData = new FormData();
                formData.append('title',         document.getElementById('id_title').value);
                formData.append('proposal_file', pdfBlob, 'proposal.pdf');

                const supportingDoc = document.getElementById('id_supporting_document')?.files?.[0];
                if (supportingDoc) formData.append('supporting_document', supportingDoc);

                document.querySelectorAll('#proposalForm input, #proposalForm textarea, #proposalForm select')
                    .forEach(input => {
                        if (!input.name || input.type === 'file') return;
                        if ((input.type === 'checkbox' || input.type === 'radio') && !input.checked) return;
                        if (input.name !== 'title') formData.append(input.name, input.value);
                    });

                formData.append('csrf_token', document.querySelector('input[name="csrf_token"]').value);

                const response = await fetch('/create-proposal' + window.location.search, {
                    method: 'POST', body: formData
                });
                const result = await response.json();

                if (response.ok) {
                    alert(defaultLabel === 'Update Proposal'
                        ? 'Proposal updated successfully.'
                        : 'Proposal submitted successfully.');
                    window.location.href = '/org-home';
                } else {
                    throw new Error(result.error || 'Server upload failed');
                }
            } catch (err) {
                console.error(err);
                alert('Error: ' + err.message);
                this.innerHTML        = defaultLabel;
                this.style.pointerEvents = 'auto';
            }
        };
    }

    /* Budget */
    if (document.getElementById('budgetRows')) {
        const items = Array.isArray(window.initialBudgetItems) ? window.initialBudgetItems : loadJsonScriptValue('initialBudgetItems', []);
        if (items.length) {
            items.forEach(addBudgetRowWithValues);
        } else if (needsBudget()) {
            addBudgetRow();
        }
    }

    /* Approach */
    if (document.getElementById('approachRows')) {
        const items = getInitialApproachItems();
        items.length ? items.forEach(addApproachRowWithValues) : addApproachRow();
    }

    document.querySelectorAll('input[name="unsdg_goals"]').forEach(i => i.addEventListener('change', updateSdgCount));

    [['id_rationale','rationale-count'],['id_objectives','obj-count'],['id_outcome','outcome-count']]
        .forEach(([id, counterId]) => {
            const field = document.getElementById(id);
            if (field) countChars(field, counterId);
        });

    updateSdgCount();
    toggleVenueOther();
    toggleBudgetSection();
    syncApproachData();
    goTo(0);

    /* ── Office / view page: render PDF preview identical to the download ── */
    // renderPdfDocument() mounts the HTML into a real DOM node (printTarget)
    // before handing it to html2pdf — required to avoid blank output on
    // complex multi-page documents. buildDocHTML() reads window.proposalViewData
    // automatically via resolveProposalData().
    const viewer = document.getElementById('proposalViewer');
    const proposalViewData = loadProposalViewData();
    if (viewer && proposalViewData) {
        try {
            const previewHtml = buildDocHTML(proposalViewData);
            if (viewer.tagName === 'IFRAME') {
                viewer.srcdoc = previewHtml;
            } else {
                viewer.innerHTML = previewHtml;
            }
        } catch (err) {
            console.error('Proposal preview error:', err);
            const fallback = '<div style="font-family:sans-serif;padding:32px;color:#ef4444;">Failed to render preview.</div>';
            if (viewer.tagName === 'IFRAME') {
                viewer.srcdoc = fallback;
            } else {
                viewer.innerHTML = fallback;
            }
        }
    }
}

if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initProPASPage, { once: true });
} else {
    initProPASPage();
}