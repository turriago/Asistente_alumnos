import * as XLSX from "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/+esm";
import { formatColombiaDate, formatColombiaTime } from "./attendance.js";

const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function sourceLabel(source) {
  if (source === "kiosk") return "kiosco";
  return "celular";
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

function sheetFromRows(rows, widths) {
  const ws = XLSX.utils.aoa_to_sheet(rows);
  ws["!cols"] = widths.map((wch) => ({ wch }));
  return ws;
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
  const presentSheet = [["ID", "Nombre", "Hora de la prueba", "Desde"], ...presentRows(present)];
  const missingSheet = [["ID", "Nombre", "Programa", "Grupo"], ...missingRows(missing)];
  return [
    ["Resumen", summary],
    ["Presentes", presentSheet],
    ["Ausentes", missingSheet],
  ];
}

function buildDayBook(session, present, missing) {
  const classCode = session.class_code || "aula1";
  const day = session.session_date || "";
  const pHeaders = ["ID", "Nombre", "Hora de la prueba", "Desde"];
  const mHeaders = ["ID", "Nombre", "Programa", "Grupo"];
  const pData = presentRows(present);
  const mData = missingRows(missing);
  const overview = sheetFromRows(
    [
      ["Asistencia del día"],
      ["Misma estructura que la vista previa. Editar este archivo no cambia el listado en la web."],
      [],
      ["Resumen"],
      ["Campo", "Valor"],
      ["Clase", classCode],
      ["Fecha", formatColombiaDate(day)],
      ["Hora de activación del QR", formatColombiaTime(session.started_at)],
      ["Personas presentes", present.length],
      ["Personas que faltaron", missing.length],
      ["Total en lista", present.length + missing.length],
      [],
      ["Presentes"],
      pHeaders,
      ...(pData.length ? pData : [["—", "", "", ""]]),
      [],
      ["Ausentes"],
      mHeaders,
      ...(mData.length ? mData : [["—", "", "", ""]]),
    ],
    [36, 42, 24, 16],
  );
  overview["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 3 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 3 } },
  ];
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, overview, "Asistencia");
  XLSX.utils.book_append_sheet(book, sheetFromRows([pHeaders, ...pData], [16, 42, 24, 14]), "Presentes");
  XLSX.utils.book_append_sheet(book, sheetFromRows([mHeaders, ...mData], [16, 42, 28, 14]), "Ausentes");
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
  const official = [
    ["codigo_estudiante", "nombres", "apellidos", "documento", "programa", "grupo", "correo"],
    ["", "", "", "", "", "", ""],
  ];
  const how = [
    ["Cómo usar esta plantilla"],
    ["Todavía no está el listado oficial de la universidad. Cuando te lo den, pégalo en la hoja Listado universidad."],
    ["No borres la primera fila de títulos."],
    ["Editar este Excel no cambia el listado de la web."],
  ];
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
  const book = XLSX.utils.book_new();
  const wide = Array(7).fill({ wch: 22 });
  const officialSheet = XLSX.utils.aoa_to_sheet(official);
  officialSheet["!cols"] = wide;
  const howSheet = XLSX.utils.aoa_to_sheet(how);
  howSheet["!cols"] = [{ wch: 90 }];
  const provSheet = XLSX.utils.aoa_to_sheet(provisional);
  provSheet["!cols"] = wide;
  XLSX.utils.book_append_sheet(book, officialSheet, "Listado universidad");
  XLSX.utils.book_append_sheet(book, howSheet, "Cómo usarlo");
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
