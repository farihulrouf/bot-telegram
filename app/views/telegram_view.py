from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from app.models.telegram_model import PhoneNumber, VerificationCode
from app.controllers import telegram_controller

router = APIRouter()

class SendMessageRequest(BaseModel):
    phone: str
    recipient: str
    message: str

@router.post("/api/send_message")
async def send_message(request: SendMessageRequest):
    try:
        response = await telegram_controller.send_message(request.phone, request.recipient, request.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/login")
async def login(phone: PhoneNumber):
    try:
        response = await telegram_controller.login(phone)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/verify")
async def verify(code: VerificationCode):
    try:
        response = await telegram_controller.verify(code)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/get_message")
async def get_message(phone: str = Query(...), channel_username: str = Query(...), limit: int = Query(10, le=100)):
    try:
        response = await telegram_controller.get_channel_messages(phone, channel_username, limit)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
