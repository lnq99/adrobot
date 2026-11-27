import type { Offer } from "../types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";

export default function OfferRow({
  offer,
  onRemove,
  onBringBack,
  onPin,
}: {
  offer: Offer;
  onRemove: () => void;
  onBringBack: () => void;
  onPin: (pinned: boolean, share: number | null) => void;
}) {
  const removed = offer.status === "removed";

  return (
    <TableRow className={removed ? "opacity-60" : ""}>
      {/* ID */}
      <TableCell className="font-mono text-sm">{offer.keitaro_offer_id}</TableCell>

      {/* Name */}
      <TableCell className="text-sm">{offer.offer_name}</TableCell>

      {/* Share */}
      <TableCell className="text-sm">
        {offer.pinned ? (
          <input
            type="number"
            value={offer.share}
            min={0}
            max={100}
            className="w-16 h-7 rounded border border-slate-200 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            onChange={(e) => onPin(true, Number(e.target.value))}
          />
        ) : (
          <span>{offer.share}%</span>
        )}
      </TableCell>

      {/* Status */}
      <TableCell>
        <div className="flex items-center gap-1">
          {removed ? (
            <Badge
              variant="secondary"
              title={
                offer.origin === "keitaro"
                  ? "Removed in Keitaro (detected on fetch)"
                  : "Removed locally"
              }
            >
              Removed
            </Badge>
          ) : (
            <Badge variant="success">active</Badge>
          )}
          {offer.pinned && <span title="Pinned">📌</span>}
        </div>
      </TableCell>

      {/* Actions */}
      <TableCell>
        <div className="flex gap-1">
          {removed ? (
            <Button size="sm" variant="outline" className="w-24" onClick={onBringBack}>
              Bring back
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant={offer.pinned ? "secondary" : "outline"}
                className="w-24"
                onClick={() => onPin(!offer.pinned, offer.pinned ? null : offer.share)}
              >
                {offer.pinned ? "📌 Unpin" : "Pin"}
              </Button>
              <Button size="sm" variant="destructive" className="w-24" onClick={onRemove}>
                Remove
              </Button>
            </>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}
