"use client";

import { useEffect, useRef, useState } from "react";
import { listLanguages } from "@/lib/api";
import { getLanguageName } from "@/lib/languages";

const POPULAR = ["en", "zh", "ja", "ko", "fr", "de", "es", "ru", "pt", "ar"];

interface Props {
  value: string;
  onChange: (v: string) => void;
  label: string;
}

export default function LanguagePicker({ value, onChange, label }: Props) {
  const [open, setOpen] = useState(false);
  const [langs, setLangs] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listLanguages()
      .then((d) => setLangs(Object.keys(d.shortcuts)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const filtered = search
    ? langs.filter((l) => {
        const name = getLanguageName(l).toLowerCase();
        return l.includes(search.toLowerCase()) || name.includes(search.toLowerCase());
      })
    : [];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg-card)] text-sm text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
      >
        {getLanguageName(value)}
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
      </button>

      {open && (
        <div className="absolute top-full mt-1 left-0 w-64 max-h-72 overflow-y-auto rounded-[var(--radius)] border border-[var(--border)] bg-[var(--bg-card)] shadow-lg z-50 p-2">
          <div className="text-xs text-[var(--text-muted)] mb-1 px-2">{label}</div>
          <input
            autoFocus
            placeholder="Search languages..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-2 py-1 mb-1 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg-input)] text-sm text-[var(--text)] outline-none"
          />
          {(search ? filtered : POPULAR).map((code) => (
            <button
              key={code}
              onClick={() => { onChange(code); setOpen(false); setSearch(""); }}
              className={`w-full text-left px-2 py-1.5 rounded-[var(--radius-sm)] text-sm transition-colors cursor-pointer flex items-center justify-between ${
                value === code
                  ? "bg-[var(--accent)] text-[var(--bg)] font-medium"
                  : "text-[var(--text)] hover:bg-[var(--bg-hover)]"
              }`}
            >
              <span>{getLanguageName(code)}</span>
              <span className="text-xs opacity-60">{code}</span>
            </button>
          ))}
          {search && filtered.length === 0 && (
            <div className="px-2 py-1 text-sm text-[var(--text-dim)]">No matches</div>
          )}
        </div>
      )}
    </div>
  );
}
