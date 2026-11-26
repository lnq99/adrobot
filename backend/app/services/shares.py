from dataclasses import dataclass

from app.core.errors import ValidationError


@dataclass
class OfferShare:
    offer_id: int
    status: str       # "active" | "removed"
    pinned: bool
    share: int        # pinned-active: locked value; otherwise recomputed


def rebalance(offers: list[OfferShare]) -> list[OfferShare]:
    for o in offers:
        if o.status == "removed":
            o.share = 0
            o.pinned = False

    active = [o for o in offers if o.status == "active"]
    pinned = [o for o in active if o.pinned]
    free = [o for o in active if not o.pinned]

    for o in pinned:
        if not 0 <= o.share <= 100:
            raise ValidationError(f"pinned share {o.share} out of range 0..100")
    pinned_sum = sum(o.share for o in pinned)
    if pinned_sum > 100:
        raise ValidationError("pinned shares exceed 100%")

    remain = 100 - pinned_sum
    if not free:
        if active and pinned_sum != 100:
            raise ValidationError("pinned shares must total 100% when no free offers")
        return offers
    if remain <= 0:
        raise ValidationError("pinned shares leave no room for other offers")

    base = remain // len(free)
    extra = remain - base * len(free)
    for i, o in enumerate(free):
        o.share = base + (1 if i < extra else 0)
    return offers
