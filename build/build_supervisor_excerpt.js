const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, Table, TableRow, TableCell, WidthType, BorderStyle,
  VerticalAlign, ShadingType, SectionType, Tab, TabStopType, LeaderType,
} = require("docx");

const ROOT = "C:/Users/abdul/CST4990-dissertation";

const CM = 566.929;
const MARGIN = Math.round(2 * CM);
const PAGE_W = 11906;
const PAGE_H = 16838;
const CONTENT_W = PAGE_W - 2 * MARGIN;

const FONT = "Calibri";
const SZ_BODY = 24;
const SZ_H1 = 32;
const SZ_H2 = 26;
const LINE_1_5 = { line: 360, lineRule: "auto" };

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
    alignment: AlignmentType.LEFT,
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

function splitRow(r) {
  return r.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

function parseTableBlock(lines, startIdx) {
  let i = startIdx;
  const rows = [];
  while (i < lines.length && lines[i].trim().startsWith("|")) { rows.push(lines[i]); i++; }
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
        children: inlineRuns(text, { size: 20, bold: !!header }),
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

function mdToElements(mdPath) {
  const raw = fs.readFileSync(mdPath, "utf8");
  const lines = raw.split(/\r?\n/);
  const elements = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === "") { i++; continue; }
    if (/^\*Draft\./.test(line.trim())) {
      while (i < lines.length && lines[i].trim() !== "") { i++; }
      continue;
    }
    if (line.startsWith("## ")) { elements.push(h2(line.replace(/^## /, "").trim())); i++; continue; }
    if (line.startsWith("# ")) { elements.push(h1(line.replace(/^# /, "").trim())); i++; continue; }
    if (line.trim().startsWith("|")) {
      const { header, dataRows, nextIdx } = parseTableBlock(lines, i);
      elements.push(buildTable(header, dataRows));
      elements.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
      i = nextIdx; continue;
    }
    function isNewBlock(l) {
      const t = l.trim();
      return t === "" || l.startsWith("#") || t.startsWith("|") || /^\d+\.\s/.test(t) || /^[-*]\s/.test(t);
    }
    if (/^\d+\.\s/.test(line.trim())) {
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
        const numMatch = lines[i].trim().match(/^(\d+)\.\s(.*)$/);
        const itemLines = [numMatch[2]]; i++;
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
        const itemLines = [lines[i].trim().replace(/^[-*]\s/, "")]; i++;
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
    const paraLines = [line]; i++;
    while (i < lines.length && lines[i].trim() !== "" && !lines[i].startsWith("#") &&
           !lines[i].trim().startsWith("|") && !/^\d+\.\s/.test(lines[i].trim()) && !/^[-*]\s/.test(lines[i].trim())) {
      paraLines.push(lines[i]); i++;
    }
    elements.push(para(paraLines.join(" ").replace(/\s+/g, " ").trim()));
  }
  return elements;
}

// ---------------------------------------------------------------------------
// Cover note + full dissertation ToC (static — this excerpt has only Ch1's
// content, so a live TOC field would show nothing else) + full Chapter 1.
// ---------------------------------------------------------------------------
const FULL_TOC = [
  ["Chapter 1", "Introduction", ["1.1 Background and motivation", "1.2 Problem definition", "1.3 Aim and objectives", "1.4 Research questions", "1.5 Scope and limitations", "1.6 Dissertation structure"]],
  ["Chapter 2", "Literature Review", ["2.1 Physical side-channel analysis", "2.2 Noise and masking countermeasures", "2.3 Side channels in virtualised co-tenancy", "2.4 Machine learning as the attacker model", "2.5 Kernel packet filtering and ACL cost", "2.6 Research gap"]],
  ["Chapter 3", "Methodology / Research Design", ["3.1 Research approach", "3.2 Threat model", "3.3 Experimental environment", "3.4 Firewall configurations", "3.5 Measurement design", "3.6 The defence", "3.7 Experimental controls", "3.8 Analysis procedure"]],
  ["Chapter 4", "Results & Analysis", ["4.1 Dataset summary", "4.2 Signal characterisation", "4.3 Attacker accuracy \u2014 defence inactive", "4.4 Attacker accuracy \u2014 defence active", "4.5 Observation-budget curve", "4.6 Cost of the defence", "4.7 Validity checks"]],
  ["Chapter 5", "Discussion & Critical Evaluation", ["5.1 Answering RQ1", "5.2 Answering RQ2", "5.3 Relation to prior work", "5.4 Limitations", "5.5 Recommendations", "5.6 Reflection"]],
  ["Chapter 6", "Conclusions & Further Work", ["6.1 Conclusions", "6.2 Contributions", "6.3 Further work"]],
  ["", "References", []],
  ["", "Appendices A\u2013E (project outline, risk assessment, source code manifest, run metadata, ethics screening)", []],
];

function coverNote() {
  return [
    h1("CST4990 Dissertation \u2014 Excerpt for Supervisor Review"),
    para("Sarfraz Masood, M01085839 \u2014 MSc Cyber Security and Emerging Threats \u2014 Supervisor: David Neilson"),
    para("This excerpt contains the full Table of Contents of the dissertation, followed by Chapter 1 (Introduction) in full \u2014 the two items the handbook (\u00a710.2) notes a supervisor can review in detail. The complete draft (all six chapters, references, appendices) is available on request."),
  ];
}

function tocPages() {
  const els = [h1("Table of Contents")];
  FULL_TOC.forEach(([num, title, subs]) => {
    const label = num ? `${num}: ${title}` : title;
    els.push(new Paragraph({
      spacing: { before: 160, after: 60 },
      tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W, leader: LeaderType.DOT }],
      children: [run(label, { bold: true })],
    }));
    subs.forEach((s) => {
      els.push(new Paragraph({
        indent: { left: 360 },
        spacing: { after: 40 },
        children: [run(s, { size: 22 })],
      }));
    });
  });
  return els;
}

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: SZ_BODY } } } },
  sections: [
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } },
      },
      children: [
        ...coverNote(), pageBreak(),
        ...tocPages(), pageBreak(),
        ...mdToElements(path.join(ROOT, "CH1_INTRODUCTION.md")),
      ],
    },
  ],
});

const outPath = path.join(ROOT, "CST4990_Excerpt_ToC_Chapter1.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log("Wrote", outPath, buf.length, "bytes");
});
