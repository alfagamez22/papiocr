const API = "http://127.0.0.1:8000/api";

async function fetchJSON<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function health() {
  return fetchJSON<{ status: string; version: string }>(`${API}/health`);
}

export async function listLanguages() {
  return fetchJSON<{ languages: string[]; shortcuts: Record<string, string> }>(`${API}/languages`);
}

export async function translateText(text: string, source: string, target: string) {
  const form = new URLSearchParams({ text, source, target });
  return fetchJSON<{ source: string; target: string; original: string; translated: string }>(
    `${API}/translate/text`,
    { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: form }
  );
}

export async function translateImage(file: File, source: string, target: string) {
  const form = new FormData();
  form.append("file", file);
  form.append("source", source);
  form.append("target", target);
  const res = await fetch(`${API}/translate/image`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res;
}

export async function translateDocument(file: File, source: string, target: string) {
  const form = new FormData();
  form.append("file", file);
  form.append("source", source);
  form.append("target", target);
  const res = await fetch(`${API}/translate/document`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res;
}
