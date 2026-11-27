import { useState, useMemo, useRef, useEffect } from "react";
import countries from "i18n-iso-countries";
import en from "i18n-iso-countries/langs/en.json";

countries.registerLocale(en);
const ALL = Object.entries(countries.getNames("en")) as [string, string][];

export default function CountrySelect({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  // Close the dropdown when clicking outside or pressing Escape.
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ALL;
    return ALL.filter(
      ([code, name]) =>
        code.toLowerCase().includes(q) || name.toLowerCase().includes(q),
    );
  }, [query]);

  function toggle(code: string) {
    onChange(value.includes(code) ? value.filter((c) => c !== code) : [...value, code]);
  }

  return (
    <div className="relative" ref={ref}>
      {/* Field: shows the selected countries, comma-separated. Click to open. */}
      <input
        type="text"
        readOnly
        aria-label="Countries"
        value={value.join(", ")}
        placeholder="Select countries…"
        onClick={() => setOpen((o) => !o)}
        className="w-full h-9 cursor-pointer rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-lg">
          {/* Search box (filter) */}
          <div className="p-2 border-b border-slate-100">
            <input
              type="text"
              autoFocus
              aria-label="Search countries"
              placeholder="Search…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full h-8 rounded border border-slate-200 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Options: each row has its own checkbox */}
          <ul className="max-h-56 overflow-auto py-1">
            {filtered.map(([code, name]) => (
              <li key={code}>
                <label className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={value.includes(code)}
                    onChange={() => toggle(code)}
                    aria-label={`${code} — ${name}`}
                  />
                  <span className="font-mono text-xs text-slate-500 w-7 shrink-0">{code}</span>
                  <span className="truncate">{name}</span>
                </label>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-3 py-2 text-sm text-slate-400">No matches</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
