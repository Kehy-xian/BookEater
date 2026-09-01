export interface Env {
  DB: D1Database;
  ALADIN_TTB_KEY: string;
}

type Json = Record<string, unknown>;
const RESPONSE = new Set(["사유","탐구","감정","감각"]);
const WORLD = new Set(["상상","모험","자연","사회","어둠"]);
const RETENTION_DAYS = 180;
const LIST_TYPES = new Set(["Bestseller","ItemNewAll","ItemNewSpecial","ItemEditorChoice","BlogBest"]);

function json(data: unknown, status = 200, extra: Record<string,string> = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...extra },
  });
}
function safeText(v: unknown, max: number): string { return String(v ?? "").trim().slice(0, max); }
function compactLabels(v: unknown, allowed: Set<string>): string[] {
  if (!Array.isArray(v)) return [];
  return [...new Set(v.map(String).map(x => x.trim()).filter(x => allowed.has(x)))].slice(0, 5);
}
function compactTags(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return [...new Set(v.map(String).map(x => x.trim()).filter(Boolean).map(x => x.slice(0, 40)))].slice(0, 12);
}
function redactText(v: unknown): string {
  let s = safeText(v, 1800);
  s = s.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[EMAIL]");
  s = s.replace(/https?:\/\/\S+|www\.\S+/gi, "[URL]");
  s = s.replace(/(?:\+?82[- ]?)?0?1[016789][- ]?\d{3,4}[- ]?\d{4}/g, "[PHONE]");
  s = s.replace(/\b\d{6}[- ]?[1-4]\d{6}\b/g, "[ID]");
  return s;
}
async function sha256(s: string): Promise<string> {
  const b = new TextEncoder().encode(s); const d = await crypto.subtle.digest("SHA-256", b);
  return [...new Uint8Array(d)].map(x => x.toString(16).padStart(2,"0")).join("");
}

async function receiveImprovement(req: Request, env: Env): Promise<Response> {
  const len = Number(req.headers.get("content-length") || 0);
  if (len > 16_384) return json({error:"payload_too_large"}, 413);
  let p: Json; try { p = await req.json<Json>(); } catch { return json({error:"bad_json"}, 400); }
  const exampleId = safeText(p.example_id, 80);
  const contributorId = safeText(p.contributor_id, 120);
  const text = redactText(p.record_text);
  const consent = safeText(p.consent_version, 80);
  const appVersion = safeText(p.app_version, 40);
  const model = safeText(p.model_backend, 80);
  if (!exampleId || contributorId.length < 20 || !text || !consent || !appVersion || !model) return json({error:"missing_or_invalid_fields"}, 400);

  const predictedResponse = compactLabels(p.predicted_response, RESPONSE);
  const predictedWorld = compactLabels(p.predicted_world, WORLD);
  const correctedResponse = compactLabels(p.corrected_response, RESPONSE);
  const correctedWorld = compactLabels(p.corrected_world, WORLD);
  const corrected = JSON.stringify(predictedResponse) !== JSON.stringify(correctedResponse) || JSON.stringify(predictedWorld) !== JSON.stringify(correctedWorld);
  const uncertainty = Number(p.model_confidence ?? 1);
  if (!corrected && Number.isFinite(uncertainty) && uncertainty >= 0.72) return json({accepted:false, reason:"not_needed"}, 202);

  const contributorHash = await sha256(contributorId); const textHash = await sha256(text);
  await env.DB.prepare(`INSERT OR IGNORE INTO improvement_examples
    (example_id,created_at,app_version,contributor_hash,text_hash,record_text,predicted_response,predicted_world,corrected_response,corrected_world,auxiliary_tags,model_backend,model_confidence,consent_version)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)`)
    .bind(exampleId,safeText(p.created_at,64),appVersion,contributorHash,textHash,text,
      JSON.stringify(predictedResponse),JSON.stringify(predictedWorld),JSON.stringify(correctedResponse),JSON.stringify(correctedWorld),
      JSON.stringify(compactTags(p.auxiliary_tags)),model,Number.isFinite(uncertainty)?Math.max(0,Math.min(1,uncertainty)):null,consent).run();
  return json({accepted:true, example_id:exampleId}, 202);
}

async function deleteContributorData(req: Request, env: Env): Promise<Response> {
  let p: Json; try { p = await req.json<Json>(); } catch { return json({error:"bad_json"}, 400); }
  const contributorId = safeText(p.contributor_id,120);
  if (contributorId.length < 20) return json({error:"invalid_contributor"},400);
  const h = await sha256(contributorId);
  const r = await env.DB.prepare("DELETE FROM improvement_examples WHERE contributor_hash=?").bind(h).run();
  return json({deleted:true, changes:r.meta.changes ?? 0});
}

function normalizeQuery(q: string): string { return q.normalize("NFKC").replace(/\s+/g," ").trim(); }
function clampCount(v: string|null, fallback=20): number {
  const n=Number(v ?? fallback); return Number.isInteger(n) ? Math.max(1,Math.min(20,n)) : fallback;
}
function pickBook(x: any): Json {
  return {
    title:safeText(x?.title,500), author:safeText(x?.author,500), publisher:safeText(x?.publisher,300),
    isbn:safeText(x?.isbn,40), isbn13:safeText(x?.isbn13,40), cover_url:safeText(x?.cover,1000),
    category:safeText(x?.categoryName,500), description:safeText(x?.description,2000), link:safeText(x?.link,1000), source:"aladin"
  };
}
function cachedRequest(origin: string, kind: string, params: Record<string,string>): Request {
  const u=new URL(origin+"/__book_cache/"+kind); for (const [k,v] of Object.entries(params)) u.searchParams.set(k,v);
  return new Request(u.toString(),{method:"GET"});
}
async function cachedJson(cacheReq: Request): Promise<Response|null> {
  const hit=await caches.default.match(cacheReq); if (!hit) return null;
  const h=new Headers(hit.headers); h.set("x-bookeater-cache","hit"); return new Response(hit.body,{status:hit.status,headers:h});
}
async function aladinJson(url: URL): Promise<any|null> {
  const r=await fetch(url.toString(),{headers:{"user-agent":"BookEater/1"}}); if(!r.ok) return null;
  try{return await r.json();}catch{return null;}
}
function commonAladinParams(a: URL, env: Env, max: number, page=1): void {
  a.searchParams.set("ttbkey",env.ALADIN_TTB_KEY);a.searchParams.set("MaxResults",String(max));a.searchParams.set("start",String(page));
  a.searchParams.set("SearchTarget","Book");a.searchParams.set("output","js");a.searchParams.set("Version","20131101");a.searchParams.set("Cover","Big");
}
function normalizedPayload(parsed:any, meta:Json):Json {
  return {source:"aladin",sourceNotice:"도서 DB 제공 : 알라딘 인터넷서점(www.aladin.co.kr)",...meta,
    totalResults:Number(parsed?.totalResults||0),startIndex:Number(parsed?.startIndex||1),items:Array.isArray(parsed?.item)?parsed.item.map(pickBook):[]};
}

async function searchBooks(url: URL, env: Env): Promise<Response> {
  const q=normalizeQuery(url.searchParams.get("q")||""); const page=Number(url.searchParams.get("page")||"1"); const max=clampCount(url.searchParams.get("max_results"));
  if(!q||q.length>200||!Number.isInteger(page)||page<1||page>50)return json({error:"invalid_query"},400);
  const cacheReq=cachedRequest(url.origin,"search",{q:q.toLocaleLowerCase("ko-KR"),page:String(page),max:String(max)});
  const hit=await cachedJson(cacheReq); if(hit)return hit; if(!env.ALADIN_TTB_KEY)return json({error:"aladin_not_configured"},503);
  const a=new URL("https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"); commonAladinParams(a,env,max,page);
  a.searchParams.set("Query",q);a.searchParams.set("QueryType","Title"); const parsed=await aladinJson(a);
  if(!parsed)return json({error:"book_provider_error"},502);
  const miss=json(normalizedPayload(parsed,{query:q}),200,{"cache-control":"public, max-age=21600","x-bookeater-cache":"miss"});
  await caches.default.put(cacheReq,miss.clone()); return miss;
}

async function listBooks(url: URL, env: Env): Promise<Response> {
  const type=safeText(url.searchParams.get("type")||"Bestseller",40); const max=clampCount(url.searchParams.get("max_results"));
  if(!LIST_TYPES.has(type))return json({error:"invalid_list_type"},400);
  const cacheReq=cachedRequest(url.origin,"list",{type,max:String(max)}); const hit=await cachedJson(cacheReq); if(hit)return hit;
  if(!env.ALADIN_TTB_KEY)return json({error:"aladin_not_configured"},503);
  const a=new URL("https://www.aladin.co.kr/ttb/api/ItemList.aspx"); commonAladinParams(a,env,max,1); a.searchParams.set("QueryType",type);
  const parsed=await aladinJson(a); if(!parsed)return json({error:"book_provider_error"},502);
  const miss=json(normalizedPayload(parsed,{listType:type}),200,{"cache-control":"public, max-age=21600","x-bookeater-cache":"miss"});
  await caches.default.put(cacheReq,miss.clone()); return miss;
}

async function cleanup(env: Env): Promise<void> {
  await env.DB.prepare(`DELETE FROM improvement_examples WHERE received_at < datetime('now', ?)`).bind(`-${RETENTION_DAYS} days`).run();
}

export default {
  async fetch(req:Request,env:Env):Promise<Response>{
    const url=new URL(req.url);
    if(req.method==="GET"&&url.pathname==="/health")return json({ok:true});
    if(req.method==="POST"&&url.pathname==="/v1/improvement-examples")return receiveImprovement(req,env);
    if(req.method==="POST"&&url.pathname==="/v1/improvement-examples/delete-mine")return deleteContributorData(req,env);
    if(req.method==="GET"&&url.pathname==="/v1/books/search")return searchBooks(url,env);
    if(req.method==="GET"&&url.pathname==="/v1/books/list")return listBooks(url,env);
    return json({error:"not_found"},404);
  },
  async scheduled(_event:ScheduledEvent,env:Env):Promise<void>{await cleanup(env);}
};
