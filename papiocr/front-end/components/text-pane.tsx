"use client";

import { useRef } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  readOnly?: boolean;
  maxLength?: number;
  label?: string;
}

export default function TextPane({ value, onChange, placeholder, readOnly, maxLength = 10000, label }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  return (
    <div className="flex flex-col flex-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--bg-input)] overflow-hidden">
      {label && (
        <div className="px-3 pt-2 pb-0 text-xs text-[var(--text-muted)]">{label}</div>
      )}
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        readOnly={readOnly}
        maxLength={maxLength}
        className="flex-1 w-full resize-none bg-transparent text-sm text-[var(--text)] placeholder:text-[var(--text-dim)] px-3 py-2 outline-none leading-relaxed"
      />
      <div className="flex items-center justify-between px-3 py-1.5 border-t border-[var(--border)]">
        <span className="text-xs text-[var(--text-dim)]">
          {value.length} / {maxLength}
        </span>
        {!readOnly && value && (
          <button
            onClick={() => onChange("")}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text)] transition-colors cursor-pointer bg-transparent border-none"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}
