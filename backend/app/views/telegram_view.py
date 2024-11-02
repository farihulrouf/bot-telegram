from fastapi import APIRouter, HTTPException, Depends
from app.models.telegram_model import PhoneNumber, VerificationCode, SendMessageRequest, ChannelDetailResponse, BulkSendMessageRequest
from app.controllers import auth_controller, telegram_controller, chanel_group_handler
from app.models.user import UserCreate, UserOut, Token, UserLogin
from app.database.db import get_db  # Pastikan import ini benar
from sqlalchemy.orm import Session

router = APIRouter()

async def handle_background_task(func, *args):
    """Helper function to handle background tasks."""
    return await func(*args)

@router.post("/api/login")
async def login(phone: PhoneNumber):
    """Handles login requests."""
    await handle_background_task(auth_controller.login, phone)
    return {"status": "success", "phone": phone, "message": "requesting token"}

@router.post("/api/verify")
async def verify(code: VerificationCode):
    """Handles verification requests."""
    return await auth_controller.verify(code)

@router.post("/api/logout")
async def logout(phone: PhoneNumber):
    """Handles logout requests."""
    return await auth_controller.logout(phone)

@router.post("/api/send_message")
async def send_message_endpoint(request: SendMessageRequest):
    """Handles sending messages."""
    return await telegram_controller.send_message(request.phone, request.recipient, request.message, request.type, request.caption)

@router.post("/api/send_bulk_message")
async def send_bulk_message_endpoint(request: BulkSendMessageRequest):
    """Handles bulk sending messages."""
    return await telegram_controller.send_bulk_message(request.phone, request.recipients, request.message)

@router.get("/api/getallchannel")
async def fetch_all_channels(phone: str):
    """Fetches all channels."""
    return await telegram_controller.get_all_channels(phone)

@router.get("/api/getchannel", response_model=ChannelDetailResponse)
async def get_channel_details(phone: str, channel_username: str):
    """Fetches channel details."""
    response = await chanel_group_handler.get_channel_details(phone, channel_username)
    if response["status"] != "success":
        raise HTTPException(status_code=400, detail="Failed to get channel details")
    return response["channel_info"]

@router.post("/api/register", response_model=UserOut)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Handles user registration."""
    if auth_controller.get_user(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return auth_controller.create_user(db, user)

@router.post("/api/token", response_model=Token)
async def get_token(user: UserLogin, db: Session = Depends(get_db)):
    """Handles user authentication and returns a token."""
    user_auth = await auth_controller.authenticate_user(db, user.username, user.password)
    if not user_auth:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = auth_controller.create_access_token(data={"sub": user_auth.username})
    return {"access_token": access_token, "token_type": "bearer"}
