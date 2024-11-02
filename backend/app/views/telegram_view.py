from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer
from app.models.telegram_model import (
    PhoneNumber, VerificationCode, SendMessageRequest, 
    ChannelDetailResponse, BulkSendMessageRequest
)
from app.controllers import auth_controller, telegram_controller, chanel_group_handler
from app.models.user import UserCreate, UserOut, Token, UserLogin
from app.database.db import get_db  # Ensure this import is correct
from sqlalchemy.orm import Session

# Define the OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# Define the router
router = APIRouter()

# Define a function to get the current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify the token
    user = auth_controller.verify_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    return user

# Helper function for handling background tasks
async def handle_background_task(func, *args):
    return await func(*args)

# Unprotected route: /api/register
@router.post("/api/register", response_model=UserOut)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if auth_controller.get_user(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return auth_controller.create_user(db, user)

# Unprotected route: /api/token
@router.post("/api/token", response_model=Token)
async def get_token(user: UserLogin, db: Session = Depends(get_db)):
    user_auth = await auth_controller.authenticate_user(db, user.username, user.password)
    if not user_auth:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = auth_controller.create_access_token(data={"sub": user_auth.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Protected route: /api/login
@router.post("/api/login", dependencies=[Depends(get_current_user)])
async def login(phone: PhoneNumber):
    await handle_background_task(auth_controller.login, phone)
    return {"status": "success", "phone": phone, "message": "requesting token"}

# Protected route: /api/verify
@router.post("/api/verify", dependencies=[Depends(get_current_user)])
async def verify(code: VerificationCode):
    return await auth_controller.verify(code)

# Protected route: /api/logout
@router.post("/api/logout", dependencies=[Depends(get_current_user)])
async def logout(phone: PhoneNumber):
    return await auth_controller.logout(phone)

# Protected route: /api/send_message
@router.post("/api/send_message", dependencies=[Depends(get_current_user)])
async def send_message_endpoint(request: SendMessageRequest):
    return await telegram_controller.send_message(request)

# Protected route: /api/send_bulk_message
@router.post("/api/send_bulk_message", dependencies=[Depends(get_current_user)])
async def send_bulk_message_endpoint(request: BulkSendMessageRequest):
    return await telegram_controller.send_bulk_message(
        request.phone, request.recipients, request.message
    )

# Protected route: /api/getallchannel
@router.get("/api/getallchannel", dependencies=[Depends(get_current_user)])
async def fetch_all_channels(phone: str):
    return await telegram_controller.get_all_channels(phone)

# Protected route: /api/getchannel
@router.get("/api/getchannel", response_model=ChannelDetailResponse, dependencies=[Depends(get_current_user)])
async def get_channel_details(phone: str, channel_username: str):
    response = await chanel_group_handler.get_channel_details(phone, channel_username)
    if response["status"] != "success":
        raise HTTPException(status_code=400, detail="Failed to get channel details")
    return response["channel_info"]
