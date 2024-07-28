from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from app.models.telegram_model import PhoneNumber, VerificationCode, JoinRequest, TextRequest, SendMessageRequest, ChannelNamesResponse
from app.controllers import telegram_controller
from typing import Dict

router = APIRouter()

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

@router.post("/api/join/subscribe")
async def join_channel(request: JoinRequest):
    try:
        response = await telegram_controller.join_subscribe(request.phone, request.username_channel)
        if response["status"] == "error":
            raise HTTPException(status_code=400, detail=response["message"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/api/getchannelname", response_model=ChannelNamesResponse)
async def get_channel_names(request: TextRequest) -> ChannelNamesResponse:
    try:
        # Call the controller function and return its result
        result = telegram_controller.extract_channel_names(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/readmessage")
async def read_message(
    phone: str = Query(...),
    channel_username: str = Query(...),  # Ensure this is a string
    limit: int = Query(10, le=100)
):
    try:
        # Call the controller function to read messages and join channels
        result = await telegram_controller.read_and_join_channels(phone, channel_username, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))