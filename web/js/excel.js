import * as XLSX from "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/+esm";
import { formatColombiaDate, formatColombiaTime } from "./attendance.js";

const XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function workbookBlob(sheets) {
  const book = XLSX.utils.book_new();
  for (const [name, rows] of sheets) {
    XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet(rows), name.slice(0, 31));
  }
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

function sourceLabel(source) {
  if (source === "kiosk") return "kiosco";
  return "celular";
}

export function daySheets(session, present, missing) {
  const classCode = session.class_code || "aula1";
  const day = session.session_date || "";
  const summary = [
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

export function dayWorkbook(session, present, missing) {
  const classCode = session.class_code || "aula1";
  const day = session.session_date || "";
  return {
    filename: `asistencia_${classCode}_${day}.xlsx`,
    blob: workbookBlob(daySheets(session, present, missing)),
  };
}

export function universityWorkbook(students) {
  const official = [
    ["codigo_estudiante", "nombres", "apellidos", "documento", "programa", "grupo", "correo"],
    ["", "", "", "", "", "", ""],
  ];
  const how = [
    ["Este archivo es la plantilla del listado que entrega la universidad."],
    ["Todavía no está cargado. Cuando te lo den, pégalo en la hoja Listado universidad."],
    ["No borres la primera fila de títulos."],
    ["La hoja Inscritos kiosco es solo un apoyo mientras llega el listado oficial."],
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
  return {
    filename: "listado_universidad_plantilla.xlsx",
    blob: workbookBlob([
      ["Listado universidad", official],
      ["Cómo usarlo", how],
      ["Inscritos kiosco", provisional],
    ]),
  };
}

export function downloadWorkbook(file) {
  downloadBlob(file.blob, file.filename);
}

export async function shareWorkbook(file, title) {
  return shareBlob(file.blob, file.filename, title || file.filename);
}
