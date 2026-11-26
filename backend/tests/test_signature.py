from app.keitaro.base import KOffer, KStream
from app.services.signature import stream_signature


def test_signature_is_order_independent_and_change_sensitive():
    a = KStream(1, "s", 1, "landings", [KOffer(1, 50), KOffer(2, 50)])
    b = KStream(1, "s", 1, "landings", [KOffer(2, 50), KOffer(1, 50)])
    c = KStream(1, "s", 1, "landings", [KOffer(1, 60), KOffer(2, 40)])
    assert stream_signature(a) == stream_signature(b)
    assert stream_signature(a) != stream_signature(c)
