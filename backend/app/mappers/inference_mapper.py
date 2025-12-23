from app.models.inference_cache import InferenceCache
from app.schemas.inference import InferenceRead


def inference_to_read(cache: InferenceCache) -> InferenceRead:
    return InferenceRead(
        id=cache.id,
        scope_hash=cache.scope_hash,
        result=cache.result,
        uncertainty=cache.uncertainty,
    )