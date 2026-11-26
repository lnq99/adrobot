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
