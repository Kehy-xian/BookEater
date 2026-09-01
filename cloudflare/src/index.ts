export interface Env {
  DB: D1Database;
  ALADIN_TTB_KEY: string;
}

type Json = Record<string, unknown>;

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function compactStringList(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map(String).map(x => x.trim()).filter(Boolean).slice(0, 20);
}

function safeText(v: unknown, max: number): string {
  return String(v ?? "").trim().slice(0, max);
}

async function receiveImprovement(req: Request, env: Env): Promise<Response> {
  let p: Json;
  try { p = await req.json<Json>(); } catch { return json({error:"bad_json"}, 400); }
  const exampleId = safeText(p.example_id, 80);
  const text = safeText(p.record_text, 5000);
  const consent = safeText(p.consent_version, 80);
  if (!exampleId || !text || !consent) return json({error:"missing_fields"}, 400);

  await env.DB.prepare(`INSERT OR IGNORE INTO improvement_examples
    (example_id,created_at,app_version,install_pseudonym,record_text,
     predicted_response,predicted_world,corrected_response,corrected_world,
     auxiliary_tags,model_backend,consent_version)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`)
    .bind(
      exampleId, safeText(p.created_at, 64), safeText(p.app_version, 40), safeText(p.install_pseudonym, 80), text,
      JSON.stringify(compactStringList(p.predicted_response)), JSON.stringify(compactStringList(p.predicted_world)),
      JSON.stringify(compactStringList(p.corrected_response)), JSON.stringify(compactStringList(p.corrected_world)),
      JSON.stringify(compactStringList(p.auxiliary_tags)), safeText(p.model_backend, 80), consent
    ).run();
  return json({accepted:true, example_id:exampleId}, 202);
}

function cacheKey(q: string, page: string): string {
  return `aladin:title:${q.toLowerCase()}:p${page}`;
}

async function searchBooks(url: URL, env: Env): Promise<Response> {
  const q = (url.searchParams.get("q") || "").trim();
  const page = url.searchParams.get("page") || "1";
  if (!q || q.length > 200) return json({error:"invalid_query"}, 400);
  const key = cacheKey(q, page);
  const now = Math.floor(Date.now()/1000);
  const cached = await env.DB.prepare(
    "SELECT payload_json FROM book_search_cache WHERE cache_key=? AND expires_at>?"
  ).bind(key, now).first<{payload_json:string}>();
  if (cached?.payload_json) {
    return new Response(cached.payload_json, {headers:{"content-type":"application/json; charset=utf-8","x-bookeater-cache":"hit"}});
  }
  if (!env.ALADIN_TTB_KEY) return json({error:"aladin_not_configured"}, 503);

  const a = new URL("https://www.aladin.co.kr/ttb/api/ItemSearch.aspx");
  a.searchParams.set("ttbkey", env.ALADIN_TTB_KEY);
  a.searchParams.set("Query", q);
  a.searchParams.set("QueryType", "Title");
  a.searchParams.set("MaxResults", "20");
  a.searchParams.set("start", page);
  a.searchParams.set("SearchTarget", "Book");
  a.searchParams.set("output", "js");
  a.searchParams.set("Version", "20131101");
  a.searchParams.set("Cover", "Big");
  const upstream = await fetch(a.toString(), {headers:{"user-agent":"BookEater/1"}});
  if (!upstream.ok) return json({error:"book_provider_error", status:upstream.status}, 502);
  const text = await upstream.text();
  const expires = now + 6*60*60;
  await env.DB.prepare(`INSERT INTO book_search_cache(cache_key,payload_json,expires_at)
    VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE SET payload_json=excluded.payload_json,expires_at=excluded.expires_at`)
    .bind(key, text, expires).run();
  return new Response(text, {headers:{"content-type":"application/json; charset=utf-8","x-bookeater-cache":"miss"}});
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (req.method === "GET" && url.pathname === "/health") return json({ok:true});
    if (req.method === "POST" && url.pathname === "/v1/improvement-examples") return receiveImprovement(req, env);
    if (req.method === "GET" && url.pathname === "/v1/books/search") return searchBooks(url, env);
    return json({error:"not_found"}, 404);
  }
};
