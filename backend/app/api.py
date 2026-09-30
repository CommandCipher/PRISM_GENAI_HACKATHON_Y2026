from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.engine import troubleshoot

router=APIRouter()

class TroubleshootRequest(BaseModel):
    query: str = Field(min_length=3)

@router.post("/v1/troubleshoot")
@router.post("/api/v1/troubleshoot")
def troubleshoot_endpoint(body: TroubleshootRequest):
    return troubleshoot(body.query)
