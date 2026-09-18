const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, Table, TableRow, TableCell, WidthType, BorderStyle,
  TableOfContents, Footer, PageNumber, NumberFormat, ImageRun,
  VerticalAlign, ShadingType, SectionType,
  Tab, TabStopType, LeaderType,
} = require("docx");

const ROOT = "C:/Users/abdul/CST4990-dissertation";
const LOGO_PATH = path.join(__dirname, "assets/mdx_logo.jpg");

// ---------------------------------------------------------------------------
// Layout constants — handbook rules (DISSERTATION_PLAN.md sec. 1) override
// the template's own Arial/Times/double-spacing/full-justify advice.
// ---------------------------------------------------------------------------
const CM = 566.929;
const MARGIN = Math.round(2 * CM);
const PAGE_W = 11906; // A4
const PAGE_H = 16838;
const CONTENT_W = PAGE_W - 2 * MARGIN;

const FONT = "Calibri";
const SZ_BODY = 24; // 12pt
const SZ_H1 = 32; // 16pt
const SZ_H2 = 26; // 13pt
const SZ_TABLE = 20; // 10pt
const LINE_1_5 = { line: 360, lineRule: "auto" };

const STUDENT_NAME = "Sarfraz Masood";
const STUDENT_ID = "M01085839";
const PROGRAMME = "MSc Cyber Security and Emerging Threats";
const SUPERVISOR = "David Neilson";
const MODULE = "CST4990 — Postgraduate Individual Project";
const TITLE = "An Empirical Evaluation of Algorithmic Power-Noise Injection: Utilizing Machine Learning to Defend Enterprise Firewall Kernels Against Side-Channel Energy Analysis Attacks";
const SUBMISSION_MONTH_YEAR = "September 2026";

function run(text, opts = {}) {
  return new TextRun(Object.assign({ text, font: FONT, size: SZ_BODY }, opts));
}

function inlineRuns(text, base = {}) {
  const runs = [];
  const re = /(\*\*(.+?)\*\*|`(.+?)`|\*(.+?)\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) runs.push(run(text.slice(last, m.index), base));
    if (m[2] !== undefined) runs.push(run(m[2], Object.assign({}, base, { bold: true })));
    else if (m[3] !== undefined) runs.push(run(m[3], Object.assign({}, base, { font: "Consolas" })));
    else if (m[4] !== undefined) runs.push(run(m[4], Object.assign({}, base, { italics: true })));
    last = re.lastIndex;
  }
  if (last < text.length) runs.push(run(text.slice(last), base));
  if (runs.length === 0) runs.push(run(text, base));
  return runs;
}

function para(text, opts = {}) {
  return new Paragraph(Object.assign({
    children: inlineRuns(text),
    alignment: AlignmentType.JUSTIFIED,
    spacing: Object.assign({ after: 160 }, LINE_1_5),
  }, opts));
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.CENTER,
    spacing: Object.assign({ before: 240, after: 240 }, LINE_1_5),
    children: [new TextRun({ text, font: FONT, size: SZ_H1, bold: true, color: "000000" })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    alignment: AlignmentType.LEFT,
    spacing: Object.assign({ before: 200, after: 120 }, LINE_1_5),
    children: [new TextRun({ text, font: FONT, size: SZ_H2, bold: true, color: "000000" })],
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

// ---------------------------------------------------------------------------
// Table parsing / rendering
// ---------------------------------------------------------------------------
function splitRow(r) {
  return r.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

function parseTableBlock(lines, startIdx) {
  let i = startIdx;
  const rows = [];
  while (i < lines.length && lines[i].trim().startsWith("|")) {
    rows.push(lines[i]);
    i++;
  }
  const header = splitRow(rows[0]);
  const dataRows = rows.slice(2).map(splitRow);
  return { header, dataRows, nextIdx: i };
}

function buildTable(header, dataRows) {
  const cols = header.length;
  const colWidth = Math.floor(CONTENT_W / cols);
  const borders = {
    top: { style: BorderStyle.SINGLE, size: 2, color: "999999" },
    bottom: { style: BorderStyle.SINGLE, size: 2, color: "999999" },
    left: { style: BorderStyle.SINGLE, size: 2, color: "999999" },
    right: { style: BorderStyle.SINGLE, size: 2, color: "999999" },
    insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
    insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  };
  function cell(text, header) {
    return new TableCell({
      width: { size: colWidth, type: WidthType.DXA },
      shading: header ? { type: ShadingType.CLEAR, fill: "D9D9D9" } : undefined,
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 60, bottom: 60, left: 80, right: 80 },
      children: [new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { line: 276, lineRule: "auto" },
        children: inlineRuns(text, { size: SZ_TABLE, bold: !!header }),
      })],
    });
  }
  const headerRow = new TableRow({ tableHeader: true, children: header.map((h) => cell(h, true)) });
  const bodyRows = dataRows.map((r) => new TableRow({ children: r.map((c) => cell(c, false)) }));
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: Array(cols).fill(colWidth),
    borders,
    rows: [headerRow, ...bodyRows],
  });
}

// ---------------------------------------------------------------------------
// Generic markdown -> docx element converter
// ---------------------------------------------------------------------------
function mdToElements(mdPath, { pageBreakBeforeH1 = false, chapterNum = null, figures = {} } = {}) {
  const raw = fs.readFileSync(mdPath, "utf8");
  const lines = raw.split(/\r?\n/);
  const elements = [];
  let i = 0;
  let sawFirstH1 = false;
  let figureCounter = 0;
  let inCode = false;
  let codeLines = [];

  function flushCode() {
    if (codeLines.length) {
      elements.push(new Paragraph({
        shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
        spacing: { after: 160, line: 240, lineRule: "auto" },
        children: codeLines.flatMap((l, idx) => idx === 0 ? [run(l, { font: "Consolas", size: 18 })] : [new TextRun({ break: 1, font: "Consolas", size: 18, text: l })]),
      }));
      codeLines = [];
    }
  }

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim().startsWith("```")) {
      if (inCode) { flushCode(); inCode = false; }
      else { inCode = true; }
      i++; continue;
    }
    if (inCode) { codeLines.push(line); i++; continue; }

    if (line.trim() === "") { i++; continue; }
    if (/^\*Draft\./.test(line.trim())) {
      while (i < lines.length && lines[i].trim() !== "") { i++; }
      continue;
    }
    const figMatch = line.trim().match(/^\[\[FIGURE:(\w+)\]\]$/);
    if (figMatch) {
      const f = figures[figMatch[1]];
      if (f) {
        figureCounter++;
        const data = fs.readFileSync(f.path);
        const targetW = 480;
        const targetH = Math.round(targetW * (f.h / f.w));
        elements.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 200, after: 80 },
          children: [new ImageRun({ type: "png", data, transformation: { width: targetW, height: targetH } })],
        }));
        elements.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 240 },
          children: [run(`Figure ${chapterNum}.${figureCounter}. `, { bold: true, size: 20 }), ...inlineRuns(f.caption, { size: 20, italics: true })],
        }));
      }
      i++; continue;
    }

    if (line.startsWith("## ")) {
      elements.push(h2(line.replace(/^## /, "").trim()));
      i++; continue;
    }
    if (line.startsWith("# ")) {
      if (pageBreakBeforeH1 && sawFirstH1) elements.push(pageBreak());
      elements.push(h1(line.replace(/^# /, "").trim()));
      sawFirstH1 = true;
      i++; continue;
    }
    if (line.trim().startsWith("|")) {
      const { header, dataRows, nextIdx } = parseTableBlock(lines, i);
      elements.push(buildTable(header, dataRows));
      elements.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
      i = nextIdx; continue;
    }
    function isNewBlock(l) {
      const t = l.trim();
      return t === "" || l.startsWith("#") || t.startsWith("|") ||
             /^\d+\.\s/.test(t) || /^[-*]\s/.test(t) || t.startsWith("```");
    }

    if (/^\d+\.\s/.test(line.trim())) {
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
        const numMatch = lines[i].trim().match(/^(\d+)\.\s(.*)$/);
        const itemLines = [numMatch[2]];
        i++;
        while (i < lines.length && !isNewBlock(lines[i])) { itemLines.push(lines[i]); i++; }
        const itemText = itemLines.join(" ").replace(/\s+/g, " ").trim();
        elements.push(new Paragraph({
          indent: { left: 360 },
          spacing: Object.assign({ after: 100 }, LINE_1_5),
          children: [run(`${numMatch[1]}. `, {}), ...inlineRuns(itemText)],
        }));
      }
      continue;
    }
    if (/^[-*]\s/.test(line.trim())) {
      while (i < lines.length && /^[-*]\s/.test(lines[i].trim())) {
        const itemLines = [lines[i].trim().replace(/^[-*]\s/, "")];
        i++;
        while (i < lines.length && !isNewBlock(lines[i])) { itemLines.push(lines[i]); i++; }
        const itemText = itemLines.join(" ").replace(/\s+/g, " ").trim();
        elements.push(new Paragraph({
          indent: { left: 360 },
          spacing: Object.assign({ after: 100 }, LINE_1_5),
          children: [run("\u2022 ", {}), ...inlineRuns(itemText)],
        }));
      }
      continue;
    }

    const paraLines = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== "" &&
           !lines[i].startsWith("#") && !lines[i].trim().startsWith("|") &&
           !/^\d+\.\s/.test(lines[i].trim()) && !/^[-*]\s/.test(lines[i].trim()) &&
           !lines[i].trim().startsWith("```")) {
      paraLines.push(lines[i]);
      i++;
    }
    const paraText = paraLines.join(" ").replace(/\s+/g, " ").trim();
    elements.push(para(paraText));
  }
  return elements;
}

function withTableCaptions(elements, chapterNum, captions, opts = {}) {
  const skip = new Set(opts.skip || []);
  const out = [];
  let tableIdx = 0;
  let n = 0;
  for (const el of elements) {
    if (el instanceof Table) {
      if (!skip.has(tableIdx)) {
        const cap = captions[n];
        n++;
        if (cap) {
          out.push(new Paragraph({
            spacing: { before: 160, after: 60 },
            children: [run(`Table ${chapterNum}.${n}. `, { bold: true, size: SZ_TABLE }), ...inlineRuns(cap, { size: SZ_TABLE })],
          }));
        }
      }
      tableIdx++;
    }
    out.push(el);
  }
  return out;
}

function wordCount(mdPath) {
  const raw = fs.readFileSync(mdPath, "utf8");
  const rawLines = raw.split(/\r?\n/);
  const keep = [];
  let skipping = false;
  for (const l of rawLines) {
    if (/^\*Draft\./.test(l.trim())) { skipping = true; continue; }
    if (skipping) { if (l.trim() === "") skipping = false; continue; }
    keep.push(l);
  }
  const clean = keep
    .filter((l) => !/^\|[\s:|-]+\|$/.test(l.trim())) // markdown table separator rows
    .map((l) => l.replace(/^#+\s*/, "").replace(/\|/g, " "))
    .join(" ");
  return clean.split(/\s+/).filter(Boolean).length;
}

// ---------------------------------------------------------------------------
// Figures (Chapter 4)
// ---------------------------------------------------------------------------
const FIG_DIR = path.join(ROOT, "results/run04/figures");
// Order below = encounter order in CH4_RESULTS.md's [[FIGURE:key]] markers,
// which is also the Figure 4.N numbering order (do not reorder without also
// reordering the markers in the markdown).
const FIGURES_CH4 = {
  fig1: { path: path.join(FIG_DIR, "fig1_latency_by_config.png"), w: 1890, h: 900,
    caption: "Distribution of per-trial median send latency for each firewall configuration, with the noise-injection defence inactive and active. Separation between configurations is the side channel; the upward shift under the defence is the latency cost paid by legitimate traffic." },
  fig2: { path: path.join(FIG_DIR, "fig2_accuracy_and_controls.png"), w: 1890, h: 930,
    caption: "Attacker balanced accuracy by condition and model. The shuffled-label control refits the identical pipeline on permuted labels and sits at the chance baseline, evidence that the real scores reflect a side channel rather than leakage in the cross-validation." },
  fig4rf: { path: path.join(FIG_DIR, "fig4_confusion_randomforest.png"), w: 1890, h: 930,
    caption: "Row-normalised confusion matrix for the random forest attacker. Rows sum to one, so the diagonal is per-class recall and off-diagonal mass shows which configurations the attacker cannot separate." },
  fig4lr: { path: path.join(FIG_DIR, "fig4_confusion_logreg.png"), w: 1890, h: 930,
    caption: "Row-normalised confusion matrix for the logistic regression attacker. As with Figure 4.3, off-diagonal mass concentrates on the accept_deep/drop_deep pair rather than on the shallow configurations." },
  fig5: { path: path.join(FIG_DIR, "fig5_feature_importance.png"), w: 1890, h: 960,
    caption: "Random forest feature importances, ordered by the undefended condition. Which statistic dominates indicates what the channel is: central-tendency features indicate a deterministic cost difference, while spread or tail features indicate the leak is carried by variability." },
  fig3: { path: path.join(FIG_DIR, "fig3_sweep_curve.png"), w: 1890, h: 1020,
    caption: "Attacker balanced accuracy as a function of observation budget, four-class axis. Both conditions clear the half-way target at the smallest budget tested, so the trace-multiplication factor degenerates to 1.0 and the axis is reported as saturated rather than informative." },
  fig3b: { path: path.join(FIG_DIR, "fig3b_sweep_curve_verdict.png"), w: 1890, h: 1020,
    caption: "Attacker balanced accuracy against observation budget on the verdict axis (accept vs drop within the deep configurations, chance 0.5), run04. Separation between the curves is the cost the defence imposes; convergence at the largest budgets is the attacker recovering — the outcome Chari et al. (1999) predict for noise countermeasures." },
};
const FIGURES_CH3 = {
  arch: { path: path.join(__dirname, "assets/ch3_architecture.png"), w: 1871, h: 1020,
    caption: "Experimental architecture: the victim (collect.py) and the noise injector (noise.py) run inside the same Lubuntu guest, contending for CPU when co-located on the same core; firewall.py applies one of four configurations per trial, and the resulting traces flow through the analysis pipeline (features.py through figures.py)." },
};

// ---------------------------------------------------------------------------
// Front matter
// ---------------------------------------------------------------------------
function logoImage(width = 180) {
  const data = fs.readFileSync(LOGO_PATH);
  const height = Math.round(width * (54 / 132));
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
    children: [new ImageRun({ type: "jpg", data, transformation: { width, height } })],
  });
}

function titlePageChildren() {
  return [
    logoImage(),
    new Paragraph({ spacing: { after: 480 } }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 480, line: 360, lineRule: "auto" },
      children: [new TextRun({ text: TITLE.toUpperCase(), font: FONT, size: 28, bold: true })],
    }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [run("By", { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 }, children: [run(STUDENT_NAME, { size: 24, bold: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run("A DISSERTATION", { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run("Submitted to", { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run("MIDDLESEX UNIVERSITY", { size: 24, bold: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 }, children: [run("Computer Science Department", { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run("in partial fulfilment of the requirements for the degree of", { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run("MASTER OF SCIENCE", { size: 24, bold: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run(PROGRAMME, { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 }, children: [run("by Examination and Dissertation", { size: 24 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run(SUBMISSION_MONTH_YEAR, { size: 24 })] }),
  ];
}

function coversheetChildren(declaredWordCount) {
  const rows = [
    ["Student ID Number", STUDENT_ID],
    ["Student Name", STUDENT_NAME],
    ["Module Code", MODULE],
    ["Programme of Study", PROGRAMME],
    ["Supervisor", SUPERVISOR],
    ["Title", TITLE],
    ["Declared Word Count", `${declaredWordCount.toLocaleString()} (main body, Chapters 1\u20136; excludes front matter, references and appendices)`],
  ];
  const colWidth1 = Math.floor(CONTENT_W * 0.28);
  const colWidth2 = CONTENT_W - colWidth1;
  const tableRows = rows.map(([label, value]) => new TableRow({
    children: [
      new TableCell({
        width: { size: colWidth1, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: "D9D9D9" },
        margins: { top: 80, bottom: 80, left: 100, right: 100 },
        children: [new Paragraph({ children: [run(label, { bold: true })] })],
      }),
      new TableCell({
        width: { size: colWidth2, type: WidthType.DXA },
        margins: { top: 80, bottom: 80, left: 100, right: 100 },
        children: [new Paragraph({ children: inlineRuns(value) })],
      }),
    ],
  }));
  const table = new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [colWidth1, colWidth2],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "999999" },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "999999" },
    },
    rows: tableRows,
  });
  return [
    logoImage(140),
    h1("Dissertation/Project Coversheet"),
    table,
  ];
}

function declarationChildren() {
  const body = [
    "I hereby certify that this dissertation constitutes my own product, that where the language of others is set forth, quotation marks so indicate, and that appropriate credit is given where I have used the language, ideas, expressions or writings of another.",
    "I confirm that I have not copied material from another source nor committed plagiarism nor commissioned all or part of the work (including unacceptable proof-reading) nor fabricated, falsified or embellished data when completing the attached piece of work.",
    "I declare that the dissertation describes original work that has not previously been presented for the award of any other degree of any institution.",
  ];
  const elements = [h1("Declaration")];
  body.forEach((t) => elements.push(para(t)));
  elements.push(new Paragraph({ spacing: { before: 480 }, children: [run("Signed,")] }));
  elements.push(new Paragraph({ spacing: { before: 240 }, children: [run(STUDENT_NAME, { bold: true })] }));
  elements.push(new Paragraph({ children: [run("Date: 7 September 2026")] }));
  return elements;
}

function acknowledgementsChildren() {
  const elements = [h1("Acknowledgements")];
  elements.push(para(
    `I would like to thank my supervisor, ${SUPERVISOR}, for his guidance throughout the design and execution of ` +
    "this project. I am also grateful to the Middlesex University Computer Science Department for the resources " +
    "and support that made the experimental work possible, and to my family and friends for their patience and " +
    "encouragement over the course of this project."
  ));
  return elements;
}

function tocListsChildren() {
  const tableEntries = [
    ["Table 3.1", "Firewall configurations distinguished by verdict and rule-chain depth", 9],
    ["Table 4.1", "Median per-packet latency by configuration", 13],
    ["Table 4.2", "Attacker balanced accuracy, defence inactive", 13],
    ["Table 4.3", "Attacker balanced accuracy, defence active, and single-shot reduction", 14],
    ["Table 4.4", "Per-packet latency quantile inflation, run04 deep configurations", 16],
    ["Table 4.5", "Observation-budget trace-multiplication factor by run", 17],
    ["Table 4.6", "run04 verdict-axis sweep curve, accuracy by observation budget", 17],
    ["Table 4.7", "Cost of the defence: latency and CPU overhead by run", 17],
  ];
  const figureEntries = [
    ["Figure 3.1", FIGURES_CH3.arch.caption.split(/\. /)[0] + ".", 10],
    ["Figure 4.1", FIGURES_CH4.fig1.caption.split(/\. /)[0] + ".", 14],
    ["Figure 4.2", FIGURES_CH4.fig2.caption.split(/\. /)[0] + ".", 15],
    ["Figure 4.3", FIGURES_CH4.fig4rf.caption.split(/\. /)[0] + ".", 15],
    ["Figure 4.4", FIGURES_CH4.fig4lr.caption.split(/\. /)[0] + ".", 15],
    ["Figure 4.5", FIGURES_CH4.fig5.caption.split(/\. /)[0] + ".", 16],
    ["Figure 4.6", FIGURES_CH4.fig3.caption.split(/\. /)[0] + ".", 18],
    ["Figure 4.7", FIGURES_CH4.fig3b.caption.split(/\. /)[0] + ".", 19],
  ];

  function listBlock(title, entries) {
    const els = [h1(title)];
    entries.forEach(([num, cap, pg]) => {
      els.push(new Paragraph({
        spacing: { after: 80 },
        tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W, leader: LeaderType.DOT }],
        children: [
          run(`${num}   `, { bold: true }), ...inlineRuns(cap),
          new TextRun({ children: [new Tab(), String(pg)], font: FONT, size: SZ_BODY }),
        ],
      }));
    });
    els.push(para("(Page numbers reflect this draft's current pagination; re-check them if content is added or removed before submitting.)"));
    return els;
  }

  return [
    h1("Table of Contents"),
    new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
    pageBreak(),
    ...listBlock("List of Tables", tableEntries),
    pageBreak(),
    ...listBlock("List of Figures", figureEntries),
  ];
}

// ---------------------------------------------------------------------------
// References (hardcoded — see REFERENCES.md for verification notes)
// ---------------------------------------------------------------------------
const REFERENCES = [
  "Chari, S., Jutla, C.S., Rao, J.R. and Rohatgi, P. (1999) 'Towards sound approaches to counteract power-analysis attacks', in Wiener, M. (ed.) Advances in Cryptology \u2014 CRYPTO '99. Lecture Notes in Computer Science 1666. Berlin: Springer, pp. 398\u2013412.",
  "Genkin, D., Pachmanov, L., Pipman, I. and Tromer, E. (2015) 'Stealing keys from PCs using a radio: cheap electromagnetic attacks on windowed exponentiation', in Cryptographic Hardware and Embedded Systems (CHES 2015). Lecture Notes in Computer Science. Berlin: Springer, pp. 207\u2013228.",
  "Genkin, D., Pachmanov, L., Pipman, I., Shamir, A. and Tromer, E. (2016) 'Physical key extraction attacks on PCs', Communications of the ACM, 59(6), pp. 70\u201379.",
  "Hettwer, B., Gehrer, S. and G\u00fcneysu, T. (2020) 'Applications of machine learning techniques in side-channel attacks: a survey', Journal of Cryptographic Engineering, 10(2), pp. 135\u2013162. doi: 10.1007/s13389-019-00212-8.",
  "Kocher, P., Jaffe, J. and Jun, B. (1999) 'Differential power analysis', in Wiener, M. (ed.) Advances in Cryptology \u2014 CRYPTO '99, 19th Annual International Cryptology Conference. Lecture Notes in Computer Science 1666. Berlin: Springer, pp. 388\u2013397.",
  "Mangard, S. (2004) 'Hardware countermeasures against DPA \u2014 a statistical analysis of their effectiveness', in Okamoto, T. (ed.) Topics in Cryptology \u2014 CT-RSA 2004. Lecture Notes in Computer Science 2964. Berlin: Springer, pp. 222\u2013235.",
  "Masure, L., Dumas, C. and Prouff, E. (2020) 'A comprehensive study of deep learning for side-channel analysis', IACR Transactions on Cryptographic Hardware and Embedded Systems, 2020(1), pp. 348\u2013375. doi: 10.13154/tches.v2020.i1.348-375.",
  "Niemann, R., Pfingst, U. and G\u00f6bel, R. (2015) Performance evaluation of netfilter: a study on the performance loss when using netfilter as a firewall. arXiv:1502.05487 [cs.NI].",
  "Ristenpart, T., Tromer, E., Shacham, H. and Savage, S. (2009) 'Hey, you, get off of my cloud: exploring information leakage in third-party compute clouds', in Proceedings of the 16th ACM Conference on Computer and Communications Security (CCS '09). New York: ACM, pp. 199\u2013212. doi: 10.1145/1653662.1653687.",
  "Rose, S., Borchert, O., Mitchell, S. and Connelly, S. (2020) Zero trust architecture. NIST Special Publication 800-207. Gaithersburg, MD: National Institute of Standards and Technology. doi: 10.6028/NIST.SP.800-207.",
  "Zhang, Y., Juels, A., Oprea, A. and Reiter, M.K. (2011) 'HomeAlone: co-residency detection in the cloud via side-channel analysis', in 2011 IEEE Symposium on Security and Privacy. Los Alamitos, CA: IEEE, pp. 313\u2013328. doi: 10.1109/SP.2011.31.",
  "Zhou, B., Gupta, A., Jahanshahi, R., Egele, M. and Joshi, A. (2018) 'Hardware performance counters can detect malware: myth or fact?', in Proceedings of the 2018 ACM Asia Conference on Computer and Communications Security (ASIACCS '18). New York: ACM, pp. 457\u2013468. doi: 10.1145/3196494.3196515.",
];

function referencesChildren() {
  const els = [h1("References")];
  REFERENCES.forEach((r) => {
    els.push(new Paragraph({
      indent: { left: 720, hanging: 720 },
      spacing: Object.assign({ after: 200 }, LINE_1_5),
      children: inlineRuns(r),
    }));
  });
  return els;
}

// ---------------------------------------------------------------------------
// Assemble
// ---------------------------------------------------------------------------
function footerWithPageNumber(format, start) {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: SZ_BODY })],
    })],
  });
}

const chWordTotal = ["CH1_INTRODUCTION.md", "CH2_LITERATURE_REVIEW.md", "CH3_METHODOLOGY.md",
  "CH4_RESULTS.md", "CH5_DISCUSSION.md", "CH6_CONCLUSIONS.md"]
  .map((f) => wordCount(path.join(ROOT, f)))
  .reduce((a, b) => a + b, 0);

console.log("Declared word count (Ch1-6, raw file word count):", chWordTotal);

const abstractEls = mdToElements(path.join(ROOT, "ABSTRACT.md"));
const ch1 = mdToElements(path.join(ROOT, "CH1_INTRODUCTION.md"));
const ch2 = mdToElements(path.join(ROOT, "CH2_LITERATURE_REVIEW.md"));
const ch3 = withTableCaptions(
  mdToElements(path.join(ROOT, "CH3_METHODOLOGY.md"), { chapterNum: 3, figures: FIGURES_CH3 }), 3,
  ["Firewall configurations distinguished by verdict and rule-chain depth"]
);
const ch4 = withTableCaptions(
  mdToElements(path.join(ROOT, "CH4_RESULTS.md"), { chapterNum: 4, figures: FIGURES_CH4 }), 4,
  [
    "Median per-packet latency by configuration",
    "Attacker balanced accuracy, defence inactive",
    "Attacker balanced accuracy, defence active, and single-shot reduction",
    "Per-packet latency quantile inflation, run04 deep configurations",
    "Observation-budget trace-multiplication factor by run",
    "run04 verdict-axis sweep curve, accuracy by observation budget",
    "Cost of the defence: latency and CPU overhead by run",
  ],
  // Table index 0 (the run ID / mode / placement lookup table under 4.1
  // Dataset summary) is referenced only as "this table" in the prose and was
  // never meant to carry a number — skip it so the 7 captions above line up
  // with the 7 tables the List of Tables actually numbers (4.1-4.7).
  { skip: [0] }
);
const ch5 = mdToElements(path.join(ROOT, "CH5_DISCUSSION.md"));
const ch6 = mdToElements(path.join(ROOT, "CH6_CONCLUSIONS.md"));
const appendices = mdToElements(path.join(ROOT, "APPENDICES.md"), { pageBreakBeforeH1: true });

const doc = new Document({
  features: { updateFields: true },
  styles: {
    default: {
      document: { run: { font: FONT, size: SZ_BODY } },
    },
  },
  sections: [
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } },
      },
      children: [
        ...titlePageChildren(), pageBreak(),
        ...coversheetChildren(chWordTotal), pageBreak(),
        ...abstractEls, pageBreak(),
        ...declarationChildren(), pageBreak(),
        ...acknowledgementsChildren(),
      ],
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
          pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN },
        },
      },
      footers: { default: footerWithPageNumber() },
      children: tocListsChildren(),
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
          pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL },
        },
      },
      footers: { default: footerWithPageNumber() },
      children: [
        ...ch1, pageBreak(),
        ...ch2, pageBreak(),
        ...ch3, pageBreak(),
        ...ch4, pageBreak(),
        ...ch5, pageBreak(),
        ...ch6, pageBreak(),
        ...referencesChildren(), pageBreak(),
        ...appendices,
      ],
    },
  ],
});

const outPath = path.join(ROOT, process.env.OUT_NAME || "CST4990_Dissertation_Masood_v2.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log("Wrote", outPath, buf.length, "bytes");
});
