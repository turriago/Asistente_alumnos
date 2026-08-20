const MODEL_URL = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/model";
const MATCH_MAX = 0.52;

let faceapi = null;
let options = null;
let ready = false;

export async function loadFaceApi() {
  if (ready) return true;
  const mod = await import("https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/dist/face-api.esm.js");
  faceapi = mod.default || mod;
  await Promise.all([
    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
    faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
    faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
  ]);
  options = new faceapi.TinyFaceDetectorOptions({ inputSize: 160, scoreThreshold: 0.35 });
  ready = true;
  return true;
}

function distance(left, right) {
  let sum = 0;
  for (let i = 0; i < left.length; i += 1) {
    const delta = left[i] - right[i];
    sum += delta * delta;
  }
  return Math.sqrt(sum);
}

async function descriptorFromImage(url) {
  const image = await faceapi.fetchImage(url);
  const det = await faceapi
    .detectSingleFace(image, options)
    .withFaceLandmarks(true)
    .withFaceDescriptor();
  return det ? det.descriptor : null;
}

export async function buildDescriptors(students) {
  const labeled = [];
  if (!ready) return labeled;
  const jobs = (students || []).map(async (student) => {
    if (!student || !student.photo) return null;
    try {
      const vector = await descriptorFromImage(student.photo);
      if (!vector) return null;
      return { student, descriptors: [vector] };
    } catch {
      return null;
    }
  });
  for (const item of await Promise.all(jobs)) {
    if (item) labeled.push(item);
  }
  return labeled;
}

export async function matchVideo(video, labeled) {
  if (!ready || !labeled.length || !video.videoWidth) return null;
  const det = await faceapi
    .detectSingleFace(video, options)
    .withFaceLandmarks(true)
    .withFaceDescriptor();
  if (!det) return null;
  let best = null;
  let second = 99;
  for (const item of labeled) {
    let score = 99;
    for (const vector of item.descriptors) {
      const value = distance(det.descriptor, vector);
      if (value < score) score = value;
    }
    if (!best || score < best.score) {
      second = best ? best.score : 99;
      best = { student: item.student, score };
    } else if (score < second) {
      second = score;
    }
  }
  if (!best || best.score > MATCH_MAX) return null;
  if (second < 99 && second - best.score < 0.04) return null;
  return best.student;
}
