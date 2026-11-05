/*
 Step 23 - Turn one of the findings reports (Markdown) into a Word document (.docx), with the charts embedded.

 It understands the small part of Markdown the reports use: headings (#, ##, ###), paragraphs, bullet and numbered lists, tables, images ![text](file.png),
 and **bold**, *italic* and `code` inside text. Images are looked up in the folder of the Markdown file.

 How to run (needs the "docx" package from npm; from the project folder):
     NODE_PATH=<folder with node_modules> node scripts/23_markdown_to_docx.js reports/findings_summary_steps_1_5.md reports/findings_summary_steps_1_5.docx compact
*/
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, ImageRun, AlignmentType, LevelFormat, Footer, PageNumber } = require("docx");

const [input, output, mode] = process.argv.slice(2);   // mode "compact" = smaller charts (for the short report)
const baseDir = path.dirname(input);
const FONT = "Arial";
const PAGE_WIDTH = 11906, PAGE_HEIGHT = 16838, MARGIN = 1134;   // A4, margins 2 cm
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN;                   // in DXA (1/20 point)

// --- inline formatting: **bold**, *italic*, `code` ---
function runs(text, base = {}) {
  const out = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g;
  let last = 0, m;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Courier New", ...base, size: (base.size || 21) - 2 }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}

// --- PNG size (width and height are in bytes 16-23 of the file) ---
function pngSize(buffer) { return { w: buffer.readUInt32BE(16), h: buffer.readUInt32BE(20) }; }

function image(alt, file) {
  const buffer = fs.readFileSync(path.join(baseDir, file));
  const { w, h } = pngSize(buffer);
  const maxW = mode === "compact" ? 520 : 600, maxH = mode === "compact" ? 260 : 640;                                  // in pixels at 96 dpi: 6.25 inch wide at most
  const scale = Math.min(maxW / w, maxH / h);
  return [new Paragraph({ children: [new ImageRun({ type: "png", data: buffer, transformation: { width: Math.round(w * scale), height: Math.round(h * scale) }, altText: { title: alt, description: alt, name: file } })],
                          spacing: { before: 120, after: 60 }, keepNext: true }),
          new Paragraph({ children: [new TextRun({ text: alt, italics: true, size: 18, color: "52514E", font: FONT })], spacing: { after: 200 } })];
}

// --- tables ---
function table(lines) {
  const rows = lines.filter((l, i) => i !== 1).map(l => l.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim()));
  const n = rows[0].length;
  const size = n > 8 ? 14 : n > 5 ? 16 : 18;                     // half-points
  // column widths from the longest text in each column (bounded), then scaled to the page width
  const raw = rows[0].map((_, c) => Math.min(40, Math.max(6, ...rows.map(r => (r[c] || "").length))));
  const total = raw.reduce((a, b) => a + b, 0);
  const widths = raw.map(v => Math.floor(CONTENT_WIDTH * v / total));
  widths[widths.length - 1] += CONTENT_WIDTH - widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "C3C2B7" };
  const borders = { top: border, bottom: border, left: border, right: border };
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({ tableHeader: ri === 0, cantSplit: true,
      children: r.map((cell, ci) => new TableCell({ borders, width: { size: widths[ci], type: WidthType.DXA }, margins: { top: 40, bottom: 40, left: 80, right: 80 },
        shading: ri === 0 ? { fill: "E8F0FB", type: ShadingType.CLEAR, color: "auto" } : undefined,
        children: [new Paragraph({ children: runs(cell, { size, bold: ri === 0 }) })] })) })) });
}

// --- the document ---
const children = [];
const lines = fs.readFileSync(input, "utf-8").split("\n");
let i = 0;
while (i < lines.length) {
  const line = lines[i];
  if (!line.trim()) { i++; continue; }
  let m;
  if ((m = line.match(/^(#{1,3}) (.*)$/))) {
    const level = m[1].length;
    children.push(new Paragraph({ heading: [HeadingLevel.TITLE, HeadingLevel.HEADING_1, HeadingLevel.HEADING_2][level - 1] ?? HeadingLevel.HEADING_2, children: [new TextRun({ text: m[2].replace(/\*\*/g, ""), font: FONT })] }));
    i++;
  } else if ((m = line.match(/^!\[(.*)\]\((.*)\)$/))) {
    children.push(...image(m[1], m[2])); i++;
  } else if (line.startsWith("|")) {
    const block = [];
    while (i < lines.length && lines[i].startsWith("|")) block.push(lines[i++]);
    children.push(table(block));
    children.push(new Paragraph({ children: [], spacing: { after: 120 } }));
  } else if ((m = line.match(/^- (.*)$/))) {
    children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(m[1], { size: 21 }), spacing: { after: 60 } })); i++;
  } else if ((m = line.match(/^(\d+)\. (.*)$/))) {
    children.push(new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: runs(m[2], { size: 21 }), spacing: { after: 40 } })); i++;
  } else {
    const para = [line];                                          // a paragraph continues until a blank line or a new block
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#{1,3} |!\[|\||- |\d+\. )/.test(lines[i])) para.push(lines[i++]);
    children.push(new Paragraph({ children: runs(para.join(" "), { size: 21 }), spacing: { after: 120, line: 288 } }));
  }
}

const doc = new Document({
  creator: "Syntra Data Science project", title: path.basename(input, ".md"),
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: FONT, size: 40, bold: true, color: "0B0B0B" }, paragraph: { spacing: { before: 0, after: 200 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 30, bold: true, color: "184F95" }, paragraph: { spacing: { before: 360, after: 120 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 25, bold: true, color: "0B0B0B" }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_WIDTH, height: PAGE_HEIGHT }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 16, color: "898781", font: FONT })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(buffer => { fs.writeFileSync(output, buffer); console.log(`Saved ${output}: ${(buffer.length / 1e6).toFixed(2)} MB, ${children.length} blocks`); });
