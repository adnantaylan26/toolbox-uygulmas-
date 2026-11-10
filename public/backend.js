// Netlify köprüsü: uygulamanın beklediği claude.use("db" | "sample" | "downloads") arayüzünü
// Netlify Functions API'si ile sağlar. Yönetici değilse veritabanı açılmaz; çalışan işlemleri /api/w/* üzerinden yürür.
(function () {
  window.TBX_NETLIFY = true;
  let token = null;
  try { token = localStorage.getItem("tbx-admin-token"); } catch (e) {}
  const tokenValid = () => { if (!token) return false; const exp = +String(token).split(".")[0]; return exp > Date.now(); };

  async function api(path, opts = {}) {
    const headers = { "content-type": "application/json" };
    if (tokenValid()) headers.authorization = "Bearer " + token;
    const r = await fetch("/api/" + path, { method: opts.method || (opts.body ? "POST" : "GET"), headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
    let j = {};
    try { j = await r.json(); } catch (e) {}
    if (!r.ok) {
      if (r.status === 401 && j.code === "unauthorized") { try { localStorage.removeItem("tbx-admin-token"); } catch (e) {} }
      throw { code: j.code || (r.status === 401 ? "unauthorized" : "unavailable"), message: j.error || "Sunucu hatası", status: r.status };
    }
    return j;
  }

  // ---- veritabanı köprüsü (yalnızca yönetici)
  function makeDb() {
    const subs = new Set();
    const docSnap = (path, d) => ({ id: path.split("/").pop(), exists: d != null, data: () => d ?? undefined, metadata: { fromCache: false, hasPendingWrites: false } });
    const colSnap = (docs) => {
      const ds = docs.map((x) => ({ id: x.id, exists: true, data: () => x.data, metadata: { fromCache: false, hasPendingWrites: false } }));
      return { docs: ds, size: ds.length, empty: !ds.length, metadata: { fromCache: false, hasPendingWrites: false }, docChanges: () => [] };
    };
    const fetchCol = async (p) => (await api("db?col=" + encodeURIComponent(p))).docs || [];
    const fetchDoc = async (p) => (await api("db?doc=" + encodeURIComponent(p))).doc ?? null;
    async function run(s) {
      try { s.cb(s.kind === "col" ? colSnap(await fetchCol(s.path)) : docSnap(s.path, await fetchDoc(s.path))); }
      catch (e) { if (s.err) s.err(e); }
    }
    let timer = null;
    const refresh = () => { clearTimeout(timer); timer = setTimeout(() => subs.forEach(run), 300); };
    setInterval(() => { if (document.visibilityState !== "hidden") subs.forEach(run); }, 30000);
    const write = async (op, path, data) => { await api("db", { body: { op, path, data } }); refresh(); };
    function doc(path) {
      return {
        id: path.split("/").pop(), path,
        get: async () => docSnap(path, await fetchDoc(path)),
        set: (d) => write("set", path, d),
        update: (d) => write("update", path, d),
        delete: () => write("delete", path),
        onSnapshot(cb, err) { const s = { kind: "doc", path, cb, err }; subs.add(s); run(s); return () => subs.delete(s); },
        collection: (sub) => collection(path + "/" + sub),
      };
    }
    function collection(path) {
      return {
        path,
        doc: (id) => doc(path + "/" + (id || Math.random().toString(36).slice(2, 12))),
        get: async () => colSnap(await fetchCol(path)),
        onSnapshot(cb, err) { const s = { kind: "col", path, cb, err }; subs.add(s); run(s); return () => subs.delete(s); },
        add: async (d) => { const r = doc(path + "/" + Math.random().toString(36).slice(2, 12)); await r.set(d); return r; },
      };
    }
    return { doc, collection };
  }

  // ---- yapay zeka (yalnızca yönetici; çalışan sınavlarında değerlendirme sunucuda yapılır)
  function makeSample() {
    const parse = (t) => {
      try { return JSON.parse(t); } catch (e) {}
      const m = String(t).match(/```(?:json)?\s*([\s\S]*?)```/); if (m) { try { return JSON.parse(m[1]); } catch (e) {} }
      const i = t.search(/[\[{]/), j = Math.max(t.lastIndexOf("]"), t.lastIndexOf("}"));
      if (i >= 0 && j > i) { try { return JSON.parse(t.slice(i, j + 1)); } catch (e) {} }
      throw { code: "invalid_json", message: "JSON okunamadı", text: t };
    };
    const sample = async (input, opts = {}) => {
      const prompt = typeof input === "string" ? input : input.map((m) => m.content).join("\n\n");
      const r = await api("ai", { body: { prompt, maxTokens: 3000 } });
      if (opts.onText) opts.onText({ text: r.text, delta: r.text });
      return { text: r.text, truncated: false };
    };
    sample.json = async (input, opts) => parse((await sample(input, opts)).text);
    sample.limits = async () => ({ maxPromptBytes: 200000 });
    return sample;
  }

  // ---- dosya indirme
  const downloads = {
    async save({ filename, data }) {
      const blob = data instanceof Blob ? data : new Blob([data], { type: filename.endsWith(".csv") ? "text/csv;charset=utf-8" : filename.endsWith(".json") ? "application/json" : "application/octet-stream" });
      const url = URL.createObjectURL(blob), a = document.createElement("a");
      a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      return { status: "saved" };
    },
  };

  const admin = tokenValid();
  const db = admin ? makeDb() : null, sample = admin ? makeSample() : null;
  window.TBX = {
    api, isAdmin: admin,
    async login(password) { const r = await api("admin/login", { body: { password } }); try { localStorage.setItem("tbx-admin-token", r.token); } catch (e) {} location.reload(); },
    logout() { try { localStorage.removeItem("tbx-admin-token"); } catch (e) {} location.hash = "#calisan"; location.reload(); },
  };
  window.claude = { use: async (n) => (n === "db" ? db : n === "sample" ? sample : n === "downloads" ? downloads : null) };
})();
