"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import LanguagePicker from "@/components/language-picker";
import DropZone from "@/components/drop-zone";
import { translateImage } from "@/lib/api";

const PROCESS_STEPS = [
  "Reading image",
  "Detecting text",
  "Translating lines",
  "Rendering result",
];

export default function ImagesPage() {
  const [src, setSrc] = useState("zh");
  const [tgt, setTgt] = useState("en");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const linkRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!loading) return;
    const timer = window.setInterval(() => {
      setLoadingStep((step) => (step + 1) % PROCESS_STEPS.length);
    }, 1100);
    return () => window.clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    return () => {
      if (resultUrl) URL.revokeObjectURL(resultUrl);
    };
  }, [resultUrl]);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    setResultUrl(null);
    setPreviewUrl(URL.createObjectURL(f));
  }, []);

  const handleTranslate = useCallback(async () => {
    if (!file) return;
    setLoadingStep(0);
    setLoading(true);
    setResultUrl(null);
    try {
      const res = await translateImage(file, src, tgt);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setResultUrl(url);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Unknown error";
      alert(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [file, src, tgt]);

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
            {loading ? PROCESS_STEPS[loadingStep] : "Translate"}
          </button>
        )}
      </div>

      {file ? (
        <div className="flex flex-1 min-h-0 gap-4 flex-col xl:flex-row">
          <div className="flex min-h-[360px] min-w-0 flex-col flex-1 rounded-[var(--radius)] border border-[var(--border)] overflow-hidden bg-[var(--bg-input)]">
            <div className="px-3 py-1.5 text-xs text-[var(--text-muted)] border-b border-[var(--border)]">Original</div>
            <div className="flex-1 min-h-0 flex items-center justify-center p-2">
              {previewUrl && <img src={previewUrl} alt="Original" className="max-w-full max-h-full object-contain rounded-[var(--radius-sm)]" />}
            </div>
          </div>
          <div className="flex min-h-[360px] min-w-0 flex-col flex-1 rounded-[var(--radius)] border border-[var(--border)] overflow-hidden bg-[var(--bg-input)]">
            <div className="flex items-center justify-between px-3 py-1.5 text-xs text-[var(--text-muted)] border-b border-[var(--border)]">
              <span>Translated</span>
              {resultUrl && (
                <a ref={linkRef} href={resultUrl} download="translated.png" className="text-[var(--accent)] hover:text-[var(--accent-hover)] no-underline">Download</a>
              )}
            </div>
            <div className="relative flex-1 min-h-0 flex items-center justify-center overflow-hidden p-2">
              {loading && previewUrl ? (
                <TranslationLoading previewUrl={previewUrl} step={loadingStep} />
              ) : resultUrl ? (
                <img src={resultUrl} alt="Translated" className="max-w-full max-h-full object-contain rounded-[var(--radius-sm)]" />
              ) : (
                <span className="text-sm text-[var(--text-dim)]">Click Translate</span>
              )}
            </div>
          </div>
        </div>
      ) : (
        <DropZone
          accept=".png,.jpg,.jpeg,.webp,.bmp,.tiff"
          maxSizeMB={15}
          onFile={handleFile}
          label="Drag & drop an image, or click to browse"
          formats="PNG, JPG, WEBP, BMP, TIFF — up to 15 MB"
        />
      )}
    </div>
  );
}

function TranslationLoading({ previewUrl, step }: { previewUrl: string; step: number }) {
  return (
    <div className="translation-loader relative flex h-full w-full items-center justify-center rounded-[var(--radius-sm)] overflow-hidden" aria-live="polite">
      <img src={previewUrl} alt="" className="max-h-full max-w-full object-contain opacity-30 blur-[1px] saturate-50" />
      <div className="translation-scan-line" />
      <div className="translation-detection translation-detection-a" />
      <div className="translation-detection translation-detection-b" />
      <div className="translation-detection translation-detection-c" />

      <div className="absolute inset-x-4 bottom-4 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--bg)]/90 p-3 shadow-lg backdrop-blur">
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-[var(--text)]">Translating image</span>
          <span className="text-xs text-[var(--accent)]">{PROCESS_STEPS[step]}</span>
        </div>
        <div className="translation-progress-track">
          <div className="translation-progress-fill" />
        </div>
        <div className="mt-3 grid grid-cols-4 gap-2">
          {PROCESS_STEPS.map((label, index) => (
            <div
              key={label}
              className={`h-1.5 rounded-full transition-colors ${
                index <= step ? "bg-[var(--accent)]" : "bg-[var(--border)]"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
