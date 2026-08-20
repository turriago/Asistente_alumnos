const SIZE = 64;

function equalizeAndNormalize(gray) {
  const hist = new Float32Array(256);
  for (let i = 0; i < gray.length; i += 1) {
    const bin = Math.max(0, Math.min(255, gray[i] | 0));
    hist[bin] += 1;
  }
  const cdf = new Float32Array(256);
  let total = 0;
  let cdfMin = 0;
  for (let i = 0; i < 256; i += 1) {
    total += hist[i];
    cdf[i] = total;
    if (!cdfMin && total) cdfMin = total;
  }
  const out = new Float32Array(gray.length);
  const denom = Math.max(1, total - cdfMin);
  for (let i = 0; i < gray.length; i += 1) {
    const bin = Math.max(0, Math.min(255, gray[i] | 0));
    out[i] = ((cdf[bin] - cdfMin) / denom) * 255;
  }
  let mean = 0;
  for (let i = 0; i < out.length; i += 1) mean += out[i];
  mean /= out.length || 1;
  let norm = 0;
  for (let i = 0; i < out.length; i += 1) {
    out[i] -= mean;
    norm += out[i] * out[i];
  }
  norm = Math.sqrt(norm) || 1;
  for (let i = 0; i < out.length; i += 1) out[i] /= norm;
  return out;
}

export function fingerprintFromSource(source, sx, sy, sw, sh, options = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (options.flip) {
    ctx.translate(SIZE, 0);
    ctx.scale(-1, 1);
  }
  ctx.drawImage(source, sx, sy, sw, sh, 0, 0, SIZE, SIZE);
  const { data } = ctx.getImageData(0, 0, SIZE, SIZE);
  const gray = new Float32Array(SIZE * SIZE);
  for (let i = 0; i < gray.length; i += 1) {
    const o = i * 4;
    gray[i] = 0.299 * data[o] + 0.587 * data[o + 1] + 0.114 * data[o + 2];
  }
  return equalizeAndNormalize(gray);
}

function cosine(left, right) {
  let sum = 0;
  for (let i = 0; i < left.length; i += 1) sum += left[i] * right[i];
  return sum;
}

async function printFromUrl(url) {
  const image = new Image();
  image.crossOrigin = "anonymous";
  image.src = url;
  await image.decode();
  return fingerprintFromSource(image, 0, 0, image.width, image.height);
}

export async function prepareGallery(students) {
  const prepared = [];
  for (const student of students) {
    const urls = [...new Set([student.photo, ...(student.photos || [])].filter(Boolean))];
    const prints = [];
    for (const url of urls) {
      try {
        prints.push(await printFromUrl(url));
      } catch {
        /* CORS o imagen rota */
      }
    }
    if (!prints.length) continue;
    prepared.push({
      id: student.id,
      name: student.name,
      program: student.program || "",
      group: student.group || "",
      photo: student.photo || urls[0],
      prints,
    });
  }
  return prepared;
}

export function matchStudent(prepared, queryPrints) {
  const queries = (Array.isArray(queryPrints) ? queryPrints : [queryPrints]).filter(Boolean);
  if (!prepared.length || !queries.length) return null;
  let best = null;
  let second = -1;
  for (const student of prepared) {
    let score = -1;
    for (const print of student.prints) {
      for (const query of queries) {
        const value = cosine(query, print);
        if (value > score) score = value;
      }
    }
    if (!best || score > best.score) {
      second = best ? best.score : -1;
      best = { student, score };
    } else if (score > second) {
      second = score;
    }
  }
  if (!best || best.score < 0.62) return null;
  if (second >= 0 && best.score - second < 0.02) return null;
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
      const images = media.filter((item) => item.kind === "card" || item.kind === "photo");
      const card = images.find((item) => item.is_card) || images[0];
      if (!card || !card.public_url) continue;
      students.push({
        id: row.student_id,
        name: row.full_name,
        program: row.program || "",
        group: row.group_name || "",
        photo: card.public_url,
        photos: images.map((item) => item.public_url).filter(Boolean),
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
