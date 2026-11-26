import { useEffect, useState } from "react";
import type { Campaign, Stream } from "../types";
import { api } from "../api";
import StreamCard from "../components/StreamCard";
import { Button } from "@/components/ui/button";

export default function Editor() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [streams, setStreams] = useState<Stream[]>([]);

  useEffect(() => {
    api.listCampaigns().then(setCampaigns);
  }, []);

  async function load(id: number) {
    setSelected(id);
    setStreams(await api.getStreams(id));
  }

  function updateStream(s: Stream) {
    setStreams((prev) => prev.map((x) => (x.id === s.id ? s : x)));
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-slate-900">Editor</h2>

      <div className="flex items-center gap-3">
        {/* Native <select> preserved for E2E: role="combobox" */}
        <select
          value={selected ?? ""}
          onChange={(e) => load(Number(e.target.value))}
          className="h-9 rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[240px]"
        >
          <option value="" disabled>
            pick a campaign
          </option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} (#{c.keitaro_campaign_id})
            </option>
          ))}
        </select>

        {selected && (
          <Button
            variant="outline"
            onClick={() => api.fetchStreams(selected).then(setStreams)}
          >
            Fetch Streams
          </Button>
        )}
      </div>

      {streams.map((s) => (
        <StreamCard key={s.id} stream={s} onChange={updateStream} />
      ))}
    </div>
  );
}
