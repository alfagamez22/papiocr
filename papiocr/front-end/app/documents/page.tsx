"use client";

import { useCallback, useRef, useState } from "react";
import LanguagePicker from "@/components/language-picker";
import DropZone from "@/components/drop-zone";
import { translateDocument } from "@/lib/api";

export default function DocumentsPage() {
  const [src, setSrc] = useState("zh");
  const [tgt, setTgt] = useState("en");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const linkRef = useRef<HTMLAnchorElement>(null);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    setResultUrl(null);
  }, []);

  const handleTranslate = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    try {
      const res = await translateDocument(file, src, tgt);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setResultUrl(url);
      linkRef.current?.click();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Unknown error";
      alert(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [file, src, tgt]);

  const ext = file ? file.name.split(".").pop() : "docx";

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
        {file && (
          <button
            onClick={handleTranslate}
            disabled={loading}
            className="ml-auto px-4 py-1.5 rounded-[var(--radius-sm)] bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-hover)] disabled:opacity-40 transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? "..." : "Translate"}
          </button>
        )}
      </div>

      {file ? (
        <div className="flex flex-col flex-1 items-center justify-center gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--bg-input)] p-8">
          <div className="text-sm text-[var(--text)] font-medium">{file.name}</div>
          <div className="text-xs text-[var(--text-dim)]">{(file.size / 1024 / 1024).toFixed(1)} MB</div>
          <button
            onClick={() => { setFile(null); setResultUrl(null); }}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text)] transition-colors cursor-pointer bg-transparent border-none"
          >
            Remove
          </button>
          {resultUrl && (
            <a ref={linkRef} href={resultUrl} download={`translated.${ext}`} className="px-4 py-1.5 rounded-[var(--radius-sm)] bg-[var(--accent)] text-white text-sm font-medium no-underline hover:bg-[var(--accent-hover)] transition-colors">
              Download translated file
            </a>
          )}
        </div>
      ) : (
        <DropZone
          accept=".doc,.docx,.pdf,.xls,.xlsx,.ppt,.pptx"
          maxSizeMB={15}
          onFile={handleFile}
          label="Drag & drop a document, or click to browse"
          formats="DOC, DOCX, PDF, XLS, XLSX, PPT, PPTX — up to 15 MB"
        />
      )}
    </div>
  );
}
