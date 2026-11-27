import hashlib

from app.keitaro.base import KStream


def stream_signature(stream: KStream) -> str:
    # Include state so a pause/activate upstream (same share) still trips a conflict.
    pairs = sorted((o.offer_id, o.share, o.state) for o in stream.offers)
    raw = ";".join(f"{oid}:{share}:{state}" for oid, share, state in pairs)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
