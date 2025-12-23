from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def explain():
    return {"message": "explainability endpoint"}