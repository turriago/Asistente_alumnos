const SIZE = 32;

export function fingerprintFromSource(source, sx, sy, sw, sh) {
  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(source, sx, sy, sw, sh, 0, 0, SIZE, SIZE);
  const { data } = ctx.getImageData(0, 0, SIZE, SIZE);
  const gray = new Float32Array(SIZE * SIZE);
  for (let i = 0; i < gray.length; i += 1) {
    const o = i * 4;
    gray[i] = 0.299 * data[o] + 0.587 * data[o + 1] + 0.114 * data[o + 2];
  }
  let mean = 0;
  for (const value of gray) mean += value;
  mean /= gray.length || 1;
  let norm = 0;
  for (let i = 0; i < gray.length; i += 1) {
    gray[i] -= mean;
    norm += gray[i] * gray[i];
  }
  norm = Math.sqrt(norm) || 1;
  for (let i = 0; i < gray.length; i += 1) gray[i] /= norm;
  return gray;
}

function cosine(left, right) {
  let sum = 0;
  for (let i = 0; i < left.length; i += 1) sum += left[i] * right[i];
  return sum;
}

export async function prepareGallery(students) {
  const prepared = [];
  for (const student of students) {
    if (!student || !student.photo) continue;
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.src = student.photo;
    try {
      await image.decode();
    } catch {
      continue;
    }
    prepared.push({
      id: student.id,
      name: student.name,
      program: student.program || "",
      group: student.group || "",
      photo: student.photo,
      print: fingerprintFromSource(image, 0, 0, image.width, image.height),
    });
  }
  return prepared;
}

export function matchStudent(prepared, queryPrint) {
  if (!prepared.length || !queryPrint) return null;
  let best = null;
  let second = -1;
  for (const student of prepared) {
    const score = cosine(queryPrint, student.print);
    if (!best || score > best.score) {
      second = best ? best.score : -1;
      best = { student, score };
    } else if (score > second) {
      second = score;
    }
  }
  if (!best || best.score < 0.84) return null;
  if (second >= 0 && best.score - second < 0.025) return null;
  return best.student;
}

async function fetchSupabaseGallery() {
  try {
    const config = await import("./supabase-public.js");
    const url = String(config.SUPABASE_URL || "").replace(/\/$/, "");
    const key = String(config.SUPABASE_ANON_KEY || "");
    if (!url || !key) return [];
    const query = new URL(url + "/rest/v1/students");
    query.searchParams.set(
      "select",
      "student_id,full_name,program,group_name,student_media(kind,public_url,is_card)",
    );
    const response = await fetch(query, {
      cache: "no-store",
      headers: { apikey: key, Authorization: "Bearer " + key },
    });
    if (!response.ok) return [];
    const rows = await response.json();
    const students = [];
    for (const row of rows || []) {
      const media = row.student_media || [];
      const card = media.find((item) => item.is_card) || media.find((item) => item.kind === "photo");
      if (!card || !card.public_url) continue;
      students.push({
        id: row.student_id,
        name: row.full_name,
        program: row.program || "",
        group: row.group_name || "",
        photo: card.public_url,
      });
    }
    return students;
  } catch {
    return [];
  }
}

export async function fetchGallery(classCode) {
  const fromSupabase = await fetchSupabaseGallery();
  if (fromSupabase.length) return fromSupabase;
  const code = encodeURIComponent((classCode || "aula1").trim() || "aula1");
  const urls = [
    `/.netlify/functions/gallery?c=${code}`,
    `./runtime/gallery.json`,
  ];
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) continue;
      const data = await response.json();
      const students = data.students || [];
      if (students.length) return students;
    } catch {
      /* siguiente origen */
    }
  }
  return [];
}
