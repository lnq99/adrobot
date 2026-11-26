import { useState } from "react";
import { api } from "../api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function OfferPicker({
  onPick,
}: {
  onPick: (offerId: number) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ id: number; name: string }[]>([]);

  async function search() {
    setResults(await api.searchOffers(q));
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="offer id or name"
          className="flex-1"
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <Button type="button" variant="outline" onClick={search}>
          Search
        </Button>
      </div>
      {results.length > 0 && (
        <ul className="border border-slate-200 rounded-md bg-white divide-y divide-slate-100 max-h-48 overflow-y-auto">
          {results.map((o) => (
            <li key={o.id} className="flex items-center justify-between px-3 py-2 text-sm">
              <span className="text-slate-700">
                {o.id} — {o.name}
              </span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onPick(o.id)}
              >
                pick
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
