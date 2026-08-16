import hashlib
import uuid


def assign_variant_index(visitor_id: str, experiment_id: uuid.UUID, num_variants: int) -> int:
    """Deterministically map (visitor, experiment) -> arm index, so a visitor gets the
    same variant on every request without persisting per-visitor assignments in Postgres
    (see ARCHITECTURE.md: Postgres holds only config + rollups, not per-visitor state).
    Recomputed identically at /config (to assign) and at goal time (to attribute)."""
    digest = hashlib.sha256(f"{visitor_id}:{experiment_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % num_variants
