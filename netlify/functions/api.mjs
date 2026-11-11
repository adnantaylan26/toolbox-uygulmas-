// Toolbox Eğitim API — tek Netlify Function, /api/* yollarını karşılar.
import { getStore } from "@netlify/blobs";
import crypto from "node:crypto";
import * as L from "./lib/logic.mjs";

export const config = { path: "/api/*" };

const store = () => getStore({ name: "toolbox", consistency: "strong" });
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
const err = (msg, status = 400, code) => json({ error: msg, code }, status);

// ---------- yönetici oturumu (HMAC imzalı, 12 saat)
const secret = () => `${process.env.SESSION_SECRET || ""}|${process.env.ADMIN_PASSWORD || ""}`;
const sign = (exp) => crypto.createHmac("sha256", secret()).update(String(exp)).digest("hex");
function safeEq(a, b) { const x = Buffer.from(String(a)), y = Buffer.from(String(b)); return x.length === y.length && crypto.timingSafeEqual(x, y); }
function isAdmin(req) {
  const t = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  const [exp, sig] = t.split(".");
  if (!exp || !sig || +exp < Date.now() || !process.env.ADMIN_PASSWORD) return false;
  return safeEq(sig, sign(exp));
}

// ---------- belge deposu
const PATH_RE = /^[A-Za-z0-9_\-.~:@+]+(\/[A-Za-z0-9_\-.~:@+]+)*$/;
const validDoc = (p) => typeof p === "string" && PATH_RE.test(p) && !p.split("/").some((s) => s === "." || s === "..") && p.split("/").length % 2 === 0;
const validCol = (p) => typeof p === "string" && PATH_RE.test(p) && p.split("/").length % 2 === 1;
const getDoc = (p) => store().get(p, { type: "json" });
const setDoc = (p, d) => store().setJSON(p, d);
const delDoc = (p) => store().delete(p);
async function listCol(col) {
  const { blobs } = await store().list({ prefix: col + "/" });
  const depth = col.split("/").length + 1;
  const keys = blobs.map((b) => b.key).filter((k) => k.split("/").length === depth);
  const docs = await Promise.all(keys.map(async (k) => ({ id: k.split("/").pop(), data: await getDoc(k) })));
  return docs.filter((d) => d.data);
}

// ---------- yapay zeka (Anthropic API)
async function askClaude(prompt, maxTokens = 2000) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw Object.assign(new Error("ANTHROPIC_API_KEY tanımlı değil"), { code: "not_granted" });
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify({ model: process.env.ANTHROPIC_MODEL || "claude-haiku-5-5", max_tokens: maxTokens, messages: [{ role: "user", content: prompt }] }),
  });
  if (!r.ok) throw Object.assign(new Error(`Yapay zeka hatası (${r.status})`), { code: r.status === 429 ? "rate_limited" : "upstream_error" });
  const j = await r.json();
  return (j.content || []).filter((c) => c.type === "text").map((c) => c.text).join("");
}
async function aiGrade(qs, answers) {
  const res = qs.map((q, i) => (String(answers[i] || "").trim().length < 2 ? { correct: false, reason: "Cevap boş bırakılmış.", by: "auto" } : null));
  const todo = qs.map((q, i) => ({ q, i, ans: String(answers[i] || "").trim() })).filter((x) => !res[x.i]);
  if (!todo.length) return res;
  try {
    const out = L.parseJSONLoose(await askClaude(L.gradePrompt(todo), 800));
    for (const x of todo) {
      const o = Array.isArray(out) ? out.find((o) => Number(o?.soru) === x.i + 1) : null;
      if (o && typeof o.dogru === "boolean") res[x.i] = { correct: o.dogru, reason: String(o.gerekce || "").slice(0, 300), by: "ai" };
    }
  } catch { /* yapay zekaya ulaşılamazsa klasikler yönetici kontrolüne kalır */ }
  return res;
}

// ---------- çalışan tarafı yardımcıları
async function activeTopic() {
  const ts = (await listCol("topics")).filter((t) => t.data.active).sort((a, b) => (b.data.date || "").localeCompare(a.data.date || ""));
  return ts[0] ? { id: ts[0].id, ...ts[0].data } : null;
}
const sanTopic = (t, dk) => ({ id: t.id, title: t.title, date: t.date, active: !!t.active, finalMode: t.finalMode || (t.finalOpen ? "open" : "auto"), subjects: t.subjects || {}, content: dk ? { [dk]: (t.content || {})[dk] || {} } : {}, createdAt: t.createdAt || 0 });
let histCache = null;
async function history() {
  const meta = await getDoc("history/meta");
  if (!meta) return null;
  if (histCache?.importedAt === meta.importedAt) return histCache.h;
  const parts = [];
  for (let i = 0; i < (meta.chunks || 0); i++) { const d = await getDoc(`history/att_${i}`); if (d?.rows) parts.push(...d.rows); }
  const h = { catalog: meta.catalog || [], att: parts.map((s) => String(s).split(",").map(Number)) };
  histCache = { importedAt: meta.importedAt, h };
  return h;
}
async function resolveMe(body) {
  const tc = String(body.tc || "").replace(/\D/g, "");
  if (!/^\d{3,10}$/.test(tc)) return { error: "Geçerli bir sicil numarası girin." };
  const list = (await getDoc("config/staff"))?.list || [];
  const p = list.find((x) => String(x.tc) === tc);
  let name = p?.name || "", dk = p ? p.deptKey || L.deptKeyOf(p.dept) : null;
  if (!p || !dk) {
    const bdk = L.DEPTS.includes(body.dk) ? body.dk : null;
    const bname = String(body.name || "").trim().slice(0, 80);
    if (!bdk || (!p && !bname)) return { needInfo: true, name, dept: p?.dept || "" };
    name = name || bname; dk = bdk;
  }
  return { me: { tc, name, dk, start: p?.start || "" } };
}
async function workerState(t, me) {
  const prog = (await getDoc(`progress/${L.safeId(t.id)}__${L.safeId(me.tc)}`))?.weeks || {};
  const r = await getDoc(`results/${L.safeId(t.id)}__${L.safeId(me.tc)}`);
  const fin = r && r.status !== "started" ? { status: r.status, score: r.score, passed: r.passed, at: r.at } : null;
  let rec = [];
  try { rec = L.recWeeks(t, me.dk, me.tc, await history()); } catch {}
  return { me, topic: sanTopic(t, me.dk), prog, fin, rec };
}

async function worker(p, req) {
  if (p === "public" && req.method === "GET") {
    const t = await activeTopic();
    return json({ topic: t ? sanTopic(t, null) : null, brand: await getDoc("config/brand") });
  }
  if (req.method !== "POST") return err("Bulunamadı", 404);
  const body = await req.json().catch(() => ({}));
  const t = await activeTopic();
  if (!t) return err("Aktif eğitim dönemi yok.", 409);
  const who = await resolveMe(body);
  if (who.error) return err(who.error);
  if (who.needInfo) return json({ needInfo: true, name: who.name, dept: who.dept });
  const me = who.me, today = L.todayISO();
  const progKey = `progress/${L.safeId(t.id)}__${L.safeId(me.tc)}`;

  if (p === "login") return json(await workerState(t, me));

  if (p === "quiz/start" || p === "quiz/submit") {
    const w = body.w === "R" ? "R" : Number(body.w);
    const win = w === "R" ? L.reviewWin(t) : L.winOf(t, w);
    if (w !== "R" && !L.subjectsOf(t, me.dk).some((s) => s.w === w)) return err("Bu hafta departmanınız için tanımlı değil.");
    if (L.winStatus(win, today) === "upcoming") return err("Bu hafta henüz açılmadı.");
    const sessKey = `qsess/${L.safeId(t.id)}__${L.safeId(me.tc)}__${w}`;
    const prog = await getDoc(progKey);
    if (prog?.weeks?.[w]) return err("Bu quizi zaten tamamladınız.", 409);
    if (p === "quiz/start") {
      let sess = await getDoc(sessKey);
      if (!sess) {
        const items = w === "R" ? L.reviewItems(t, me.dk) : L.weeklyItems(t, me.dk, w);
        if (!items.length) return err("Bu hafta için soru tanımlı değil.");
        sess = { items, readAt: Date.now() };
        await setDoc(sessKey, sess);
      }
      return json({ items: L.sanItems(sess.items) });
    }
    const sess = await getDoc(sessKey);
    if (!sess) return err("Quiz oturumu bulunamadı. Lütfen quizi yeniden başlatın.", 409);
    const ans = Array.isArray(body.answers) ? body.answers : [];
    const score = sess.items.filter((it, i) => ans[i] === it.q.a).length;
    const entry = { score, total: sess.items.length, at: Date.now(), readAt: sess.readAt, late: L.winStatus(win, today) === "past",
      items: sess.items.map((it, i) => ({ type: it.type, id: it.q.id, q: it.q.q, opts: it.q.opts || null, a: it.q.a, ans: ans[i] ?? null })) };
    const doc = L.deepMerge(prog || { topicId: t.id, tc: me.tc }, { name: me.name, dk: me.dk, weeks: { [String(w)]: entry } });
    await setDoc(progKey, doc);
    await delDoc(sessKey);
    return json({ score, total: entry.total, items: sess.items.map((it) => ({ type: it.type, q: it.q })) });
  }

  if (p === "final/start" || p === "final/submit") {
    if (!L.finalOpenOf(t, today)) return err("Genel tekrar sınavı şu an açık değil.", 403);
    const key = `results/${L.safeId(t.id)}__${L.safeId(me.tc)}`;
    const prev = await getDoc(key);
    if (prev && prev.status !== "started") return err("Bu sınava zaten girdiniz.", 409);
    if (p === "final/start") {
      if (prev?.questions) return json({ questions: L.sanFinal(prev.questions), resumed: true, startedAt: prev.startedAt });
      const d = L.draw(t, me.dk);
      if (d.error) return err(d.error + " Yöneticiye haber verin.");
      const doc = { topicId: t.id, topicTitle: t.title, topicDate: t.date, tc: me.tc, name: me.name, deptKey: me.dk, status: "started", questions: d.questions, startedAt: Date.now() };
      await setDoc(key, doc);
      return json({ questions: L.sanFinal(d.questions), resumed: false, startedAt: doc.startedAt });
    }
    if (!prev?.questions) return err("Sınav oturumu bulunamadı.", 409);
    const A = body.answers || {};
    const answers = {
      tf: prev.questions.tf.map((_, i) => (typeof A.tf?.[i] === "boolean" ? A.tf[i] : null)),
      mc: prev.questions.mc.map((_, i) => (Number.isInteger(A.mc?.[i]) ? A.mc[i] : null)),
      classic: prev.questions.classic.map((_, i) => String(A.classic?.[i] || "").slice(0, 2000)),
    };
    const ev = await aiGrade(prev.questions.classic, answers.classic);
    const doc = { ...prev, status: "done", answers, classicEval: ev.map((x) => x || null), at: Date.now() };
    const sc = L.scoreOf(doc);
    Object.assign(doc, { score: sc.score, passed: sc.passed, classicPending: sc.pending, points: { tf: sc.tf, mc: sc.mc, classic: sc.cl } });
    await setDoc(key, doc);
    return json(doc);
  }
  return err("Bulunamadı", 404);
}

// ---------- yedekten içe aktarma
async function importBackup(b) {
  const n = { topics: 0, results: 0, progress: 0 };
  for (const col of ["topics", "results", "progress"]) {
    for (const d of b[col] || []) { if (d?.id && d?.data && validDoc(`${col}/${d.id}`)) { await setDoc(`${col}/${d.id}`, d.data); n[col]++; } }
  }
  if (b.staff?.list) await setDoc("config/staff", { list: b.staff.list, updatedAt: Date.now() });
  if (b.settings) await setDoc("config/settings", b.settings);
  if (b.brand) await setDoc("config/brand", b.brand);
  if (b.history?.att) {
    const CH = 1500, att = b.history.att, chunks = Math.ceil(att.length / CH);
    for (let i = 0; i < chunks; i++) await setDoc(`history/att_${i}`, { rows: att.slice(i * CH, (i + 1) * CH).map((r) => r.join(",")) });
    const m = b.history.meta || {};
    await setDoc("history/meta", { chunks, catalog: b.history.catalog || [], aliases: b.history.aliases || {}, range: m.range, left: m.left || 0, rowsRaw: m.rowsRaw || att.length, variants: m.variants || 0, importedAt: Date.now(), source: m.source || "Yedekten yüklendi" });
    histCache = null;
  }
  return n;
}

// ---------- yönlendirici
export default async (req) => {
  const url = new URL(req.url);
  const p = url.pathname.replace(/^\/api\/?/, "");
  try {
    if (p === "admin/login" && req.method === "POST") {
      const { password } = await req.json().catch(() => ({}));
      const pw = process.env.ADMIN_PASSWORD || "";
      if (!pw) return err("ADMIN_PASSWORD ortam değişkeni tanımlı değil.", 500);
      if (!password || !safeEq(password, pw)) { await new Promise((r) => setTimeout(r, 800)); return err("Şifre yanlış.", 401); }
      const exp = Date.now() + 12 * 3600e3;
      return json({ token: `${exp}.${sign(exp)}` });
    }
    if (p.startsWith("w/")) return await worker(p.slice(2), req);

    if (!isAdmin(req)) return err("Yönetici girişi gerekli.", 401, "unauthorized");
    if (p === "db" && req.method === "GET") {
      const col = url.searchParams.get("col"), doc = url.searchParams.get("doc");
      if (col && validCol(col)) return json({ docs: await listCol(col) });
      if (doc && validDoc(doc)) return json({ doc: await getDoc(doc) });
      return err("Geçersiz yol", 400, "invalid_argument");
    }
    if (p === "db" && req.method === "POST") {
      const { op, path, data } = await req.json();
      if (!validDoc(path)) return err("Geçersiz yol", 400, "invalid_argument");
      if (op === "set") await setDoc(path, data || {});
      else if (op === "update") { const cur = await getDoc(path); if (!cur) return err("Belge yok", 400, "invalid_argument"); await setDoc(path, L.deepMerge(cur, data)); }
      else if (op === "delete") await delDoc(path);
      else return err("Geçersiz işlem", 400, "invalid_argument");
      if (path.startsWith("history/")) histCache = null;
      return json({ ok: true });
    }
    if (p === "ai" && req.method === "POST") {
      const { prompt, maxTokens } = await req.json();
      return json({ text: await askClaude(String(prompt || "").slice(0, 200000), Math.min(Number(maxTokens) || 2000, 4000)) });
    }
    if (p === "admin/import" && req.method === "POST") return json({ ok: true, ...(await importBackup(await req.json())) });
    return err("Bulunamadı", 404);
  } catch (e) {
    return err(e.message || "Sunucu hatası", 500, e.code || "upstream_error");
  }
};
