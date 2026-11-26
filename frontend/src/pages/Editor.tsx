import { useEffect, useState } from "react";
import type { Campaign, Stream } from "../types";
import { api } from "../api";
import StreamCard from "../components/StreamCard";

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
    <div>
      <h2>Editor</h2>
      <select
        value={selected ?? ""}
        onChange={(e) => load(Number(e.target.value))}
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
        <button onClick={() => api.fetchStreams(selected).then(setStreams)}>
          Fetch Streams
        </button>
      )}
      {streams.map((s) => (
        <StreamCard key={s.id} stream={s} onChange={updateStream} />
      ))}
    </div>
  );
}
