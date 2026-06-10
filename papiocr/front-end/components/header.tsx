"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "./theme-toggle";

const TABS = [
  { href: "/text", label: "Text" },
  { href: "/documents", label: "Documents" },
  { href: "/images", label: "Images" },
];

export default function Header() {
  const path = usePathname();

  return (
    <header className="flex items-center h-14 px-4 border-b border-[var(--border)] bg-[var(--bg)]">
      <Link href="/text" className="flex items-center gap-2 mr-8 no-underline">
        <div className="w-7 h-7 rounded-[var(--radius-sm)] bg-[var(--accent)] flex items-center justify-center text-white text-xs font-bold leading-none">
          p
        </div>
        <span className="text-sm font-medium text-[var(--text)]">papiocr</span>
      </Link>

      <nav className="flex items-center gap-1 flex-1">
        {TABS.map((t) => {
          const active = path === t.href || (t.href === "/text" && path === "/");
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-sm transition-colors no-underline ${
                active
                  ? "bg-[var(--bg-card)] text-[var(--accent)] font-medium"
                  : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]"
              }`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>

      <ThemeToggle />
    </header>
  );
}
