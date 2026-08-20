const { getStore } = require("@netlify/blobs");

function corsHeaders(event) {
  const origin = (event.headers && (event.headers.origin || event.headers.Origin)) || "*";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  };
}

function classCode(event, body) {
  const query = event.queryStringParameters || {};
  const fromQuery = String(query.c || "").trim();
  const fromBody = body && String(body.code || "").trim();
  return (fromBody || fromQuery || "aula1").slice(0, 32).toLowerCase();
}

exports.handler = async (event) => {
  const headers = corsHeaders(event);
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers, body: "" };
  }

  let store;
  try {
    store = getStore("web-gallery");
  } catch (err) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ students: [], error: "Sin almacén de fotos." }),
    };
  }

  if (event.httpMethod === "POST") {
    let body = {};
    try {
      body = JSON.parse(event.body || "{}");
    } catch {
      return { statusCode: 400, headers, body: JSON.stringify({ ok: false, error: "JSON inválido." }) };
    }
    const students = Array.isArray(body.students) ? body.students : [];
    const key = classCode(event, body);
    await store.setJSON(key, {
      code: key,
      students,
      updated_at: new Date().toISOString(),
    });
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ ok: true, count: students.length }),
    };
  }

  if (event.httpMethod !== "GET") {
    return { statusCode: 405, headers, body: JSON.stringify({ error: "Método no permitido." }) };
  }

  const key = classCode(event, null);
  const data = await store.get(key, { type: "json" });
  return {
    statusCode: 200,
    headers,
    body: JSON.stringify(data || { students: [] }),
  };
};
