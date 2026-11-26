import { useState } from "react";
import { api } from "../api";

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
    <div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="offer id or name"
      />
      <button type="button" onClick={search}>
        Search
      </button>
      <ul>
        {results.map((o) => (
          <li key={o.id}>
            {o.id} — {o.name}{" "}
            <button type="button" onClick={() => onPick(o.id)}>
              pick
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
