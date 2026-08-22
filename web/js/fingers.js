const WRIST = 0;
const THUMB_MCP = 2;
const THUMB_IP = 3;
const THUMB_TIP = 4;
const INDEX_MCP = 5;
const PINKY_MCP = 17;
const OTHER = [
  [8, 6, 5],
  [12, 10, 9],
  [16, 14, 13],
  [20, 18, 17],
];

function dist(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

function dot(point, end, origin) {
  return (point[0] - origin[0]) * (end[0] - origin[0]) + (point[1] - origin[1]) * (end[1] - origin[1]);
}

function align(start, mid, end) {
  const ax = mid[0] - start[0];
  const ay = mid[1] - start[1];
  const bx = end[0] - mid[0];
  const by = end[1] - mid[1];
  const na = Math.hypot(ax, ay);
  const nb = Math.hypot(bx, by);
  if (na < 1 || nb < 1) return 0;
  return (ax * bx + ay * by) / (na * nb);
}

function beyond(points, tip, joint, origin, ratio) {
  const o = points[origin];
  const j = points[joint];
  const t = points[tip];
  const length2 = dist(j, o) ** 2;
  if (length2 < 1) return false;
  return dot(t, j, o) > length2 * ratio;
}

function fingerUp(points, tip, pip, mcp, ratio = 1.08) {
  if (!beyond(points, tip, pip, mcp, ratio)) return false;
  const bone = dist(points[mcp], points[pip]);
  if (bone < 1) return false;
  if (dist(points[mcp], points[tip]) < bone * 1.85) return false;
  if (align(points[mcp], points[pip], points[tip]) < 0.62) return false;
  return true;
}

function thumbAway(points) {
  const tip = points[THUMB_TIP];
  const ip = points[THUMB_IP];
  const mcp = points[THUMB_MCP];
  const index = points[INDEX_MCP];
  const pinky = points[PINKY_MCP];
  const palm = dist(index, pinky);
  if (palm < 1) return false;
  if (dist(tip, pinky) <= dist(mcp, pinky) * 1.02) return false;
  if (dist(tip, pinky) < palm * 0.52) return false;
  if (dist(tip, index) < palm * 0.32) return false;
  const center = [
    (points[WRIST][0] + index[0] + pinky[0]) / 3,
    (points[WRIST][1] + index[1] + pinky[1]) / 3,
  ];
  return dist(tip, center) >= dist(ip, center);
}

export function toPoints(landmarks, width, height) {
  return landmarks.map((p) => [p.x * width, p.y * height]);
}

export function countFingers(landmarks, width, height) {
  if (!landmarks || landmarks.length < 21) return 0;
  const points = toPoints(landmarks, width, height);
  let raised = 0;
  for (const [tip, pip, mcp] of OTHER) {
    if (fingerUp(points, tip, pip, mcp)) raised += 1;
  }
  if (thumbAway(points) && (raised >= 4 || fingerUp(points, THUMB_TIP, THUMB_IP, THUMB_MCP, 1.12))) {
    raised += 1;
  }
  return Math.min(5, raised);
}

export function readNumber(hands, width, height) {
  const usable = (hands || []).filter((hand) => hand && hand.length >= 21);
  if (!usable.length) return { counts: [], total: 0, number: null };
  const chosen = usable.slice().sort((a, b) => (a[0]?.y ?? 1) - (b[0]?.y ?? 1))[0];
  const n = countFingers(chosen, width, height);
  return {
    counts: [n],
    total: n,
    number: n >= 1 && n <= 5 ? n : null,
  };
}

export class NumberSmoother {
  constructor(stableMs = 400) {
    this.stableMs = stableMs;
    this.candidate = null;
    this.since = 0;
    this.value = null;
  }

  update(number, now) {
    if (number === this.value) {
      this.candidate = number;
      this.since = now;
      return this.value;
    }
    if (number !== this.candidate) {
      this.candidate = number;
      this.since = now;
      return this.value;
    }
    if (now - this.since >= this.stableMs) this.value = number;
    return this.value;
  }

  reset() {
    this.candidate = null;
    this.since = 0;
    this.value = null;
  }
}
