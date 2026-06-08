"use client";

import { useCallback, useState } from "react";
import LanguagePicker from "@/components/language-picker";
import TextPane from "@/components/text-pane";
import { translateText } from "@/lib/api";
import { getLanguageName } from "@/lib/languages";

export default function TextPage() {
  const [src, setSrc] = useState("zh");
  const [tgt, setTgt] = useState("en");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleTranslate = useCallback(async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await translateText(input, src, tgt);
      setOutput(res.translated);
    } catch (e: any) {
      setOutput(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [input, src, tgt]);

  return (
    <div className="flex flex-col flex-1 gap-4">
      <div className="flex items-center gap-3">
        <LanguagePicker value={src} onChange={setSrc} label="Source" />
        <button
          onClick={() => { const t = src; setSrc(tgt); setTgt(t); }}
          className="flex items-center justify-center w-8 h-8 rounded-full border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="17 1 21 5 17 9"/><line x1="3" y1="11" x2="21" y2="11"/><polyline points="7 23 3 19 7 15"/><line x1="21" y1="13" x2="3" y2="13"/></svg>
        </button>
        <LanguagePicker value={tgt} onChange={setTgt} label="Target" />
        <button
          onClick={handleTranslate}
          disabled={loading || !input.trim()}
          className="ml-auto px-4 py-1.5 rounded-[var(--radius-sm)] bg-[var(--accent)] text-[var(--bg)] text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-40 transition-colors cursor-pointer disabled:cursor-not-allowed"
        >
          {loading ? "..." : "Translate"}
        </button>
      </div>
      <div className="flex flex-1 gap-4">
        <TextPane value={input} onChange={setInput} placeholder="Enter text to translate" label={`Source (${getLanguageName(src)})`} />
        <TextPane value={output} onChange={() => {}} placeholder="Translation" readOnly label={`Target (${getLanguageName(tgt)})`} />
      </div>
    </div>
  );
}
