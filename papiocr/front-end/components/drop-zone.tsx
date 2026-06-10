"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  accept: string;
  maxSizeMB: number;
  onFile: (f: File) => void;
  label: string;
  formats: string;
}

export default function DropZone({ accept, maxSizeMB, onFile, label, formats }: Props) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) validate(f);
  }

  function validate(f: File) {
    if (f.size > maxSizeMB * 1024 * 1024) {
      alert(`File too large (max ${maxSizeMB} MB)`);
      return;
    }
    onFile(f);
  }

  useEffect(() => {
    function handlePaste(e: ClipboardEvent) {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.kind === "file") {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            if (file.size > maxSizeMB * 1024 * 1024) {
              alert(`File too large (max ${maxSizeMB} MB)`);
              return;
            }
            onFile(file);
            break;
          }
        }
      }
    }

    document.addEventListener("paste", handlePaste);
    return () => document.removeEventListener("paste", handlePaste);
  }, [maxSizeMB, onFile]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center flex-1 rounded-[var(--radius)] border-2 border-dashed transition-colors cursor-pointer ${
        drag
          ? "border-[var(--accent)] bg-[var(--accent)]/5"
          : "border-[var(--border)] hover:border-[var(--text-dim)] bg-[var(--bg-input)]"
      }`}
    >
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-[var(--text-dim)] mb-2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <span className="text-sm text-[var(--text-muted)]">{label}</span>
      <span className="text-xs text-[var(--text-dim)] mt-1">{formats}</span>
      <span className="text-xs text-[var(--text-dim)] mt-1">or press Ctrl+V to paste</span>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) validate(f); }}
      />
    </div>
  );
}
