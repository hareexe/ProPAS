/**
 * ProPAS - Project Proposal Automation System
 * Multi-step Form, Document Generation & Cloud Submission Logic
 */

// ─── STATE & CONFIGURATION ───────────────────────
let cur = 0;
const TOTAL = 5;

// ─── NAVIGATION LOGIC ────────────────────────────

function goTo(idx) {
    // Clamp index between 0 and TOTAL-1
    idx = Math.min(Math.max(idx, 0), TOTAL - 1);

    // Toggle Section Visibility
    document.querySelectorAll('.form-section').forEach((s, i) => {
        s.classList.toggle('active', i === idx);
    });

    // Toggle Nav Button Active State
    document.querySelectorAll('.section-nav button').forEach((b, i) => {
        b.classList.toggle('active', i === idx);
    });

    cur = idx;

    // Update Progress Indicators
    const stepIndicator = document.getElementById('currentStep');
    const progressBar = document.getElementById('progressBar');

    if (stepIndicator) stepIndicator.textContent = idx + 1;
    if (progressBar) progressBar.style.width = ((idx + 1) / TOTAL * 100) + '%';

    // UI Element Visibility Logic
    const isFirst = (idx === 0);
    const isLast  = (idx === TOTAL - 1);

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
    goTo(cur + dir);
}

// ─── BUDGET TABLE LOGIC ──────────────────────────

function addBudgetRow() {
    const tbody = document.getElementById('budgetRows');
    if (!tbody) return;

    const rowCount = tbody.rows.length + 1;
    const row = document.createElement('tr');

    row.innerHTML = `
        <td>${rowCount}</td>
        <td><input type="text" class="bud-desc bud-input" placeholder="Item name"></td>
        <td><input type="number" class="bud-qty bud-input" value="1" min="0" oninput="calcTotal()"></td>
        <td><input type="number" class="bud-unit bud-input" value="0" min="0" step="0.01" oninput="calcTotal()"></td>
        <td class="row-total">₱ 0.00</td>
        <td><button type="button" class="btn-danger-small" onclick="this.closest('tr').remove(); calcTotal(); renumberRows();">✕</button></td>
    `;
    tbody.appendChild(row);
    calcTotal();
}

function renumberRows() {
    document.querySelectorAll('#budgetRows tr').forEach((row, i) => {
        row.cells[0].textContent = i + 1;
    });
}

function calcTotal() {
    let grandTotal = 0;
    document.querySelectorAll('#budgetRows tr').forEach(row => {
        const qty  = parseFloat(row.querySelector('.bud-qty')?.value)  || 0;
        const unit = parseFloat(row.querySelector('.bud-unit')?.value) || 0;
        const total = qty * unit;
        grandTotal += total;

        const rowTotalDisplay = row.querySelector('.row-total');
        if (rowTotalDisplay) {
            rowTotalDisplay.textContent = '₱ ' + total.toLocaleString('en-PH', { minimumFractionDigits: 2 });
        }
    });

    const totalDisplay      = document.getElementById('budgetTotal');
    const hiddenBudgetInput = document.getElementById('id_budget');

    if (totalDisplay)      totalDisplay.textContent = '₱ ' + grandTotal.toLocaleString('en-PH', { minimumFractionDigits: 2 });
    if (hiddenBudgetInput) hiddenBudgetInput.value  = grandTotal;
}

// ─── HELPERS & CHARACTER COUNTS ──────────────────

function countChars(el, id) {
    const counter = document.getElementById(id);
    if (counter) {
        counter.textContent = `${el.value.length} / ${el.maxLength}`;
    }
}

function updateProgress() {
    const n = ['id_title', 'id_sponsor'].filter(id => {
        const el = document.getElementById(id);
        return el && el.value.trim() !== '';
    }).length;

    if (cur === 0) {
        const progressBar = document.getElementById('progressBar');
        if (progressBar) progressBar.style.width = (20 + n * 8) + '%';
    }
}

// ─── DOCUMENT PREVIEW & EXPORT ───────────────────

const g   = id => (document.getElementById(id) || {}).value || '';
const esc = s  => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const fmt = n  => Number(n || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function buildDocHTML() {
    let budgetRowsHTML = '';
    let grandTotal = 0;
    document.querySelectorAll('#budgetRows tr').forEach((row, i) => {
        const desc  = row.querySelector('.bud-desc')?.value  || '';
        const qty   = parseFloat(row.querySelector('.bud-qty')?.value)  || 0;
        const unit  = parseFloat(row.querySelector('.bud-unit')?.value) || 0;
        const total = qty * unit;
        grandTotal += total;
        budgetRowsHTML += `
            <tr>
                <td style="border:1px solid #000;padding:4px 8px;text-align:center;">${i + 1}</td>
                <td style="border:1px solid #000;padding:4px 8px;">${esc(desc)}</td>
                <td style="border:1px solid #000;padding:4px 8px;text-align:center;">${qty}</td>
                <td style="border:1px solid #000;padding:4px 8px;text-align:right;">₱ ${fmt(unit)}</td>
                <td style="border:1px solid #000;padding:4px 8px;text-align:right;">₱ ${fmt(total)}</td>
            </tr>`;
    });

    const objLines = g('id_objectives').split('\n').filter(l => l.trim());
    const objHTML  = objLines.map((l, i) => `<div class="obj-row"><span class="obj-n">${i + 1}.</span><span class="obj-v">${esc(l)}</span></div>`).join('');

    return `
    <div class="doc-wrap">
      <div class="doc-page">
        <div class="lh">
          <h2>NORTHWESTERN UNIVERSITY</h2>
          <p>Laoag City, Ilocos Norte</p>
          <p>Office of Student Affairs</p>
          <hr class="lh-rule">
        </div>
        <div class="doc-hdr-row">
          <div class="doc-hdr-title">PROJECT PROPOSAL</div>
          <div class="doc-hdr-code">OSA-F05A</div>
        </div>
        <div class="di"><span class="di-n">I.</span><div class="di-b"><strong>Project Proposal Title:</strong><div class="uline">${esc(g('id_title'))}</div></div></div>
        <div class="di"><span class="di-n">II.</span><div class="di-b"><strong>Sponsor / Organization:</strong><div class="uline">${esc(g('id_sponsor'))}</div></div></div>
        <div class="di"><span class="di-n">III.</span><div class="di-b"><strong>Date & Venue:</strong><div class="uline">${esc(g('id_date_venue'))}</div></div></div>
        <div class="di"><span class="di-n">IV.</span><div class="di-b"><strong>Target Participants:</strong><div class="uline">${esc(g('id_participation'))}</div></div></div>
        <div class="di"><span class="di-n">V.</span><div class="di-b"><strong>Background / Rationale:</strong><div class="uline" style="white-space:pre-wrap;min-height:60px;">${esc(g('id_rationale'))}</div></div></div>
        <div class="di"><span class="di-n">VI.</span><div class="di-b"><strong>Objectives:</strong>${objHTML || '<div class="uline">&nbsp;</div>'}</div></div>
        <div class="di"><span class="di-n">VII.</span><div class="di-b"><strong>UNSDGs:</strong><div class="uline" style="white-space:pre-wrap;">${esc(g('id_unsdg'))}</div></div></div>
        <div class="di"><span class="di-n">VIII.</span><div class="di-b"><strong>Approach / Process:</strong><div class="uline" style="white-space:pre-wrap;min-height:60px;">${esc(g('id_approach'))}</div></div></div>
        <div class="di"><span class="di-n">IX.</span><div class="di-b"><strong>Expected Outcomes:</strong><div class="uline" style="white-space:pre-wrap;min-height:40px;">${esc(g('id_outcome'))}</div></div></div>
        <div class="di"><span class="di-n">X.</span><div class="di-b"><strong>Budget</strong>
          <div style="margin:8px 0 4px;"><strong>a. Proposed Budget:</strong> <span class="uline" style="width:auto;display:inline-block;min-width:120px;">₱ ${fmt(g('id_budget'))}</span></div>
          <table style="width:100%;border-collapse:collapse;font-size:10pt;">
            <thead><tr><th style="border:1px solid #000;">#</th><th style="border:1px solid #000;">Item</th><th style="border:1px solid #000;">Qty</th><th style="border:1px solid #000;">Unit</th><th style="border:1px solid #000;">Amount</th></tr></thead>
            <tbody>${budgetRowsHTML}</tbody>
            <tfoot><tr><td colspan="4" style="border:1px solid #000;text-align:right;">TOTAL</td><td style="border:1px solid #000;text-align:right;">₱ ${fmt(grandTotal)}</td></tr></tfoot>
          </table>
          <div style="margin-top:8px;"><strong>c. Source of Funding:</strong> <span class="uline">${esc(g('id_funding_source'))}</span></div>
        </div></div>
      </div>
      <div class="doc-page">
        <p style="font-weight:700;">APPROVAL SIGNATURES</p>
        <div class="p2-two-col">
          <div class="p2-left">
            <div class="p2-sig-blk"><div class="p2-sig-ln"></div><span class="p2-sig-lbl">President</span><div style="text-align:center;">${esc(g('id_sig_president'))}</div></div>
            <div class="p2-sig-blk"><div class="p2-sig-ln"></div><span class="p2-sig-lbl">Adviser</span><div style="text-align:center;">${esc(g('id_sig_adviser'))}</div></div>
          </div>
          <div class="p2-right">
            <div class="p2-sig-blk-r"><div class="p2-sig-ln"></div><span class="p2-sig-lbl">Dept Head</span><div style="text-align:center;">${esc(g('id_sig_dept'))}</div></div>
            <div class="p2-sig-blk-r"><div class="p2-sig-ln"></div><span class="p2-sig-lbl">Dean</span><div style="text-align:center;">${esc(g('id_sig_dean'))}</div></div>
          </div>
        </div>
      </div>
    </div>`;
}

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

// ─── INITIALIZATION & EVENT LISTENERS ────────────

window.onload = () => {
    // 1. Home button
    const btnHome = document.getElementById('btnHome');
    if (btnHome) {
        btnHome.onclick = function () {
            window.location.href = this.getAttribute('data-url') || '/org-home';
        };
    }

    // 2. Submit button (PDF Generation + Hybrid JSON Upload)
    const btnSubmit = document.getElementById('btnSubmit');
    if (btnSubmit) {
        btnSubmit.onclick = async function () {
            const titleEl = document.getElementById('id_title');
            if (!titleEl || !titleEl.value.trim()) {
                alert('Please enter a Project Title.');
                goTo(0);
                return;
            }

            if (!confirm('Submit this proposal?')) return;

            this.innerHTML = 'Uploading...';
            this.style.pointerEvents = 'none';

            try {
                // A. Create PDF Blob
                const offscreenTemplate = document.createElement('div');
                offscreenTemplate.innerHTML = buildDocHTML(); 
                
                const opt = {
                    margin: 10,
                    filename: 'proposal.pdf',
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: { scale: 2, useCORS: true },
                    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
                };

                const pdfBlob = await html2pdf().set(opt).from(offscreenTemplate).output('blob');

                // B. Prepare FormData (Hybrid)
                const formData = new FormData();
                formData.append('title', titleEl.value);
                formData.append('proposal_file', pdfBlob, 'proposal.pdf');

                // Auto-append all other form inputs for the JSON blob
                document.querySelectorAll('#proposalForm input, #proposalForm textarea').forEach(input => {
                    if (input.name && input.type !== 'file') {
                        formData.append(input.name, input.value);
                    }
                });

                const csrfToken = document.querySelector('input[name="csrf_token"]').value;
                formData.append('csrf_token', csrfToken);

                // C. POST to Server
                const response = await fetch('/create-proposal', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    window.location.href = '/org-home';
                } else {
                    throw new Error(result.error || 'Server upload failed');
                }

            } catch (error) {
                console.error(error);
                alert('Error: ' + error.message);
                this.innerHTML = 'Submit Proposal';
                this.style.pointerEvents = 'auto';
            }
        };
    }

    if (document.getElementById('budgetRows')) addBudgetRow();
    goTo(0);
};