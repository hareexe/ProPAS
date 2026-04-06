// ─── STATE & CONFIGURATION ───────────────────────
let cur = 0;
const TOTAL = 5;

// ─── NAVIGATION LOGIC ────────────────────────────

function goTo(idx) {
    idx = Math.min(Math.max(idx, 0), TOTAL - 1);

    document.querySelectorAll('.form-section').forEach((s, i) => {
        s.classList.toggle('active', i === idx);
    });

    document.querySelectorAll('.section-nav button').forEach((b, i) => {
        b.classList.toggle('active', i === idx);
    });

    cur = idx;

    const stepIndicator = document.getElementById('currentStep');
    const progressBar = document.getElementById('progressBar');

    if (stepIndicator) stepIndicator.textContent = idx + 1;
    if (progressBar) progressBar.style.width = ((idx + 1) / TOTAL * 100) + '%';

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

async function downloadPDF() {
    const htmlString = buildDocHTML();
    const opt = {
        margin: 10,
        filename: 'proposal.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, logging: false },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    await html2pdf().set(opt).from(htmlString).save();
}

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
    const objHTML  = objLines.map((l, i) => `
        <div style="display:flex;gap:6px;margin-bottom:3px;">
            <span style="min-width:18px;">${i + 1}.</span>
            <span style="flex:1;border-bottom:1px solid #000;min-height:17px;padding:1px 2px;white-space:pre-wrap;">${esc(l)}</span>
        </div>`).join('');

    return `
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: Arial, sans-serif; background: white; }
    </style>
    <div style="background:white;max-width:794px;margin:0 auto;padding:36px 48px;font-family:Arial,sans-serif;font-size:10.5pt;color:#000;line-height:1.4;text-align:justify;">

      <!-- LETTERHEAD -->
      <div style="text-align:center;margin-bottom:8px;">
        <img src="/static/images/NWUlogo.jpg" style="height:70px;width:auto;margin-bottom:4px;" alt="NWU Logo">
        <h2 style="font-size:12pt;font-weight:700;letter-spacing:.05em;margin:4px 0 0;">NORTHWESTERN UNIVERSITY</h2>
        <p style="font-size:9pt;margin:0;">Don Mariano Marcos Avenue, Laoag City, 2900, Ilocos Norte, Philippines</p>
        <hr style="border:none;border-top:2px solid #000;margin:6px 0 0;">
      </div>

      <!-- HEADER ROW -->
      <div style="display:flex;border:1.5px solid #000;margin:12px 0 14px;">
        <div style="flex:1;text-align:center;font-weight:700;font-size:11pt;padding:6px 4px;border-right:1.5px solid #000;letter-spacing:.1em;">PROJECT PROPOSAL</div>
        <div style="padding:6px 12px;font-weight:700;font-size:11pt;display:flex;align-items:center;white-space:nowrap;">OSA-F05A</div>
      </div>

      <!-- FIELDS -->
      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">I.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Project Proposal Title:</strong>
          <div style="border-bottom:1px solid #000;min-height:18px;padding:1px 3px;width:100%;font-size:10.5pt;">${esc(g('id_title'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">II.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Sponsor / Organization:</strong>
          <div style="border-bottom:1px solid #000;min-height:18px;padding:1px 3px;width:100%;font-size:10.5pt;">${esc(g('id_sponsor'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">III.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Date &amp; Venue:</strong>
          <div style="border-bottom:1px solid #000;min-height:18px;padding:1px 3px;width:100%;font-size:10.5pt;">${esc(g('id_date_venue'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">IV.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Target Participants:</strong>
          <div style="border-bottom:1px solid #000;min-height:18px;padding:1px 3px;width:100%;font-size:10.5pt;">${esc(g('id_participation'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">V.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Background / Rationale:</strong>
          <div style="text-align:justify;white-space:pre-wrap;min-height:60px;padding:1px 3px;display:block;width:100%;">${esc(g('id_rationale'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">VI.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Objectives:</strong>
          ${objHTML || '<div style="border-bottom:1px solid #000;min-height:18px;">&nbsp;</div>'}
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">VII.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">UNSDGs:</strong>
          <div style="text-align:justify;white-space:pre-wrap;padding:1px 3px;display:block;width:100%;">${esc(g('id_unsdg'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">VIII.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Approach / Process:</strong>
          <div style="text-align:justify;white-space:pre-wrap;min-height:60px;padding:1px 3px;display:block;width:100%;">${esc(g('id_approach'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">IX.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Expected Outcomes:</strong>
          <div style="text-align:justify;white-space:pre-wrap;min-height:40px;padding:1px 3px;display:block;width:100%;">${esc(g('id_outcome'))}</div>
        </div>
      </div>

      <div style="display:flex;gap:6px;margin-bottom:10px;align-items:flex-start;">
        <span style="font-weight:700;min-width:42px;padding-top:1px;">X.</span>
        <div style="flex:1;">
          <strong style="text-align:left;display:block;">Budget</strong>
          <div style="margin:8px 0 4px;">
            <strong>a. Proposed Budget:</strong>
            <span style="border-bottom:1px solid #000;width:auto;display:inline-block;min-width:120px;padding:1px 3px;">₱ ${fmt(g('id_budget'))}</span>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:10pt;">
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
                <td style="border:1px solid #000;padding:4px 8px;text-align:right;font-weight:700;">₱ ${fmt(grandTotal)}</td>
              </tr>
            </tfoot>
          </table>
          <div style="margin-top:8px;">
            <strong>c. Source of Funding:</strong>
            <span style="border-bottom:1px solid #000;display:inline-block;min-width:200px;padding:1px 3px;">${esc(g('id_funding_source'))}</span>
          </div>
        </div>
      </div>

      <!-- APPROVAL SIGNATURES -->
      <div style="margin-top:40px;">
        <p style="font-weight:700;margin-bottom:20px;">APPROVAL SIGNATURES</p>
        <div style="display:flex;gap:16px;">
          <div style="flex:1;">
            <div style="margin-bottom:28px;">
              <div style="min-height:20px;text-align:center;width:210px;">${esc(g('id_sig_president'))}</div>
              <div style="border-top:1px solid #000;margin-bottom:4px;width:210px;"></div>
              <span style="font-style:italic;font-weight:700;font-size:10pt;text-align:center;width:210px;display:block;">Org President</span>
            </div>
            <div style="margin-bottom:28px;">
              <div style="min-height:20px;text-align:center;width:210px;">${esc(g('id_sig_adviser'))}</div>
              <div style="border-top:1px solid #000;margin-bottom:4px;width:210px;"></div>
              <span style="font-style:italic;font-weight:700;font-size:10pt;text-align:center;width:210px;display:block;">Org Adviser</span>
            </div>
          </div>
          <div style="flex:1;display:flex;flex-direction:column;align-items:flex-end;">
            <div style="margin-bottom:28px;text-align:right;">
              <div style="min-height:20px;text-align:center;width:210px;">${esc(g('id_sig_dept'))}</div>
              <div style="border-top:1px solid #000;margin-bottom:4px;width:210px;"></div>
              <span style="font-style:italic;font-weight:700;font-size:10pt;text-align:center;width:210px;display:block;">Dept Head</span>
            </div>
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
                // A. Generate PDF from HTML string (no DOM element needed)
                const opt = {
                    margin: 10,
                    filename: 'proposal.pdf',
                    image: { type: 'jpeg', quality: 0.98 },
                    html2canvas: { scale: 2, useCORS: true, logging: false },
                    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
                };

                const pdfBlob = await html2pdf().set(opt).from(buildDocHTML()).output('blob');

                // B. Prepare FormData (Hybrid)
                const formData = new FormData();
                formData.append('title', titleEl.value);
                formData.append('proposal_file', pdfBlob, 'proposal.pdf');

                document.querySelectorAll('#proposalForm input, #proposalForm textarea').forEach(input => {
                    if (input.name && input.type !== 'file') {
                        formData.append(input.name, input.value);
                    }
                });

                const csrfToken = document.querySelector('input[name="csrf_token"]').value;
                formData.append('csrf_token', csrfToken);

                // C. POST to Server
                const response = await fetch('/create-proposal' + window.location.search, {
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