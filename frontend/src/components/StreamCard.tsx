import { useState } from "react";
import type { Stream } from "../types";
import { api } from "../api";
import OfferRow from "./OfferRow";
import OfferPicker from "./OfferPicker";

export default function StreamCard({
  stream,
  onChange,
}: {
  stream: Stream;
  onChange: (s: Stream) => void;
}) {
  const [err, setErr] = useState("");

  async function run(p: Promise<Stream>) {
    try {
      onChange(await p);
      setErr("");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (stream.kind === "opaque") {
    return (
      <div style={{ border: "1px solid #ccc", padding: 12, margin: "8px 0" }}>
        <strong>Stream #{stream.keitaro_stream_id}</strong> (redirect — not editable)
      </div>
    );
  }

  const total = stream.offers
    .filter((o) => o.status === "active")
    .reduce((a, o) => a + o.share, 0);

  return (
    <div
      style={{
        border: "1px solid #ccc",
        padding: 12,
        margin: "8px 0",
        background: stream.is_dirty ? "#fff8d0" : "white",
      }}
    >
      <strong>Stream #{stream.keitaro_stream_id}</strong>{" "}
      {stream.is_dirty && <em>(unpublished)</em>}
      <table>
        <tbody>
          {stream.offers.map((o) => (
            <OfferRow
              key={o.keitaro_offer_id}
              offer={o}
              onRemove={() => run(api.removeOffer(stream.id, o.keitaro_offer_id))}
              onBringBack={() => run(api.bringBack(stream.id, o.keitaro_offer_id))}
              onPin={(pinned, share) => run(api.pin(stream.id, o.keitaro_offer_id, pinned, share))}
            />
          ))}
        </tbody>
      </table>
      <div>Total: {total}%</div>
      <OfferPicker onPick={(oid) => run(api.addOffer(stream.id, oid))} />
      <div style={{ marginTop: 8 }}>
        <button onClick={() => run(api.push(stream.id))}>Push to Keitaro</button>
        <button onClick={() => run(api.cancel(stream.id))}>Cancel</button>
      </div>
      {err && <p style={{ color: "crimson" }}>{err}</p>}
    </div>
  );
}
