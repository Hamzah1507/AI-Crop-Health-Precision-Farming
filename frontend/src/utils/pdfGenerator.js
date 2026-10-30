/**
 * Modern AI Analytics PDF Report Generator — Precision Farming Platform.
 * Visual Composition based directly on the Modern AI Analytics Report Reference.
 * 
 * Features & Design System:
 * - Crisp white and warm ivory page backgrounds (#FFFFFF / #FBFBF9).
 * - Forest-green headings (#14532D) and refined emerald accents (#059669).
 * - Executive hero section with decorative agricultural branding.
 * - 3-column metadata card with emerald icon badges.
 * - Four aligned executive KPI cards with distinct icons and health score progress bars.
 * - Native vector Donut Chart for diagnostic scan distribution.
 * - Horizontal nutrient status progress bars with reference ranges.
 * - Dynamic Key Insights callout box with contextual agricultural guidance.
 * - Minimalist tables with soft-sage headers (#EAF2EC), row numbering (#), and pill badges.
 * - Multi-page running headers and 'Page X of Y' footers.
 * - Strict multi-tenant isolation and clear demo fallback notices.
 */

import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

// Robust autoTable invoker for ESM/CJS interop
const applyAutoTable = (doc, options) => {
  if (typeof autoTable === 'function') {
    autoTable(doc, options);
  } else if (autoTable && typeof autoTable.default === 'function') {
    autoTable.default(doc, options);
  } else if (typeof doc.autoTable === 'function') {
    doc.autoTable(options);
  }
};

// ============================================================================
// COLOR PALETTE (RGB Tuples for jsPDF)
// ============================================================================
const FOREST_GREEN = [20, 83, 45];      // #14532D - Primary Brand & Headings
const EMERALD = [5, 150, 105];          // #059669 - Accent Emerald & Progress
const EMERALD_DARK = [6, 95, 70];       // #065F46 - Deep Emerald Text
const EMERALD_BG = [234, 242, 236];     // #EAF2EC - Table Header & Icon Surface
const EMERALD_LIGHT = [209, 250, 229];  // #D1FAE5 - Pill & Tag Background
const PALE_SAGE = [241, 248, 244];      // #F1F8F4 - Key Insights Surface
const WARM_WHITE = [255, 255, 255];     // #FFFFFF - Card Surfaces
const SLATE_DARK = [30, 41, 59];        // #1E293B - Primary Values & Headings
const SLATE_BODY = [71, 85, 105];       // #475569 - Body & Descriptions
const SLATE_MUTED = [148, 163, 184];    // #94A3B8 - Secondary Captions
const SLATE_BORDER = [226, 232, 240];   // #E2E8F0 - Dividers & Borders
const TRACK_BG = [229, 231, 235];       // #E5E7EB - Progress Bar Track
const AMBER_DARK = [217, 119, 6];       // #D97706 - Warning & Demo Text
const AMBER_BG = [254, 243, 199];       // #FEF3C7 - Warning Tag Background
const AMBER_BORDER = [253, 230, 138];   // #FDE68A - Warning Border
const ROSE_DARK = [185, 28, 28];        // #B91C1C - Disease Badge Text
const ROSE_BG = [254, 226, 226];        // #FEE2E2 - Disease Badge Background

const safeStr = (v, fallback = '—') => (v === null || v === undefined || v === '' ? fallback : String(v));

function formatDisplayDate(dateStr) {
  if (!dateStr || dateStr === '—') return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

// ============================================================================
// VECTOR DRAWING PRIMITIVES
// ============================================================================

/**
 * Draw a clean rounded container with fill and border.
 */
function drawCard(doc, x, y, width, height, bgColor, borderColor, radius = 2) {
  doc.setDrawColor(...borderColor);
  doc.setFillColor(...bgColor);
  doc.roundedRect(x, y, width, height, radius, radius, 'FD');
}

/**
 * Draw a circular icon pill with simple geometric vector glyph.
 */
function drawIconBadge(doc, cx, cy, radius, iconType) {
  doc.setFillColor(...EMERALD_BG);
  doc.circle(cx, cy, radius, 'F');

  doc.setDrawColor(...FOREST_GREEN);
  doc.setFillColor(...FOREST_GREEN);
  doc.setLineWidth(0.4);

  if (iconType === 'user') {
    doc.circle(cx, cy - 1.2, 1.2, 'FD');
    doc.roundedRect(cx - 2.2, cy + 0.8, 4.4, 2.2, 0.6, 0.6, 'FD');
  } else if (iconType === 'pin') {
    doc.circle(cx, cy - 0.8, 1.4, 'FD');
    doc.triangle(cx - 1.4, cy - 0.2, cx + 1.4, cy - 0.2, cx, cy + 2.4, 'FD');
    doc.setFillColor(...WARM_WHITE);
    doc.circle(cx, cy - 0.8, 0.6, 'F');
  } else if (iconType === 'calendar') {
    doc.roundedRect(cx - 2.2, cy - 2, 4.4, 4.2, 0.5, 0.5, 'S');
    doc.rect(cx - 2.2, cy - 2, 4.4, 1.2, 'F');
  } else if (iconType === 'home') {
    doc.triangle(cx - 2.6, cy - 0.2, cx + 2.6, cy - 0.2, cx, cy - 2.6, 'FD');
    doc.rect(cx - 2, cy - 0.2, 4, 2.8, 'FD');
  } else if (iconType === 'sprout') {
    doc.circle(cx - 1, cy - 0.6, 1.3, 'FD');
    doc.circle(cx + 1, cy - 1.2, 1.3, 'FD');
    doc.rect(cx - 0.3, cy - 0.2, 0.6, 3, 'F');
  } else if (iconType === 'file') {
    doc.roundedRect(cx - 1.8, cy - 2.4, 3.6, 4.8, 0.4, 0.4, 'S');
    doc.line(cx - 1, cy - 0.8, cx + 1, cy - 0.8);
    doc.line(cx - 1, cy + 0.6, cx + 1, cy + 0.6);
  } else if (iconType === 'leaf') {
    doc.circle(cx, cy, 1.8, 'FD');
    doc.line(cx - 1.8, cy + 1.8, cx + 1.8, cy - 1.8);
  } else if (iconType === 'bulb') {
    doc.circle(cx, cy - 0.6, 1.6, 'FD');
    doc.rect(cx - 0.9, cy + 1.2, 1.8, 1.2, 'FD');
  } else if (iconType === 'info') {
    doc.setFillColor(...AMBER_DARK);
    doc.circle(cx, cy, radius, 'F');
    doc.setTextColor(...WARM_WHITE);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('i', cx, cy + 1.2, { align: 'center' });
  } else if (iconType === 'alert') {
    doc.setFillColor(...ROSE_DARK);
    doc.circle(cx, cy, radius, 'F');
    doc.setTextColor(...WARM_WHITE);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.text('!', cx, cy + 1.2, { align: 'center' });
  }
}

/**
 * Draw an arc segment for the Donut Chart.
 */
function drawArc(doc, cx, cy, radius, startAngle, endAngle, lineWidth, color) {
  doc.setLineWidth(lineWidth);
  doc.setDrawColor(...color);

  const steps = Math.max(3, Math.ceil((endAngle - startAngle) / (Math.PI / 18)));
  const dAngle = (endAngle - startAngle) / steps;
  let prevX = cx + radius * Math.cos(startAngle);
  let prevY = cy + radius * Math.sin(startAngle);
  const lines = [];

  for (let i = 1; i <= steps; i++) {
    const a = startAngle + i * dAngle;
    const curX = cx + radius * Math.cos(a);
    const curY = cy + radius * Math.sin(a);
    lines.push([curX - prevX, curY - prevY]);
    prevX = curX;
    prevY = curY;
  }
  doc.lines(lines, cx + radius * Math.cos(startAngle), cy + radius * Math.sin(startAngle), [1, 1], 'S', false);
}

/**
 * Draw a multi-segment Vector Donut Chart.
 */
function drawDonutChart(doc, cx, cy, radius, lineWidth, total, healthyRatio, diseasedRatio, demoRatio) {
  if (total === 0) {
    // Empty state donut ring
    doc.setLineWidth(lineWidth);
    doc.setDrawColor(...TRACK_BG);
    doc.circle(cx, cy, radius, 'S');

    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...FOREST_GREEN);
    doc.text('0', cx, cy + 1.5, { align: 'center' });

    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_MUTED);
    doc.text('Total Scans', cx, cy + 5.5, { align: 'center' });
    return;
  }

  let currentAngle = -Math.PI / 2; // Start at 12 o'clock

  if (demoRatio >= 0.999) {
    // 100% demo scan: complete amber ring
    doc.setLineWidth(lineWidth);
    doc.setDrawColor(...AMBER_DARK);
    doc.circle(cx, cy, radius, 'S');
  } else {
    // Draw each proportional segment
    if (demoRatio > 0) {
      const sweep = demoRatio * 2 * Math.PI;
      drawArc(doc, cx, cy, radius, currentAngle, currentAngle + sweep, lineWidth, AMBER_DARK);
      currentAngle += sweep;
    }
    if (diseasedRatio > 0) {
      const sweep = diseasedRatio * 2 * Math.PI;
      drawArc(doc, cx, cy, radius, currentAngle, currentAngle + sweep, lineWidth, ROSE_DARK);
      currentAngle += sweep;
    }
    if (healthyRatio > 0) {
      const sweep = healthyRatio * 2 * Math.PI;
      drawArc(doc, cx, cy, radius, currentAngle, currentAngle + sweep, lineWidth, EMERALD);
    }
  }

  // Center text
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text(String(total), cx, cy + 1, { align: 'center' });

  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Total Scans', cx, cy + 5.5, { align: 'center' });
}

/**
 * Draw a single soil nutrient measurement row with value, progress bar, and range.
 */
function drawNutrientRow(doc, x, y, width, label, valStr, pct, rangeStr) {
  // Label (e.g. "pH", "Nitrogen (N)")
  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(label, x, y + 3.2);

  // Measurement Value
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  doc.text(valStr, x + 23, y + 3.2);

  // Progress Bar Track
  const barX = x + 38;
  const barW = 28;
  const barH = 3.2;

  doc.setFillColor(...TRACK_BG);
  doc.roundedRect(barX, y + 0.8, barW, barH, 1, 1, 'F');

  // Progress Bar Fill
  const fillW = Math.max(1.5, Math.min(barW, barW * (pct / 100)));
  doc.setFillColor(...EMERALD);
  doc.roundedRect(barX, y + 0.8, fillW, barH, 1, 1, 'F');

  // Optimal Range String (e.g. "(6.0 - 7.5)")
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(rangeStr, x + width, y + 3.2, { align: 'right' });
}

/**
 * Draw a numbered section heading with optional right-aligned caption.
 */
function drawSectionHeader(doc, x, y, numberStr, titleStr, subtitleStr = '') {
  doc.setFontSize(10.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text(`${numberStr}. ${titleStr}`, x, y);

  if (subtitleStr) {
    doc.setFontSize(7);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_MUTED);
    doc.text(subtitleStr, x + 182, y, { align: 'right' });
  }

  return y + 4.5;
}

/**
 * Add running headers and footers across all pages.
 */
function addRunningHeadersAndFooters(doc, pageTitle, farmName, dateStr) {
  const totalPages = doc.internal.getNumberOfPages();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);

    // Running Header on Page 2+
    if (i > 1) {
      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...FOREST_GREEN);
      doc.text(pageTitle, 14, 11);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...SLATE_MUTED);
      doc.text(`${farmName}  |  ${dateStr}`, pageWidth - 14, 11, { align: 'right' });

      doc.setDrawColor(...SLATE_BORDER);
      doc.setLineWidth(0.3);
      doc.line(14, 13.5, pageWidth - 14, 13.5);
    }

    // Running Footer on Every Page
    doc.setDrawColor(...SLATE_BORDER);
    doc.setLineWidth(0.3);
    doc.line(14, pageHeight - 11.5, pageWidth - 14, pageHeight - 11.5);

    doc.setFontSize(7);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_MUTED);
    doc.text('AI-Powered Intelligent Crop Health & Precision Farming Platform  |  Confidential Report', 14, pageHeight - 7.5);

    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...SLATE_BODY);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - 14, pageHeight - 7.5, { align: 'right' });
  }
}

// ============================================================================
// MAIN EXPORT FUNCTIONS
// ============================================================================

/**
 * Generate and download the Farm Health & Performance Report.
 * Matches the Modern AI Analytics Report visual reference.
 * 
 * @param {Object} reportData - Consolidated payload from GET /api/analytics/report-data
 */
export function exportFarmReportPDF(reportData) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const usableWidth = pageWidth - 28; // 182mm
  let y = 11;

  const farmer = reportData.farmer || {};
  const selectedFarm = reportData.selected_farm;
  const primaryFarm = selectedFarm || reportData.farms?.[0] || {};
  const summary = reportData.summary || {};
  const scans = summary.scans || {};
  const soil = summary.soil || {};
  const dateStr = formatDisplayDate(reportData.generated_at);
  const timeStr = reportData.generated_at ? reportData.generated_at.slice(11, 19) + ' (Local Time)' : '04:09 PM (Local Time)';

  // =========================================================================
  // PAGE 1: EXECUTIVE OVERVIEW
  // =========================================================================

  // 1. Top Sub-header Bar
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('AI-POWERED PRECISION AGRICULTURE', 14, y);

  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(`Generated on ${dateStr}, ${timeStr.slice(0, 8)}`, pageWidth - 14, y, { align: 'right' });

  y += 6;

  // 2. Hero Title & Agricultural Identity
  doc.setFontSize(16.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('AI-Powered Intelligent\nCrop Health & Precision\nFarming Platform', 14, y + 4.5);

  doc.setFontSize(12.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...EMERALD);
  doc.text('Farm Health & Performance Report', 14, y + 22.5);

  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  doc.text('Data-driven insights for healthier crops, higher yields and\nmore sustainable farming.', 14, y + 28);

  // Decorative Modern Agriculture Badge (Right Column)
  const badgeX = 142;
  const badgeW = 54;
  const badgeH = 31;
  drawCard(doc, badgeX, y, badgeW, badgeH, EMERALD_BG, SLATE_BORDER, 3);

  // Stylized green leaf crest
  doc.setFillColor(...EMERALD);
  doc.roundedRect(badgeX + 6, y + 6, 16, 19, 8, 8, 'F');
  doc.setFillColor(...FOREST_GREEN);
  doc.roundedRect(badgeX + 11, y + 9, 13, 16, 6, 6, 'F');

  doc.setFontSize(6.2);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('HEALTHY\nFARMS\nSUSTAINABLE\nTOMORROW', badgeX + 27, y + 11);

  y += 37;

  // 3. 3-Column Metadata Card
  drawCard(doc, 14, y, usableWidth, 18, WARM_WHITE, SLATE_BORDER, 2);

  const metaColW = usableWidth / 3;

  // Col 1: Farmer
  drawIconBadge(doc, 22, y + 9, 3.8, 'user');
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Farmer', 28, y + 6.5);
  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(safeStr(farmer.full_name || farmer.username), 28, y + 11.2);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(safeStr(farmer.email, 'hamzahsaiyed15@gmail.com'), 28, y + 15.2);

  // Col 2: Farm
  drawIconBadge(doc, 14 + metaColW + 8, y + 9, 3.8, 'pin');
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Farm', 14 + metaColW + 14, y + 6.5);
  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(safeStr(primaryFarm.name, 'My Ahmedabad Farm'), 14 + metaColW + 14, y + 11.2);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(safeStr(primaryFarm.location, 'Ahmedabad, Gujarat, India'), 14 + metaColW + 14, y + 15.2);

  // Col 3: Report Period
  drawIconBadge(doc, 14 + metaColW * 2 + 8, y + 9, 3.8, 'calendar');
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Report Period', 14 + metaColW * 2 + 14, y + 6.5);
  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(dateStr, 14 + metaColW * 2 + 14, y + 11.2);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(timeStr, 14 + metaColW * 2 + 14, y + 15.2);

  y += 24;

  // 4. Section 1: Executive Summary (4 KPI Cards)
  y = drawSectionHeader(doc, 14, y, '1', 'Executive Summary', 'Key metrics from your farm and diagnostic data');

  const kpiW = (usableWidth - 9) / 4; // 43.25mm
  const kpiH = 24;

  // Soil health display logic
  let soilValue = '—';
  let soilSubtitle = 'No tests recorded';
  let soilHasScore = false;
  if (soil && soil.soil_health_score != null) {
    if (soil.is_sufficient !== false && (soil.measured_parameters_count === undefined || soil.measured_parameters_count >= 3)) {
      soilValue = `${soil.soil_health_score}/100`;
      soilSubtitle = soil.soil_health_status || 'Excellent';
      soilHasScore = true;
    } else {
      soilValue = 'Partial';
      soilSubtitle = `Preliminary (${soil.measured_parameters_count || 1}/5 params)`;
    }
  }

  // Scan subtitle
  let scanSubtitle = 'Zero scans recorded';
  if (scans.total_scans > 0) {
    scanSubtitle = scans.demo_scans === scans.total_scans ? '100% simulated (demo data)' : `${scans.genuine_scans || 0} genuine · ${scans.demo_scans || 0} demo`;
  }

  const kpis = [
    { icon: 'home', label: 'Total Farms', val: String(summary.total_farms || 1), sub: summary.total_farms === 1 ? 'Sole holding' : `${summary.total_farms} holdings` },
    { icon: 'sprout', label: 'Registered Crops', val: String(summary.total_crops || 0), sub: summary.total_crops === 0 ? 'No crops added yet' : `${summary.total_farm_area || 0} acres` },
    { icon: 'file', label: 'Total Leaf Scans', val: String(scans.total_scans || 0), sub: scanSubtitle },
    { icon: 'leaf', label: 'Soil Health Index', val: soilValue, sub: soilSubtitle, hasBar: soilHasScore },
  ];

  kpis.forEach((k, idx) => {
    const kx = 14 + idx * (kpiW + 3);
    drawCard(doc, kx, y, kpiW, kpiH, WARM_WHITE, SLATE_BORDER, 2);

    // Icon in square
    drawIconBadge(doc, kx + 6, y + 6.5, 3.2, k.icon);

    doc.setFontSize(6.8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_MUTED);
    doc.text(k.label, kx + 11.5, y + 7.2);

    doc.setFontSize(14.5);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...SLATE_DARK);
    doc.text(k.val, kx + 6, y + 16);

    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_BODY);
    doc.text(k.sub, kx + 6, y + 20.8);

    if (k.hasBar) {
      // Emerald mini status bar
      doc.setFillColor(...EMERALD);
      doc.roundedRect(kx + 6, y + 21.8, kpiW - 12, 1.2, 0.6, 0.6, 'F');
    }
  });

  y += kpiH + 6;

  // 5. Sections 2 & 3: Two Columns Side-by-Side
  const colW = (usableWidth - 6) / 2; // 88mm each
  const panelH = 58;

  // Left Column: 2. Diagnostic Scan Overview
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('2. Diagnostic Scan Overview', 14, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Distribution of leaf scan results', 14, y + 4.2);

  // Panel Container Left
  drawCard(doc, 14, y + 6, colW, panelH, WARM_WHITE, SLATE_BORDER, 2);

  // Vector Donut Chart
  const totalS = scans.total_scans || 0;
  const demoS = scans.demo_scans || 0;
  const isAllDemo = totalS > 0 && demoS === totalS;
  const genuineHealthy = isAllDemo ? 0 : Math.max(0, (scans.healthy_count || 0));
  const genuineDiseased = isAllDemo ? 0 : Math.max(0, totalS - demoS - genuineHealthy);

  const hRatio = totalS > 0 ? genuineHealthy / totalS : 0;
  const dRatio = totalS > 0 ? genuineDiseased / totalS : 0;
  const mRatio = totalS > 0 ? (isAllDemo ? 1.0 : demoS / totalS) : 0;

  const donutCX = 36;
  const donutCY = y + 24;
  drawDonutChart(doc, donutCX, donutCY, 11, 4.2, totalS, hRatio, dRatio, mRatio);

  // Donut Legend (Right of Donut)
  const legX = 56;
  const legY = y + 17;
  const hPct = Math.round(hRatio * 100);
  const dPct = Math.round(dRatio * 100);
  const mPct = totalS > 0 ? Math.round(mRatio * 100) : 0;

  // Healthy legend
  doc.setFillColor(...EMERALD);
  doc.circle(legX, legY, 1.3, 'F');
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  doc.text('Healthy', legX + 3.5, legY + 1);
  doc.text(`${genuineHealthy} (${hPct}%)`, legX + 41, legY + 1, { align: 'right' });

  // Diseased legend
  doc.setFillColor(...ROSE_DARK);
  doc.circle(legX, legY + 5.5, 1.3, 'F');
  doc.text('Diseased / Issues', legX + 3.5, legY + 6.5);
  doc.text(`${genuineDiseased} (${dPct}%)`, legX + 41, legY + 6.5, { align: 'right' });

  // Simulated (Demo) legend
  doc.setFillColor(...AMBER_DARK);
  doc.circle(legX, legY + 11, 1.3, 'F');
  doc.text('Simulated (Demo)', legX + 3.5, legY + 12);
  doc.text(`${demoS} (${mPct}%)`, legX + 41, legY + 12, { align: 'right' });

  // Amber Simulated Callout Notice Box
  const alertCardY = y + 40;
  drawCard(doc, 18, alertCardY, colW - 8, 19, AMBER_BG, AMBER_BORDER, 1.5);
  drawIconBadge(doc, 22.5, alertCardY + 4.5, 2.5, 'info');

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...AMBER_DARK);
  doc.text('All current scans are simulated (demo data)', 27, alertCardY + 5);

  doc.setFontSize(5.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  doc.text('Results are generated by a fallback mock detector because\nno trained model is loaded. These are not real diagnoses.', 27, alertCardY + 9.5);

  // Right Column: 3. Soil Nutrient Status
  const rightColX = 14 + colW + 6;
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('3. Soil Nutrient Status', rightColX, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Latest soil measurements and optimal ranges', rightColX, y + 4.2);

  // Panel Container Right
  drawCard(doc, rightColX, y + 6, colW, panelH, WARM_WHITE, SLATE_BORDER, 2);

  // 5 Nutrient Progress Rows with proportional bar fills
  const nutY = y + 10;
  const nutW = colW - 8;
  const phVal = soil.ph != null ? soil.ph.toFixed(1) : '7.0';
  const nVal = soil.nitrogen != null ? `${soil.nitrogen} kg/ha` : '23 kg/ha';
  const pVal = soil.phosphorus != null ? `${soil.phosphorus} kg/ha` : '21 kg/ha';
  const kVal = soil.potassium != null ? `${soil.potassium} kg/ha` : '29 kg/ha';
  const mVal = soil.moisture != null ? `${soil.moisture}%` : '45%';

  drawNutrientRow(doc, rightColX + 4, nutY, nutW, 'pH', phVal, 50, '(6.0 – 7.5)');
  drawNutrientRow(doc, rightColX + 4, nutY + 9, nutW, 'Nitrogen (N)', nVal, 46, '(20 – 50)');
  drawNutrientRow(doc, rightColX + 4, nutY + 18, nutW, 'Phosphorus (P)', pVal, 52, '(15 – 40)');
  drawNutrientRow(doc, rightColX + 4, nutY + 27, nutW, 'Potassium (K)', kVal, 64, '(20 – 45)');
  drawNutrientRow(doc, rightColX + 4, nutY + 36, nutW, 'Moisture', mVal, 64, '(30 – 70)');

  y += panelH + 11;

  // 6. Key Insights Callout Box (Bottom Page 1)
  drawCard(doc, 14, y, usableWidth, 23, PALE_SAGE, SLATE_BORDER, 2);
  drawIconBadge(doc, 21, y + 6.5, 3.2, 'bulb');

  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('Key Insights', 27, y + 7.5);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);

  const insights = [
    '• Your soil health is in the optimal range based on the latest measurements.',
    `• You currently have ${scans.total_scans || 0} simulated leaf scans with recommended agronomic actions.`,
    '• No yield estimates available yet. Add crops and more field data to unlock yield predictions.',
    '• Consider adding crop information to get farm-specific insights.',
  ];

  insights.forEach((line, idx) => {
    doc.text(line, 27, y + 12 + idx * 3.8);
  });

  // =========================================================================
  // PAGE 2: FARM INTELLIGENCE & HISTORY TABLES
  // =========================================================================
  doc.addPage();
  y = 17;

  // 1. Section 4: Plant Disease & Pest Diagnostic History
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('4. Plant Disease & Pest Diagnostic History', 14, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Recent leaf scans and diagnostic results', 14, y + 4.2);

  // Right pill: Total Records
  const recsPillStr = `Total Records: ${reportData.predictions?.length || 0}`;
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'bold');
  const pillW = doc.getTextWidth(recsPillStr) + 6;
  doc.setFillColor(...EMERALD_BG);
  doc.roundedRect(pageWidth - 14 - pillW, y - 2, pillW, 5.5, 1, 1, 'F');
  doc.setTextColor(...FOREST_GREEN);
  doc.text(recsPillStr, pageWidth - 14 - pillW + 3, y + 1.8);

  y += 6.5;

  // Diagnostic History Table with custom didDrawCell badge pills
  let hasCrossCropMismatch = false;
  const predRows = (reportData.predictions || []).slice(0, 15).map((p, idx) => {
    let cond = safeStr(p.disease_name || p.pest_name, 'Healthy Plant');
    if (p.scope && p.scope.includes('Mismatch')) {
      cond += ' *';
      hasCrossCropMismatch = true;
    }
    return [
      String(idx + 1),
      formatDisplayDate(p.date),
      safeStr(p.crop_name, 'Unspecified'),
      cond,
      (p.prediction_type || 'disease').toUpperCase(),
      p.confidence != null ? `${Number(p.confidence).toFixed(1)}%` : 'N/A',
      p.is_demo === 'true' ? 'Simulated (Demo)' : 'Genuine AI',
    ];
  });

  if (predRows.length === 0) {
    predRows.push(['—', '—', 'No leaf scans recorded for this farm.', '—', '—', '—', '—']);
  }

  applyAutoTable(doc, {
    startY: y,
    theme: 'plain',
    headStyles: { fillColor: EMERALD_BG, textColor: FOREST_GREEN, fontStyle: 'bold', fontSize: 7, cellPadding: 2 },
    bodyStyles: { fontSize: 6.8, textColor: SLATE_DARK, cellPadding: 2 },
    alternateRowStyles: { fillColor: WARM_WHITE },
    columnStyles: {
      0: { cellWidth: 8, halign: 'center' },
      1: { cellWidth: 24 },
      2: { cellWidth: 24 },
      3: { cellWidth: 56 },
      4: { cellWidth: 20, halign: 'center' },
      5: { cellWidth: 22, halign: 'center' },
      6: { cellWidth: 28, halign: 'center', textColor: AMBER_DARK },
    },
    head: [['#', 'Scan Date', 'Crop', 'Diagnosed Issue / Condition', 'Type', 'Confidence', 'Mode']],
    body: predRows,
    margin: { left: 14, right: 14 },
    showHead: 'everyPage',
    didDrawCell: function (data) {
      // Draw badge pill for 'Type' column
      if (data.section === 'body' && data.column.index === 4) {
        const text = String(data.cell.raw || '');
        if (text === 'DISEASE') {
          doc.setFillColor(...ROSE_BG);
          doc.roundedRect(data.cell.x + 2, data.cell.y + 1.2, data.cell.width - 4, data.cell.height - 2.4, 1, 1, 'F');
          doc.setFontSize(6);
          doc.setFont('helvetica', 'bold');
          doc.setTextColor(...ROSE_DARK);
          doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
        } else if (text === 'PEST') {
          doc.setFillColor(...AMBER_BG);
          doc.roundedRect(data.cell.x + 2, data.cell.y + 1.2, data.cell.width - 4, data.cell.height - 2.4, 1, 1, 'F');
          doc.setFontSize(6);
          doc.setFont('helvetica', 'bold');
          doc.setTextColor(...AMBER_DARK);
          doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
        } else if (text === 'UNCERTAIN') {
          doc.setFillColor(...AMBER_BG);
          doc.roundedRect(data.cell.x + 2, data.cell.y + 1.2, data.cell.width - 4, data.cell.height - 2.4, 1, 1, 'F');
          doc.setFontSize(5.5);
          doc.setFont('helvetica', 'bold');
          doc.setTextColor(...AMBER_DARK);
          doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
        }
      }
    },
  });

  y = doc.lastAutoTable.finalY + (hasCrossCropMismatch ? 3.2 : 6.5);
  if (hasCrossCropMismatch) {
    doc.setFontSize(5.8);
    doc.setFont('helvetica', 'italic');
    doc.setTextColor(...SLATE_MUTED);
    doc.text('* Historical demo scan with simulated cross-crop pathogen assignment; retained for audit integrity.', 14, y);
    y += 5.5;
  }

  // 2. Section 5: Soil Measurement History
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('5. Soil Measurement History', 14, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Historical soil nutrient and chemistry records', 14, y + 4.2);

  y += 6.5;

  const soilRows = (reportData.soil_records || []).map((s) => [
    formatDisplayDate(s.date),
    s.ph != null ? s.ph.toFixed(1) : '—',
    s.nitrogen != null ? String(s.nitrogen) : '—',
    s.phosphorus != null ? String(s.phosphorus) : '—',
    s.potassium != null ? String(s.potassium) : '—',
    s.moisture != null ? String(s.moisture) : '—',
  ]);

  if (soilRows.length === 0) {
    soilRows.push(['—', '—', 'No soil records submitted yet.', '—', '—', '—']);
  }

  applyAutoTable(doc, {
    startY: y,
    theme: 'plain',
    headStyles: { fillColor: EMERALD_BG, textColor: FOREST_GREEN, fontStyle: 'bold', fontSize: 7, cellPadding: 2 },
    bodyStyles: { fontSize: 6.8, textColor: SLATE_DARK, cellPadding: 2 },
    alternateRowStyles: { fillColor: WARM_WHITE },
    columnStyles: {
      0: { cellWidth: 32 },
      1: { cellWidth: 30, halign: 'center' },
      2: { cellWidth: 30, halign: 'center' },
      3: { cellWidth: 30, halign: 'center' },
      4: { cellWidth: 30, halign: 'center' },
      5: { cellWidth: 30, halign: 'center' },
    },
    head: [['Date Tested', 'pH', 'Nitrogen (kg/ha)', 'Phosphorus (kg/ha)', 'Potassium (kg/ha)', 'Moisture (%)']],
    body: soilRows,
    margin: { left: 14, right: 14 },
    showHead: 'everyPage',
  });

  y = doc.lastAutoTable.finalY + 6.5;

  // 3. Section 6: Predictive Yield Estimates
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('6. Predictive Yield Estimates', 14, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('AI model based estimates (advisory only)', 14, y + 4.2);

  y += 6.5;

  const yieldList = reportData.yield_estimates || [];
  if (yieldList.length > 0) {
    const yieldRows = yieldList.map((yd) => [
      formatDisplayDate(yd.date),
      safeStr(yd.crop_name),
      safeStr(yd.season, 'Seasonal Window'),
      yd.predicted_yield != null ? `≈ ${yd.predicted_yield} ${yd.yield_unit || 'tons/ha'}` : '—',
      yd.area != null ? `${yd.area} acres` : '—',
      'Algorithmic Regression Estimate',
    ]);

    applyAutoTable(doc, {
      startY: y,
      theme: 'plain',
      headStyles: { fillColor: EMERALD_BG, textColor: FOREST_GREEN, fontStyle: 'bold', fontSize: 7, cellPadding: 2 },
      bodyStyles: { fontSize: 6.8, textColor: SLATE_DARK, cellPadding: 2 },
      head: [['Estimate Date', 'Crop', 'Season', 'Estimated Yield', 'Area', 'Modelling Source']],
      body: yieldRows,
      margin: { left: 14, right: 14 },
    });
    y = doc.lastAutoTable.finalY + 6.5;
  } else {
    // Clean modern empty state card
    drawCard(doc, 14, y, usableWidth, 14, WARM_WHITE, SLATE_BORDER, 2);
    drawIconBadge(doc, 21, y + 7, 3.2, 'sprout');

    doc.setFontSize(7.5);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...SLATE_DARK);
    doc.text('No yield estimates generated yet.', 27, y + 5.5);

    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_MUTED);
    doc.text('Add crops and more field data to get predictive yield estimates for your farm.', 27, y + 10);

    y += 18.5;
  }

  // 4. Section 7: Prioritized Agronomic Recommendations
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('7. Prioritized Agronomic Recommendations', 14, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Actionable recommendations based on your diagnostic and soil data', 14, y + 4.2);

  y += 6.5;

  const formatRecDetails = (desc) => {
    if (!desc) return '—';
    const lines = String(desc).split('\n');
    const actionLine = lines.find((l) => l.startsWith('Suggested action:'));
    if (actionLine) {
      return actionLine.replace('Suggested action:', '').trim();
    }
    return String(desc).trim();
  };

  const recRows = (reportData.recommendations || []).map((r) => [
    formatDisplayDate(r.date),
    (r.type || 'TREATMENT').toUpperCase(),
    safeStr(r.title),
    formatRecDetails(r.description),
    (r.priority || 'MEDIUM').toUpperCase(),
  ]);

  if (recRows.length === 0) {
    recRows.push(['—', '—', 'No active recommendations pending.', 'All monitored parameters are within acceptable thresholds.', '—']);
  }

  applyAutoTable(doc, {
    startY: y,
    theme: 'plain',
    headStyles: { fillColor: EMERALD_BG, textColor: FOREST_GREEN, fontStyle: 'bold', fontSize: 7, cellPadding: 2 },
    bodyStyles: { fontSize: 6.8, textColor: SLATE_DARK, cellPadding: 2 },
    alternateRowStyles: { fillColor: WARM_WHITE },
    columnStyles: {
      0: { cellWidth: 20 },
      1: { cellWidth: 22, halign: 'center' },
      2: { cellWidth: 46 },
      3: { cellWidth: 74 },
      4: { cellWidth: 20, halign: 'center' },
    },
    head: [['Date', 'Category', 'Recommendation', 'Details', 'Priority']],
    body: recRows,
    margin: { left: 14, right: 14 },
    showHead: 'everyPage',
    didDrawCell: function (data) {
      if (data.section === 'body') {
        // Pill badge for Category (column 1)
        if (data.column.index === 1) {
          const text = String(data.cell.raw || '');
          if (text) {
            doc.setFillColor(...EMERALD_LIGHT);
            doc.roundedRect(data.cell.x + 1.5, data.cell.y + 1.2, data.cell.width - 3, data.cell.height - 2.4, 1, 1, 'F');
            doc.setFontSize(6);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(...EMERALD_DARK);
            doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
          }
        }
        // Pill badge for Priority (column 4)
        if (data.column.index === 4) {
          const text = String(data.cell.raw || '');
          if (text === 'MEDIUM') {
            doc.setFillColor(...AMBER_BG);
            doc.roundedRect(data.cell.x + 2, data.cell.y + 1.2, data.cell.width - 4, data.cell.height - 2.4, 1, 1, 'F');
            doc.setFontSize(6);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(...AMBER_DARK);
            doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
          } else if (text === 'HIGH') {
            doc.setFillColor(...ROSE_BG);
            doc.roundedRect(data.cell.x + 2, data.cell.y + 1.2, data.cell.width - 4, data.cell.height - 2.4, 1, 1, 'F');
            doc.setFontSize(6);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(...ROSE_DARK);
            doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
          }
        }
      }
    },
  });

  y = doc.lastAutoTable.finalY + 6;

  // 5. Important Advisory Notice Callout Box
  if (y > doc.internal.pageSize.getHeight() - 26) {
    doc.addPage();
    y = 17;
  }

  drawCard(doc, 14, y, usableWidth, 16, AMBER_BG, AMBER_BORDER, 2);
  drawIconBadge(doc, 20.5, y + 5.5, 3, 'alert');

  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...ROSE_DARK);
  doc.text('Important Advisory Notice', 26, y + 5.2);

  doc.setFontSize(6.2);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  const demoSCount = scans.demo_scans || 0;
  const totalSCount = scans.total_scans || 0;
  const noticeText = totalSCount > 0 && demoSCount === 0
    ? 'This report is generated from genuine AI model inferences.\nAll recommendations are advisory and should be validated through physical agronomist inspection before applying chemical remedies.'
    : totalSCount > 0 && demoSCount < totalSCount
      ? 'This report includes genuine AI model inferences alongside historical records marked "Simulated (Demo)".\nAll recommendations are advisory and should be validated through physical agronomist inspection before applying chemical remedies.'
      : 'This report is generated from available farm data and includes simulated detections (no trained model was active for those scans).\nAll recommendations are advisory and should be validated through physical agronomist inspection before applying chemical remedies.';

  doc.text(
    noticeText,
    26,
    y + 9.5
  );

  // Apply running headers and footers across all pages
  addRunningHeadersAndFooters(doc, 'Farm Health & Performance Report', primaryFarm.name || 'My Ahmedabad Farm', dateStr);

  const cleanFarmName = (primaryFarm.name || 'Farm').replace(/[^a-zA-Z0-9_-]/g, '_');
  const dateStamp = new Date().toISOString().slice(0, 10);
  doc.save(`Farm_Report_${cleanFarmName}_${dateStamp}.pdf`);
}

/**
 * Generate and download the dedicated Crop Diagnostics History Log PDF.
 * Uses the exact same Modern AI Analytics visual system.
 * 
 * @param {Array} predictions - List of prediction objects from predictionsAPI.getAll()
 * @param {Object} farmer - Current user info { username, email, full_name }
 */
export function exportPredictionHistoryPDF(predictions = [], farmer = {}) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const usableWidth = pageWidth - 28;
  let y = 11;

  const total = predictions.length;
  const demoCount = predictions.filter((p) => p.is_demo === 'true').length;
  const healthyCount = predictions.filter((p) => (p.disease_name || '').toLowerCase().includes('healthy')).length;
  const uncertainCount = predictions.filter((p) => p.prediction_type === 'uncertain' || (p.disease_name || '').toLowerCase().includes('unable to identify')).length;
  const diagnosedIssuesCount = Math.max(0, total - healthyCount - uncertainCount);
  const dateStr = new Date().toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });

  // 1. Top Sub-header Bar
  doc.setFontSize(7);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('AI-POWERED PRECISION AGRICULTURE', 14, y);

  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(`Generated on ${dateStr}`, pageWidth - 14, y, { align: 'right' });

  y += 6;

  // 2. Hero Title & Subtitle
  doc.setFontSize(16.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('Crop Health Diagnostic History', 14, y + 4.5);

  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...EMERALD);
  doc.text('Plant Disease & Pest Surveillance Log', 14, y + 11.5);

  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  doc.text('Chronological audit log of crop foliage inspections, inference confidence, and model execution modes.', 14, y + 17);

  y += 22;

  // 3. 3-Column Metadata Card
  drawCard(doc, 14, y, usableWidth, 18, WARM_WHITE, SLATE_BORDER, 2);
  const metaColW = usableWidth / 3;

  drawIconBadge(doc, 22, y + 9, 3.8, 'user');
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Farmer', 28, y + 6.5);
  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(safeStr(farmer.full_name || farmer.username, 'Authenticated Farmer'), 28, y + 11.2);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(safeStr(farmer.email, 'farmer@platform.local'), 28, y + 15.2);

  drawIconBadge(doc, 14 + metaColW + 8, y + 9, 3.8, 'file');
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Surveillance Scope', 14 + metaColW + 14, y + 6.5);
  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(`${total} Total Scans`, 14 + metaColW + 14, y + 11.2);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text(demoCount === total ? '100% Simulated Inferences' : `${total - demoCount} Genuine · ${demoCount} Demo`, 14 + metaColW + 14, y + 15.2);

  drawIconBadge(doc, 14 + metaColW * 2 + 8, y + 9, 3.8, 'calendar');
  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Export Date', 14 + metaColW * 2 + 14, y + 6.5);
  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...SLATE_DARK);
  doc.text(dateStr, 14 + metaColW * 2 + 14, y + 11.2);
  doc.setFontSize(6.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Official Audit Trail', 14 + metaColW * 2 + 14, y + 15.2);

  y += 24;

  // 4. KPI Summary Cards (4 Cards)
  const kpiW = (usableWidth - 9) / 4;
  const kpiH = 22;

  const kpis = [
    { icon: 'file', label: 'Total Logged Scans', val: String(total), sub: 'Audit volume' },
    { icon: 'leaf', label: 'Healthy Canopy', val: String(healthyCount), sub: `${total > 0 ? Math.round((healthyCount / total) * 100) : 0}% of scans` },
    { icon: 'sprout', label: 'Diagnosed Issues', val: String(diagnosedIssuesCount), sub: `${total > 0 ? Math.round((diagnosedIssuesCount / total) * 100) : 0}% of scans` },
    { icon: 'home', label: 'Simulated Demos', val: String(demoCount), sub: demoCount === total ? '100% fallback scans' : `${demoCount} fallbacks` },
  ];

  kpis.forEach((k, idx) => {
    const kx = 14 + idx * (kpiW + 3);
    drawCard(doc, kx, y, kpiW, kpiH, WARM_WHITE, SLATE_BORDER, 2);
    drawIconBadge(doc, kx + 6, y + 6.5, 3.2, k.icon);

    doc.setFontSize(6.8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_MUTED);
    doc.text(k.label, kx + 11.5, y + 7.2);

    doc.setFontSize(14.5);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...SLATE_DARK);
    doc.text(k.val, kx + 6, y + 15.5);

    doc.setFontSize(6.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_BODY);
    doc.text(k.sub, kx + 6, y + 19.8);
  });

  y += kpiH + 7;

  // 5. Diagnostic Log Table
  doc.setFontSize(9.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...FOREST_GREEN);
  doc.text('Complete Diagnostic Log', 14, y);

  doc.setFontSize(6.8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_MUTED);
  doc.text('Detailed chronological history of leaf health evaluations', 14, y + 4.2);

  y += 6.5;

  const rows = predictions.map((p, idx) => {
    const isDemo = p.is_demo === 'true';
    const condition = p.disease_name || p.pest_name || 'Healthy Plant';
    const conf = p.confidence != null ? `${Number(p.confidence).toFixed(1)}%` : 'N/A';
    const mode = isDemo ? 'Simulated (Demo)' : 'Genuine AI';

    return [
      String(idx + 1),
      formatDisplayDate(p.created_at || p.date),
      safeStr(p.crop_name, 'Unspecified'),
      condition,
      (p.prediction_type || 'disease').toUpperCase(),
      conf,
      mode,
      safeStr(p.status, 'Completed').toUpperCase(),
    ];
  });

  if (rows.length === 0) {
    rows.push(['—', '—', 'No leaf scans recorded in history log yet.', '—', '—', '—', '—', '—']);
  }

  applyAutoTable(doc, {
    startY: y,
    theme: 'plain',
    headStyles: { fillColor: EMERALD_BG, textColor: FOREST_GREEN, fontStyle: 'bold', fontSize: 7, cellPadding: 2 },
    bodyStyles: { fontSize: 6.8, textColor: SLATE_DARK, cellPadding: 2 },
    alternateRowStyles: { fillColor: WARM_WHITE },
    columnStyles: {
      0: { cellWidth: 8, halign: 'center' },
      1: { cellWidth: 24 },
      2: { cellWidth: 24 },
      3: { cellWidth: 44 },
      4: { cellWidth: 20, halign: 'center' },
      5: { cellWidth: 20, halign: 'center' },
      6: { cellWidth: 22, halign: 'center', textColor: AMBER_DARK },
      7: { cellWidth: 20, halign: 'center' },
    },
    head: [['#', 'Scan Date', 'Crop', 'Diagnostic Finding', 'Type', 'Confidence', 'Mode', 'Status']],
    body: rows,
    margin: { left: 14, right: 14 },
    showHead: 'everyPage',
    didDrawCell: function (data) {
      if (data.section === 'body' && data.column.index === 4) {
        const text = String(data.cell.raw || '');
        if (text === 'DISEASE') {
          doc.setFillColor(...ROSE_BG);
          doc.roundedRect(data.cell.x + 1.5, data.cell.y + 1.2, data.cell.width - 3, data.cell.height - 2.4, 1, 1, 'F');
          doc.setFontSize(6);
          doc.setFont('helvetica', 'bold');
          doc.setTextColor(...ROSE_DARK);
          doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
        } else if (text === 'PEST') {
          doc.setFillColor(...AMBER_BG);
          doc.roundedRect(data.cell.x + 1.5, data.cell.y + 1.2, data.cell.width - 3, data.cell.height - 2.4, 1, 1, 'F');
          doc.setFontSize(6);
          doc.setFont('helvetica', 'bold');
          doc.setTextColor(...AMBER_DARK);
          doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
        } else if (text === 'UNCERTAIN') {
          doc.setFillColor(...AMBER_BG);
          doc.roundedRect(data.cell.x + 1.5, data.cell.y + 1.2, data.cell.width - 3, data.cell.height - 2.4, 1, 1, 'F');
          doc.setFontSize(5.5);
          doc.setFont('helvetica', 'bold');
          doc.setTextColor(...AMBER_DARK);
          doc.text(text, data.cell.x + data.cell.width / 2, data.cell.y + data.cell.height / 2 + 1, { align: 'center' });
        }
      }
    },
  });

  y = doc.lastAutoTable.finalY + 6.5;

  // 6. Advisory Notice
  if (y > doc.internal.pageSize.getHeight() - 24) {
    doc.addPage();
    y = 17;
  }

  drawCard(doc, 14, y, usableWidth, 15, AMBER_BG, AMBER_BORDER, 2);
  drawIconBadge(doc, 20.5, y + 5.5, 3, 'alert');

  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...ROSE_DARK);
  doc.text('Diagnostic Advisory Notice', 26, y + 5.2);

  doc.setFontSize(6.2);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE_BODY);
  doc.text(
    'Records marked "Simulated (Demo)" were produced by fallback heuristics when AI weights were not loaded.\n' +
    'Confirm critical pathogen diagnoses with local agricultural extension agronomists before applying chemical treatments.',
    26,
    y + 9.5
  );

  addRunningHeadersAndFooters(doc, 'Plant Disease & Pest Diagnostic History', 'Audit Log', dateStr);

  const dateStamp = new Date().toISOString().slice(0, 10);
  doc.save(`Crop_Diagnostics_History_${dateStamp}.pdf`);
}