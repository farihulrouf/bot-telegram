from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from app.models.telegram_model import PhoneNumber,WebhookPayload, ContactResponse, ChannelDetailResponse, VerificationCode, JoinRequest, TextRequest, SendMessageRequest, ChannelNamesResponse, ChannelNamesResponseAll
from app.controllers import telegram_controller
from typing import Dict, List

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
async def get_message(
    phone: str = Query(...),
    channel_username: str = Query(...),
    limit: int = Query(10)  # Removed the maximum limit constraint
):
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
    channel_username: str = Query(...),  # Pastikan ini adalah string
    limit: int = Query(10)
    ):
    try:
        # Panggil fungsi controller untuk membaca pesan dan bergabung dengan channel
        result = await telegram_controller.read_and_join_channels(phone, channel_username, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Tambahkan endpoint untuk mendapatkan semua channel
@router.get("/api/getallchannels", response_model=ChannelNamesResponseAll)
async def get_all_channel(phone: str):
    try:
        response = await telegram_controller.get_all_channels(phone)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/api/getchannel", response_model=ChannelDetailResponse)
async def get_channel_details(phone: str = Query(...), channel_username: str = Query(...)):
    try:
        response = await telegram_controller.get_channel_details(phone, channel_username)
        if response["status"] == "success":
            return response["channel_info"]
        else:
            raise HTTPException(status_code=400, detail="Failed to get channel details")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/getcontacts", response_model=List[ContactResponse])
async def get_all_contacts(phone: str = Query(...)):
    try:
        response = await telegram_controller.get_all_contacts(phone)
        if response["status"] == "success":
            return response["contacts"]
        else:
            raise HTTPException(status_code=400, detail="Failed to get contacts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/api/get_user_details")
async def get_user_details(phone: str = Query(...), username: str = Query(...)):
    try:
        response = await telegram_controller.get_user_details(phone, username)
        if "error" in response:
            raise HTTPException(status_code=400, detail=response["error"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/webhook")
async def receive_webhook(payload: WebhookPayload):
    # Proses data webhook di sini
    print("Webhook received:")
    print(payload.dict())

    # Contoh: Kirim respons untuk mengonfirmasi bahwa webhook diterima
    return {"status": "success"}