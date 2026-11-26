import type { Offer } from "../types";

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
    <tr style={{ color: removed ? "#999" : "inherit" }}>
      <td>{offer.keitaro_offer_id}</td>
      <td>{offer.offer_name}</td>
      <td>
        {offer.pinned ? (
          <input
            type="number"
            value={offer.share}
            min={0}
            max={100}
            style={{ width: 60 }}
            onChange={(e) => onPin(true, Number(e.target.value))}
          />
        ) : (
          `${offer.share}%`
        )}
      </td>
      <td>
        {removed && offer.origin === "keitaro" && <span>REM </span>}
        {removed ? (
          <button onClick={onBringBack}>Bring back</button>
        ) : (
          <>
            <button onClick={() => onPin(!offer.pinned, offer.pinned ? null : offer.share)}>
              {offer.pinned ? "📌 Unpin" : "Pin"}
            </button>
            <button onClick={onRemove}>Remove</button>
          </>
        )}
      </td>
    </tr>
  );
}
