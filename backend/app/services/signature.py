import hashlib

from app.keitaro.base import KStream


def stream_signature(stream: KStream) -> str:
    pairs = sorted((o.offer_id, o.share) for o in stream.offers)
    raw = ";".join(f"{oid}:{share}" for oid, share in pairs)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
