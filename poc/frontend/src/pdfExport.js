/**
 * PDF export module — pure, framework-agnostic functions that build jsPDF
 * documents from plain data. Kept separate from App.jsx so new report
 * sections/tabs can be added here without touching component code.
 *
 * Vector text + tables (not html2canvas screenshots), so output stays
 * crisp, paginates correctly, and text remains selectable/searchable.
 */
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const PAGE_MARGIN = 40;
const CONTENT_BOTTOM = 780; // A4 pt height (~842) minus footer clearance

const COLORS = {
  navy: [15, 23, 42],
  blue: [37, 99, 235],
  slate: [71, 85, 105],
  green: [21, 128, 61],
  red: [185, 28, 28],
  amber: [180, 83, 9],
  gray: [148, 163, 184],
};

const AGENT_COLORS = {
  Infrastructure: [37, 99, 235],
  Application: [124, 58, 237],
  Business: [5, 150, 105],
  Security: [220, 38, 38],
  Chair: [180, 83, 9],
};

const AGENT_LABELS = {
  Infrastructure: 'Infrastructure Specialist',
  Application: 'Application Specialist',
  Business: 'Business & Service Owner',
  Security: 'Security & Compliance Officer',
  Chair: 'Change Manager (Chair)',
};

const SEVERITY_COLORS = {
  'Must-fix': [185, 28, 28],
  'Should-fix': [180, 83, 9],
  'Nice-to-have': [37, 99, 235],
};

const DECISION_COLORS = {
  'Approved': COLORS.green,
  'Rejected': COLORS.red,
  'Conditional Approval': COLORS.amber,
};

// ---- low-level helpers ----------------------------------------------------

function stripMarkdown(text) {
  if (!text) return '';
  return String(text)
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`(.*?)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^[-*]\s+/gm, '• ')
    .trim();
}

function timestamp() {
  return new Date().toISOString().slice(0, 10); // YYYY-MM-DD
}

function sanitizeFilename(name) {
  return String(name || 'report').replace(/[^a-zA-Z0-9_-]+/g, '_');
}

function newDoc() {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  doc.setFont('helvetica', 'normal');
  return doc;
}

function pageWidth(doc) {
  return doc.internal.pageSize.getWidth();
}

function pageHeight(doc) {
  return doc.internal.pageSize.getHeight();
}

/** Colored title banner at the top of a report; returns the y cursor below it. */
function drawBanner(doc, title, subtitle) {
  const w = pageWidth(doc);
  doc.setFillColor(...COLORS.navy);
  doc.rect(0, 0, w, 70, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text(String(title || ''), PAGE_MARGIN, 32);
  if (subtitle) {
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(200, 210, 225);
    doc.text(String(subtitle), PAGE_MARGIN, 50);
  }
  doc.setTextColor(0, 0, 0);
  return 92;
}

/** Starts a new page if `needed` pt of vertical space isn't left; returns the (possibly reset) y cursor. */
function ensureSpace(doc, y, needed) {
  if (y + needed > CONTENT_BOTTOM) {
    doc.addPage();
    return PAGE_MARGIN + 20;
  }
  return y;
}

function addFootersToAllPages(doc, reportLabel) {
  const total = doc.internal.getNumberOfPages();
  const generatedAt = new Date().toLocaleString();
  for (let i = 1; i <= total; i++) {
    doc.setPage(i);
    const w = pageWidth(doc);
    const h = pageHeight(doc);
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text(`${reportLabel} — Generated ${generatedAt}`, PAGE_MARGIN, h - 20);
    doc.text(`Page ${i} of ${total}`, w - PAGE_MARGIN - 60, h - 20);
  }
}

// ---- reusable content blocks -----------------------------------------------

/** Two-column key/value grid, e.g. RFC metadata. */
function renderMetaBlock(doc, y, rows) {
  const visible = rows.filter(([, value]) => value !== undefined && value !== null && value !== '');
  doc.setFontSize(9);
  visible.forEach(([label, value], i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = PAGE_MARGIN + col * 260;
    const yy = y + row * 32;
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...COLORS.slate);
    doc.text(String(label).toUpperCase(), x, yy);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(20, 20, 20);
    doc.text(String(value), x, yy + 14);
  });
  const rowCount = Math.ceil(visible.length / 2);
  return y + rowCount * 32 + 14;
}

/** A heading + wrapped paragraph, with automatic pagination. */
function renderParagraphSection(doc, y, heading, bodyText, headingColor = COLORS.navy) {
  y = ensureSpace(doc, y, 40);
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...headingColor);
  doc.text(heading, PAGE_MARGIN, y);
  y += 18;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(40, 40, 40);
  const clean = stripMarkdown(bodyText) || 'Not provided';
  const lines = doc.splitTextToSize(clean, pageWidth(doc) - PAGE_MARGIN * 2);
  for (const line of lines) {
    y = ensureSpace(doc, y, 16);
    doc.text(line, PAGE_MARGIN, y);
    y += 14;
  }
  return y + 12;
}

function parseAgentLogForPdf(log) {
  const text = String(log || '').trim();
  const match = text.match(/^(?:🔍|📋)\s*([^:]+):\s*([\s\S]*)$/);
  const rawName = match ? match[1].toUpperCase() : '';
  const body = match ? match[2].trim() : text;

  let key = 'Chair';
  if (rawName.includes('INFRASTRUCTURE')) key = 'Infrastructure';
  else if (rawName.includes('APPLICATION')) key = 'Application';
  else if (rawName.includes('BUSINESS')) key = 'Business';
  else if (rawName.includes('SECURITY')) key = 'Security';

  return {
    label: AGENT_LABELS[key] + (rawName.includes('SYNTHESIS') ? ' — Synthesis' : ''),
    color: AGENT_COLORS[key],
    body: stripMarkdown(body),
  };
}

function renderDeliberationSection(doc, y, agentLogs) {
  y = ensureSpace(doc, y, 30);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.navy);
  doc.text('CAB Deliberation Transcript', PAGE_MARGIN, y);
  y += 22;

  const logs = (agentLogs || []).filter(
    (l) => typeof l === 'string' && !l.includes('REQUIRED CHANGES & RECOMMENDATIONS')
  );

  for (const log of logs) {
    const { label, color, body } = parseAgentLogForPdf(log);
    if (!body) continue;

    y = ensureSpace(doc, y, 40);
    doc.setFillColor(...color);
    doc.rect(PAGE_MARGIN, y - 10, 3, 14, 'F');
    doc.setFontSize(10.5);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...color);
    doc.text(label, PAGE_MARGIN + 10, y);
    y += 14;

    doc.setFontSize(9.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(30, 30, 30);
    const lines = doc.splitTextToSize(body, pageWidth(doc) - PAGE_MARGIN * 2 - 10);
    for (const line of lines) {
      y = ensureSpace(doc, y, 14);
      doc.text(line, PAGE_MARGIN + 10, y);
      y += 13;
    }
    y += 14;
  }
  return y;
}

function renderDecisionSection(doc, y, decision, reasoning) {
  y = ensureSpace(doc, y, 30);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.navy);
  doc.text('Final Decision', PAGE_MARGIN, y);
  y += 24;

  const label = decision || 'Pending Review';
  const dColor = DECISION_COLORS[label] || COLORS.slate;
  const w = doc.getTextWidth(label) + 28;
  doc.setFillColor(...dColor);
  doc.roundedRect(PAGE_MARGIN, y - 14, w, 22, 6, 6, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text(label, PAGE_MARGIN + 14, y + 1);
  y += 32;

  return renderParagraphSection(doc, y, 'Reasoning', reasoning);
}

function renderFlagsSection(doc, y, flags) {
  y = ensureSpace(doc, y, 30);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.navy);
  doc.text('Required Changes & Recommendations', PAGE_MARGIN, y);
  y += 20;

  const list = Array.isArray(flags) ? flags : [];
  if (list.length === 0) {
    doc.setFontSize(10);
    doc.setFont('helvetica', 'italic');
    doc.setTextColor(120, 120, 120);
    doc.text('No required changes flagged.', PAGE_MARGIN, y);
    return y + 20;
  }

  autoTable(doc, {
    startY: y,
    margin: { left: PAGE_MARGIN, right: PAGE_MARGIN },
    head: [['Severity', 'Category', 'Affected Element', 'Recommendation', 'Raised By']],
    body: list.map((f) => [f.severity, f.category, f.affected_element, f.recommendation, f.raised_by]),
    styles: { fontSize: 8.5, cellPadding: 6, overflow: 'linebreak', valign: 'top' },
    headStyles: { fillColor: COLORS.navy, textColor: 255 },
    columnStyles: {
      0: { cellWidth: 58 },
      1: { cellWidth: 72 },
      2: { cellWidth: 88 },
      3: { cellWidth: 'auto' },
      4: { cellWidth: 88 },
    },
    didParseCell: (data) => {
      if (data.section === 'body' && data.column.index === 0) {
        const c = SEVERITY_COLORS[data.cell.raw];
        if (c) {
          data.cell.styles.textColor = c;
          data.cell.styles.fontStyle = 'bold';
        }
      }
    },
  });
  return doc.lastAutoTable.finalY + 20;
}

function renderRfcTable(doc, y, rfcs) {
  autoTable(doc, {
    startY: y,
    margin: { left: PAGE_MARGIN, right: PAGE_MARGIN },
    head: [['RFC Number', 'Title', 'Type', 'Status', 'Created']],
    body: rfcs.map((r) => [
      r.rfc_number,
      r.title,
      r.change_type,
      r.status,
      new Date(r.created_at).toLocaleDateString(),
    ]),
    styles: { fontSize: 8.5, cellPadding: 6, overflow: 'linebreak' },
    headStyles: { fillColor: COLORS.navy, textColor: 255 },
  });
  return doc.lastAutoTable.finalY + 24;
}

function renderBarChart(doc, y, title, data) {
  if (data.length === 0) return y;
  y = ensureSpace(doc, y, 30 + data.length * 22);
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.navy);
  doc.text(title, PAGE_MARGIN, y);
  y += 18;

  const maxVal = Math.max(1, ...data.map((d) => d.value));
  const chartW = pageWidth(doc) - PAGE_MARGIN * 2 - 150;
  data.forEach((d) => {
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(60, 60, 60);
    doc.text(String(d.label).slice(0, 28), PAGE_MARGIN, y + 8);
    const barW = Math.max(2, (d.value / maxVal) * chartW);
    doc.setFillColor(...COLORS.blue);
    doc.rect(PAGE_MARGIN + 150, y, barW, 12, 'F');
    doc.setTextColor(30, 30, 30);
    doc.text(String(d.value), PAGE_MARGIN + 150 + barW + 6, y + 9);
    y += 20;
  });
  return y + 14;
}

function countBy(items, key) {
  const counts = {};
  items.forEach((item) => {
    counts[item[key]] = (counts[item[key]] || 0) + 1;
  });
  return Object.entries(counts)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);
}

// ---- public API -------------------------------------------------------

/**
 * Registry of CAB result sections. Adding a new CAB result tab later means
 * adding one entry here (hasData + render) — no other export logic changes.
 */
export const CAB_SECTIONS = {
  deliberation: {
    label: 'Deliberation',
    hasData: (d) => Array.isArray(d.agentLogs) && d.agentLogs.length > 0,
    render: (doc, y, d) => renderDeliberationSection(doc, y, d.agentLogs),
  },
  decision: {
    label: 'Decision',
    hasData: (d) => Boolean(d.decision),
    render: (doc, y, d) => renderDecisionSection(doc, y, d.decision, d.reasoning),
  },
  flags: {
    label: 'RequiredChanges',
    hasData: (d) => Boolean(d.decision), // tab is shown once reviewed, even with 0 flags
    render: (doc, y, d) => renderFlagsSection(doc, y, d.flags),
  },
};

/** Download PDF for exactly one CAB result tab. */
export function downloadCabTabPdf(kind, rfc, cabData) {
  const section = CAB_SECTIONS[kind];
  if (!section) throw new Error(`Unknown CAB section: ${kind}`);

  const doc = newDoc();
  const y = drawBanner(doc, rfc.rfc_number, rfc.title) + 16;
  section.render(doc, y, cabData);

  addFootersToAllPages(doc, `${rfc.rfc_number} — ${section.label}`);
  doc.save(`${sanitizeFilename(rfc.rfc_number)}_${section.label}_${timestamp()}.pdf`);
}

/**
 * Download all CAB result tabs combined into one report. Skips (and reports
 * back) any section whose data isn't available yet instead of failing.
 */
export function downloadCabAllPdf(rfc, cabData) {
  const doc = newDoc();
  let y = drawBanner(doc, rfc.rfc_number, `${rfc.title} — Full CAB Report`) + 16;

  const skipped = [];
  let rendered = 0;

  for (const kind of Object.keys(CAB_SECTIONS)) {
    const section = CAB_SECTIONS[kind];
    if (!section.hasData(cabData)) {
      skipped.push(section.label);
      continue;
    }
    if (rendered > 0) {
      doc.addPage();
      y = PAGE_MARGIN + 20;
    }
    y = section.render(doc, y, cabData);
    rendered += 1;
  }

  if (rendered === 0) {
    doc.setFontSize(12);
    doc.setTextColor(120, 120, 120);
    doc.text('No CAB results available yet for this RFC.', PAGE_MARGIN, y);
  }

  addFootersToAllPages(doc, `${rfc.rfc_number} — Full CAB Report`);
  doc.save(`${sanitizeFilename(rfc.rfc_number)}_CAB_Report_${timestamp()}.pdf`);
  return skipped;
}

/** Download the RFC's own fields plus all available CAB sections in one report. */
export function downloadFullRfcReportPdf(rfc, cabData) {
  const doc = newDoc();
  let y = drawBanner(doc, rfc.rfc_number, rfc.title) + 10;

  y = renderMetaBlock(doc, y, [
    ['Type', rfc.change_type],
    ['Status', rfc.status],
    ['Impact', rfc.impact],
    ['Priority', rfc.priority],
    ['Risk Level', rfc.risk_level ? `${rfc.risk_level} / 5` : null],
    ['Requestor', rfc.requestor_name],
  ]);

  y = renderParagraphSection(doc, y, 'Description', rfc.description);
  if (rfc.business_justification) {
    y = renderParagraphSection(doc, y, 'Business Justification', rfc.business_justification);
  }
  if (rfc.implementation_plan) {
    y = renderParagraphSection(doc, y, 'Implementation Plan', rfc.implementation_plan);
  }
  if (rfc.test_cases) {
    y = renderParagraphSection(doc, y, 'Test Cases & Results', rfc.test_cases);
  }
  if (rfc.back_out_plan) {
    y = renderParagraphSection(doc, y, 'Rollback / Back-Out Plan', rfc.back_out_plan);
  }

  const skipped = [];
  for (const kind of Object.keys(CAB_SECTIONS)) {
    const section = CAB_SECTIONS[kind];
    if (!section.hasData(cabData)) {
      skipped.push(section.label);
      continue;
    }
    doc.addPage();
    y = PAGE_MARGIN + 20;
    y = section.render(doc, y, cabData);
  }

  addFootersToAllPages(doc, `${rfc.rfc_number} — Full Report`);
  doc.save(`${sanitizeFilename(rfc.rfc_number)}_Full_Report_${timestamp()}.pdf`);
  return skipped;
}

/** Download the RFC register (table + analytics charts) as one PDF. */
export function downloadRegisterPdf(rfcs) {
  const doc = newDoc();
  let y =
    drawBanner(doc, 'RFC Register', `${rfcs.length} change request${rfcs.length !== 1 ? 's' : ''}`) + 16;

  y = renderRfcTable(doc, y, rfcs);

  doc.addPage();
  y = PAGE_MARGIN + 20;
  y = renderBarChart(doc, y, 'RFCs by Change Type', countBy(rfcs, 'change_type'));
  renderBarChart(doc, y, 'RFCs by Status', countBy(rfcs, 'status'));

  addFootersToAllPages(doc, 'RFC Register');
  doc.save(`RFC_Register_${timestamp()}.pdf`);
}
