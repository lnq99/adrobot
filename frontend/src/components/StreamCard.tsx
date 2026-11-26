import { useState } from "react";
import type { Stream } from "../types";
import { api } from "../api";
import OfferRow from "./OfferRow";
import OfferPicker from "./OfferPicker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
      <Card className="border-slate-200">
        <CardContent className="py-3 px-4">
          <span className="font-semibold text-slate-700">
            Stream #{stream.keitaro_stream_id}
          </span>{" "}
          <span className="text-slate-500 text-sm">(redirect — not editable)</span>
        </CardContent>
      </Card>
    );
  }

  const total = stream.offers
    .filter((o) => o.status === "active")
    .reduce((a, o) => a + o.share, 0);

  return (
    <Card
      className={`border ${stream.is_dirty ? "ring-2 ring-amber-400 border-amber-300 bg-amber-50" : "border-slate-200 bg-white"}`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-800">
            Stream #{stream.keitaro_stream_id}
          </span>
          {stream.is_dirty && (
            <span className="text-sm text-amber-700 font-medium">(unpublished)</span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Offers Table */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Share</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stream.offers.map((o) => (
              <OfferRow
                key={o.keitaro_offer_id}
                offer={o}
                onRemove={() => run(api.removeOffer(stream.id, o.keitaro_offer_id))}
                onBringBack={() => run(api.bringBack(stream.id, o.keitaro_offer_id))}
                onPin={(pinned, share) =>
                  run(api.pin(stream.id, o.keitaro_offer_id, pinned, share))
                }
              />
            ))}
          </TableBody>
        </Table>

        <div className="text-sm font-medium text-slate-700">
          Total: {total}%
        </div>

        {/* Offer picker for adding new offers */}
        <div className="border-t border-slate-100 pt-3">
          <div className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">
            Add offer
          </div>
          <OfferPicker onPick={(oid) => run(api.addOffer(stream.id, oid))} />
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 pt-1 border-t border-slate-100">
          <Button onClick={() => run(api.push(stream.id))}>
            Push to Keitaro
          </Button>
          <Button variant="outline" onClick={() => run(api.cancel(stream.id))}>
            Cancel
          </Button>
        </div>

        {err && (
          <p className="text-sm text-red-600 mt-1">{err}</p>
        )}
      </CardContent>
    </Card>
  );
}
