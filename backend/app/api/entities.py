from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_entities():
    return []


@router.post("/")
def create_entity(payload: dict):
    return payload