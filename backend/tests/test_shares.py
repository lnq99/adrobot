from app.services.shares import OfferShare, rebalance


def shares(result):
    return [o.share for o in result]


def test_four_active_even():
    offers = [OfferShare(i, "active", False, 0) for i in range(4)]
    assert shares(rebalance(offers)) == [25, 25, 25, 25]


def test_three_active_remainder_to_first():
    offers = [OfferShare(i, "active", False, 0) for i in range(3)]
    assert shares(rebalance(offers)) == [34, 33, 33]
