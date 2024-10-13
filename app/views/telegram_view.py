from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from app.models.telegram_model import PhoneNumber, VerificationCode, SendMessageRequest
from app.controllers import auth_controller, telegram_controller

router = APIRouter()

@router.post("/api/login")
async def login(background_tasks: BackgroundTasks, phone: PhoneNumber):
    try:
        background_tasks.add_task(auth_controller.login, phone)
        return {"status": "success", "phone": phone, "message": "requesting token"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/verify")
async def verify(code: VerificationCode):
    try:
        return await auth_controller.verify(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/logout")
async def logout(phone: PhoneNumber):
    """Endpoint untuk logout dari Telegram."""
    try:
        # Memanggil fungsi logout dari auth_controller
        response = await auth_controller.logout(phone)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/api/send_message")
async def send_message_endpoint(request: SendMessageRequest):
    try:
        # Menggunakan fungsi controller untuk mengirim pesan
        result = await telegram_controller.send_message(request.phone, request.recipient, request.message)
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/api/getallchannel")
async def fetch_all_channels(phone: str):
    return await telegram_controller.get_all_channels(phone)