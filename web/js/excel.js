import * as XLSX from "https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/+esm";
import { formatColombiaDate, formatColombiaTime } from "./attendance.js";

const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

const BLUE = "2F6FED";
const GREEN = "1F5C48";
const YELLOW = "5A4A22";
const DARK = "0B1220";
const PANEL = "141C2E";
const WHITE = "F4F7FB";
const MUTED = "9AA8C1";
const LINE = "2A3650";

const border = {
  top: { style: "thin", color: { rgb: LINE } },
  bottom: { style: "thin", color: { rgb: LINE } },
  left: { style: "thin", color: { rgb: LINE } },
  right: { style: "thin", color: { rgb: LINE } },
};

const titleStyle = {
  font: { bold: true, sz: 18, color: { rgb: WHITE }, name: "Calibri" },
  fill: { patternType: "solid", fgColor: { rgb: DARK } },
  alignment: { vertical: "center" },
};

const sectionStyle = {
  font: { bold: true, sz: 14, color: { rgb: WHITE }, name: "Calibri" },
  fill: { patternType: "solid", fgColor: { rgb: PANEL } },
  alignment: { vertical: "center" },
};

const noteStyle = {
  font: { italic: true, sz: 10, color: { rgb: MUTED }, name: "Calibri" },
  alignment: { wrapText: true, vertical: "center" },
};

function headerStyle(rgb) {
  return {
    font: { bold: true, sz: 11, color: { rgb: WHITE }, name: "Calibri" },
    fill: { patternType: "solid", fgColor: { rgb } },
    alignment: { vertical: "center", wrapText: true },
    border,
  };
}

const cellStyle = {
  font: { sz: 11, color: { rgb: DARK }, name: "Calibri" },
  alignment: { vertical: "center", wrapText: true },
  border,
};

const labelStyle = {
  ...cellStyle,
  font: { bold: true, sz: 11, color: { rgb: DARK }, name: "Calibri" },
  fill: { patternType: "solid", fgColor: { rgb: "EEF2F8" } },
};

function styleCell(ws, r, c, style) {
  const addr = XLSX.utils.encode_cell({ r, c });
  if (!ws[addr]) ws[addr] = { t: "s", v: "" };
  ws[addr].s = style;
}

function styleRange(ws, r1, c1, r2, c2, style) {
  for (let r = r1; r <= r2; r += 1) {
    for (let c = c1; c <= c2; c += 1) styleCell(ws, r, c, style);
  }
}

function sourceLabel(source) {
  if (source === "kiosk") return "kiosco";
  return "celular";
}

export function daySheets(session, present, missing) {
  const classCode = session.class_code || "aula1";
  const day = session.session_date || "";
  const summary = [
    ["Campo", "Valor"],
    ["Clase", classCode],
    ["Fecha", formatColombiaDate(day)],
    ["Hora de activación del QR", formatColombiaTime(session.started_at)],
    ["Personas presentes", present.length],
    ["Personas que faltaron", missing.length],
    ["Total en lista", present.length + missing.length],
  ];
  const presentSheet = [["ID", "Nombre", "Hora de la prueba", "Desde"]];
  for (const student of present) {
    presentSheet.push([
      student.student_id || student.id || "",
      student.full_name || student.name || "",
      formatColombiaTime(student.passed_at),
      sourceLabel(student.source),
    ]);
  }
  const missingSheet = [["ID", "Nombre", "Programa", "Grupo"]];
  for (const student of missing) {
    missingSheet.push([
      student.student_id || student.id || "",
      student.full_name || student.name || "",
      student.program || "",
      student.group_name || student.group || "",
    ]);
  }
  return [
    ["Resumen", summary],
    ["Presentes", presentSheet],
    ["Ausentes", missingSheet],
  ];
}

function presentRows(present) {
  return present.map((student) => [
    student.student_id || student.id || "",
    student.full_name || student.name || "",
    formatColombiaTime(student.passed_at),
    sourceLabel(student.source),
  ]);
}

function missingRows(missing) {
  return missing.map((student) => [
    student.student_id || student.id || "",
    student.full_name || student.name || "",
    student.program || "",
    student.group_name || student.group || "",
  ]);
}

function buildDayBook(session, present, missing) {
  const classCode = session.class_code || "aula1";
  const day = session.session_date || "";
  const book = XLSX.utils.book_new();
  const overview = XLSX.utils.aoa_to_sheet([]);
  overview["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 3 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 3 } },
  ];
  XLSX.utils.sheet_add_aoa(
    overview,
    [
      ["Asistencia del día"],
      ["Misma estructura que la vista previa de la profesora. Editar este archivo no cambia el listado en la web."],
      [],
      ["Resumen"],
    ],
    { origin: "A1" },
  );
  styleRange(overview, 0, 0, 0, 3, titleStyle);
  styleRange(overview, 1, 0, 1, 3, noteStyle);
  styleRange(overview, 3, 0, 3, 3, sectionStyle);
  overview["!rows"] = [{ hpt: 28 }, { hpt: 32 }, { hpt: 12 }, { hpt: 22 }];

  const summaryHeaders = ["Campo", "Valor"];
  const summaryRows = [
    ["Clase", classCode],
    ["Fecha", formatColombiaDate(day)],
    ["Hora de activación del QR", formatColombiaTime(session.started_at)],
    ["Personas presentes", present.length],
    ["Personas que faltaron", missing.length],
    ["Total en lista", present.length + missing.length],
  ];
  XLSX.utils.sheet_add_aoa(overview, [summaryHeaders, ...summaryRows], { origin: "A5" });
  styleRange(overview, 4, 0, 4, 1, headerStyle(BLUE));
  for (let i = 0; i < summaryRows.length; i += 1) {
    styleCell(overview, 5 + i, 0, labelStyle);
    styleCell(overview, 5 + i, 1, cellStyle);
  }

  let row = 13;
  XLSX.utils.sheet_add_aoa(overview, [["Presentes"]], { origin: { r: row, c: 0 } });
  styleRange(overview, row, 0, row, 3, { ...sectionStyle, fill: { patternType: "solid", fgColor: { rgb: GREEN } } });
  row += 1;
  const pHeaders = ["ID", "Nombre", "Hora de la prueba", "Desde"];
  const pData = presentRows(present);
  XLSX.utils.sheet_add_aoa(overview, [pHeaders, ...(pData.length ? pData : [["", "", "", ""]])], {
    origin: { r: row, c: 0 },
  });
  styleRange(overview, row, 0, row, 3, headerStyle(GREEN));
  const presentCount = Math.max(pData.length, 1);
  for (let i = 0; i < presentCount; i += 1) styleRange(overview, row + 1 + i, 0, row + 1 + i, 3, cellStyle);
  row += 1 + presentCount + 1;

  XLSX.utils.sheet_add_aoa(overview, [["Ausentes"]], { origin: { r: row, c: 0 } });
  styleRange(overview, row, 0, row, 3, { ...sectionStyle, fill: { patternType: "solid", fgColor: { rgb: YELLOW } } });
  row += 1;
  const mHeaders = ["ID", "Nombre", "Programa", "Grupo"];
  const mData = missingRows(missing);
  XLSX.utils.sheet_add_aoa(overview, [mHeaders, ...(mData.length ? mData : [["", "", "", ""]])], {
    origin: { r: row, c: 0 },
  });
  styleRange(overview, row, 0, row, 3, headerStyle(YELLOW));
  const missingCount = Math.max(mData.length, 1);
  for (let i = 0; i < missingCount; i += 1) styleRange(overview, row + 1 + i, 0, row + 1 + i, 3, cellStyle);

  overview["!cols"] = [{ wch: 32 }, { wch: 42 }, { wch: 24 }, { wch: 16 }];
  XLSX.utils.book_append_sheet(book, overview, "Asistencia");

  const presentSheet = XLSX.utils.aoa_to_sheet([pHeaders, ...pData]);
  styleRange(presentSheet, 0, 0, 0, 3, headerStyle(GREEN));
  for (let i = 0; i < pData.length; i += 1) styleRange(presentSheet, i + 1, 0, i + 1, 3, cellStyle);
  presentSheet["!cols"] = [{ wch: 16 }, { wch: 42 }, { wch: 24 }, { wch: 14 }];
  if (pData.length) presentSheet["!autofilter"] = { ref: "A1:D" + (pData.length + 1) };
  XLSX.utils.book_append_sheet(book, presentSheet, "Presentes");

  const missingSheet = XLSX.utils.aoa_to_sheet([mHeaders, ...mData]);
  styleRange(missingSheet, 0, 0, 0, 3, headerStyle(YELLOW));
  for (let i = 0; i < mData.length; i += 1) styleRange(missingSheet, i + 1, 0, i + 1, 3, cellStyle);
  missingSheet["!cols"] = [{ wch: 16 }, { wch: 42 }, { wch: 28 }, { wch: 14 }];
  if (mData.length) missingSheet["!autofilter"] = { ref: "A1:D" + (mData.length + 1) };
  XLSX.utils.book_append_sheet(book, missingSheet, "Ausentes");

  return book;
}

function workbookBlob(book) {
  const bytes = XLSX.write(book, { bookType: "xlsx", type: "array" });
  return new Blob([bytes], { type: XLSX_TYPE });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

async function shareBlob(blob, filename, title) {
  const file = new File([blob], filename, { type: XLSX_TYPE });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    await navigator.share({ files: [file], title, text: title });
    return true;
  }
  downloadBlob(blob, filename);
  return false;
}

export function dayWorkbook(session, present, missing) {
  const classCode = session.class_code || "aula1";
  const day = session.session_date || "";
  return {
    filename: `asistencia_${classCode}_${day}.xlsx`,
    blob: workbookBlob(buildDayBook(session, present, missing)),
  };
}

export function universityWorkbook(students) {
  const book = XLSX.utils.book_new();
  const official = [
    ["codigo_estudiante", "nombres", "apellidos", "documento", "programa", "grupo", "correo"],
    ["", "", "", "", "", "", ""],
  ];
  const officialSheet = XLSX.utils.aoa_to_sheet(official);
  styleRange(officialSheet, 0, 0, 0, 6, headerStyle(BLUE));
  styleRange(officialSheet, 1, 0, 1, 6, cellStyle);
  officialSheet["!cols"] = Array(7).fill({ wch: 22 });
  XLSX.utils.book_append_sheet(book, officialSheet, "Listado universidad");

  const how = XLSX.utils.aoa_to_sheet([
    ["Cómo usar esta plantilla"],
    ["Todavía no está el listado oficial de la universidad. Cuando te lo den, pégalo en la hoja Listado universidad."],
    ["No borres la primera fila de títulos."],
    ["La hoja Inscritos kiosco es solo un apoyo mientras llega el listado oficial."],
    ["Editar este Excel no cambia el listado de la web."],
  ]);
  styleCell(how, 0, 0, titleStyle);
  how["!cols"] = [{ wch: 90 }];
  XLSX.utils.book_append_sheet(book, how, "Cómo usarlo");

  const provisional = [["codigo_estudiante", "nombres", "apellidos", "documento", "programa", "grupo", "correo"]];
  for (const student of students || []) {
    const name = String(student.full_name || student.name || "").trim();
    const parts = name.split(" ");
    const first = parts.shift() || "";
    provisional.push([
      student.student_id || student.id || "",
      first,
      parts.join(" "),
      "",
      student.program || "",
      student.group_name || student.group || "",
      "",
    ]);
  }
  if (provisional.length === 1) provisional.push(["", "", "", "", "", "", ""]);
  const provSheet = XLSX.utils.aoa_to_sheet(provisional);
  styleRange(provSheet, 0, 0, 0, 6, headerStyle(GREEN));
  for (let i = 1; i < provisional.length; i += 1) styleRange(provSheet, i, 0, i, 6, cellStyle);
  provSheet["!cols"] = Array(7).fill({ wch: 22 });
  XLSX.utils.book_append_sheet(book, provSheet, "Inscritos kiosco");

  return {
    filename: "listado_universidad_plantilla.xlsx",
    blob: workbookBlob(book),
  };
}

export function downloadWorkbook(file) {
  downloadBlob(file.blob, file.filename);
}

export async function shareWorkbook(file, title) {
  return shareBlob(file.blob, file.filename, title || file.filename);
}
