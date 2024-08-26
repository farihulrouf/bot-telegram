from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel
from app.models.telegram_model import FileDetails, ListDataResponse, PhoneNumber, WebhookPayload, ContactResponse, ChannelDetailResponse, VerificationCode, JoinRequest, GroupSearchRequest, TextRequest, SendMessageRequest, ChannelNamesResponse, ChannelNamesResponseAll
from app.models.telegram_model import active_clients
from app.controllers import telegram_group, telegram_crowler, telegram_controller, telegram_message
from typing import Dict, List, Any
import asyncio
import os

router = APIRouter()

# ok
@router.post("/api/login")
async def login(background_tasks: BackgroundTasks, phone: PhoneNumber):
    try:
        background_tasks.add_task(telegram_controller.login, phone)
        return {"status": "success", "phone": phone, "message": "requesting token"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ok
@router.post("/api/verify")
async def verify(code: VerificationCode):
    try:
        return await telegram_controller.verify(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ok
@router.post("/api/logout")
async def login(phone: PhoneNumber):
    try:
        return await telegram_controller.logout(phone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ok
@router.post("/api/status")
async def login(phone: PhoneNumber):
    try:
        return await telegram_controller.status(phone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ok
@router.post("/api/send_message")
async def send_message(request: SendMessageRequest):
    try:
        return await telegram_controller.send_message(request.phone, request.recipient, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ok
@router.post("/api/group/join")
async def join_channel(request: JoinRequest):
    try:
        return await telegram_group.join(request.phone, request.username_channel)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ok
@router.post("/api/group/leave")
async def leave_channel(request: JoinRequest):
    try:
        return await telegram_group.leave(request.phone, request.username_channel)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ok
@router.post("/api/group/search")
async def search_channel(background_tasks: BackgroundTasks, request: GroupSearchRequest):
    try:
        background_tasks.add_task(telegram_group.search, request.phone, request.query)
        return {"status": "starting group search", "query": request.query}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ok
@router.get("/api/group/messages")
async def get_group_messages(
    background_tasks: BackgroundTasks,
    phone: str = Query(...),
    channel_username: str = Query(...),
    limit: int = Query(10)
):
    try:
        background_tasks.add_task(telegram_group.get_chats, phone, channel_username, limit)
        return {"status": "starting fetch group messages", "username": channel_username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ok
@router.get("/api/group/members")
async def get_group_members(
    background_tasks: BackgroundTasks,
    phone: str = Query(...),
    channel_username: str = Query(...),
    limit: int = Query(10)
):
    try:
        background_tasks.add_task(telegram_group.get_members, phone, channel_username, limit)
        return {"status": "starting fetch group messages", "username": channel_username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ok
@router.get("/api/devices")
async def get_devices(query: str | None = Query(default=None),):
    try:
        return telegram_controller.list_devices(query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ok
@router.get("/api/group/detail")
async def get_group_detail(phone: str = Query(...), strid: str = Query(...)):
    try:
        return await telegram_group.detail(phone,strid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------- untested ------

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


@router.get("/api/read_all_messages")
async def read_all_messages(
    phone: str = Query(...),
    channel_username: str = Query(...),
    limit: int = Query(10)
) -> Dict[str, Any]:
    try:
        response = await telegram_message.read_all_messages(phone, channel_username, limit)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))