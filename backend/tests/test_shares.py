import random

import pytest

from app.core.errors import ValidationError
from app.services.shares import OfferShare, rebalance


def shares(result):
    return [o.share for o in result]


def test_four_active_even():
    offers = [OfferShare(i, "active", False, 0) for i in range(4)]
    assert shares(rebalance(offers)) == [25, 25, 25, 25]


def test_three_active_remainder_to_first():
    offers = [OfferShare(i, "active", False, 0) for i in range(3)]
    assert shares(rebalance(offers)) == [34, 33, 33]


def test_removed_offer_zeroed_and_excluded():
    offers = [
        OfferShare(1, "active", False, 0),
        OfferShare(2, "active", False, 0),
        OfferShare(3, "removed", False, 99),
    ]
    out = rebalance(offers)
    by_id = {o.offer_id: o.share for o in out}
    assert by_id == {1: 50, 2: 50, 3: 0}


def test_pin_even_split_of_remainder():
    offers = [
        OfferShare(1, "active", True, 25),
        OfferShare(2, "active", False, 0),
        OfferShare(3, "active", False, 0),
    ]
    out = rebalance(offers)
    assert [o.share for o in out] == [25, 38, 37]


def test_pin_user_set_value():
    offers = [
        OfferShare(1, "active", True, 40),
        OfferShare(2, "active", False, 0),
        OfferShare(3, "active", False, 0),
    ]
    out = rebalance(offers)
    assert [o.share for o in out] == [40, 30, 30]


def test_pins_over_100_rejected():
    offers = [OfferShare(1, "active", True, 60), OfferShare(2, "active", True, 50)]
    with pytest.raises(ValidationError):
        rebalance(offers)


def test_pin_leaves_no_room_rejected():
    offers = [OfferShare(1, "active", True, 100), OfferShare(2, "active", False, 0)]
    with pytest.raises(ValidationError):
        rebalance(offers)


def test_all_pinned_must_total_100():
    ok = [OfferShare(1, "active", True, 60), OfferShare(2, "active", True, 40)]
    assert [o.share for o in rebalance(ok)] == [60, 40]
    bad = [OfferShare(1, "active", True, 60), OfferShare(2, "active", True, 30)]
    with pytest.raises(ValidationError):
        rebalance(bad)


def test_single_pin_out_of_range_rejected():
    # A single pinned share outside 0..100 is rejected before the sum check
    # (distinct branch from "pinned shares exceed 100%").
    with pytest.raises(ValidationError):
        rebalance([OfferShare(1, "active", True, 150), OfferShare(2, "active", False, 0)])
    with pytest.raises(ValidationError):
        rebalance([OfferShare(1, "active", True, -5), OfferShare(2, "active", False, 0)])


def test_rebalance_invariant_fuzz():
    """Property check: for any valid mix of pinned/free/removed offers, active
    shares always total exactly 100, pinned offers keep their value, removed
    offers are zeroed, and free offers differ by at most 1 (remainder-to-first)."""
    rng = random.Random(1234)
    for _ in range(500):
        offers, oid = [], 1
        # 0..3 pinned offers whose shares sum to <= 90, leaving room for free offers
        budget = 90
        for _ in range(rng.randint(0, 3)):
            s = rng.randint(0, min(30, budget))
            budget -= s
            offers.append(OfferShare(oid, "active", True, s)); oid += 1
        # always >= 1 free active offer so a remainder exists to split
        for _ in range(rng.randint(1, 5)):
            offers.append(OfferShare(oid, "active", False, rng.randint(0, 100))); oid += 1
        # 0..2 removed offers (any input share/pinned — must be zeroed/cleared)
        for _ in range(rng.randint(0, 2)):
            offers.append(OfferShare(oid, "removed", rng.choice([True, False]), rng.randint(0, 99))); oid += 1
        rng.shuffle(offers)

        pinned_before = {o.offer_id: o.share for o in offers if o.status == "active" and o.pinned}
        out = rebalance(offers)
        active = [o for o in out if o.status == "active"]

        assert sum(o.share for o in active) == 100
        for o in out:
            if o.status == "removed":
                assert o.share == 0 and o.pinned is False
        for o in active:
            if o.offer_id in pinned_before:
                assert o.share == pinned_before[o.offer_id]
        free = [o.share for o in active if not o.pinned]
        if free:
            assert max(free) - min(free) <= 1
