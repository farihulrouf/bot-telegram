import logging
import os
import asyncio
from typing import Dict, Union
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from fastapi.encoders import jsonable_encoder
from app.models.telegram_model import PhoneNumber, VerificationCode, create_client, sessions, active_clients
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.models.user import UserCreate, User
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Security, Depends
from app.models.user import TokenData

# Setup untuk hashing password
# Load environment variables
load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def list_devices(query: str = None) -> Dict[str, Union[str, list]]:
    """List devices based on the query."""
    devices = [v for v in sessions.keys() if query is None or query in v]
    return {
        "status": "success",
        "data": devices
    }

# Saat login, menyimpan client dan phone_code_hash
async def login(phone: PhoneNumber) -> Dict[str, str]:
    try:
        client = create_client(phone.phone)
        await client.connect()
        sent_code = await client.send_code_request(phone.phone)
        
        # Simpan client dan phone_code_hash dalam dictionary
        sessions[phone.phone] = {
            'client': client,
            'phone_code_hash': sent_code.phone_code_hash
        }
        logging.debug(f"Session created and stored for phone: {phone.phone}")
        return {"status": "code_sent"}
    except Exception as e:
        logging.error(f"Login failed for {phone.phone}: {str(e)}")
        raise Exception(f"Failed to login: {str(e)}")

async def verify(code: VerificationCode):
    try:
        # Ambil session data
        session_data = sessions.get(code.phone)
        if not session_data:
            raise Exception("Session not found")

        # Ambil client dan phone_code_hash dari session data
        client = session_data['client']
        phone_code_hash = session_data['phone_code_hash']

        if not client.is_connected():
            await client.connect()

        # Gunakan phone_code_hash dalam proses sign in
        await client.sign_in(code.phone, code.code, phone_code_hash=phone_code_hash)

        if await client.is_user_authorized():
            return {"status": "success", "message": "User authorized"}
        else:
            raise Exception("Verification failed.")

    except Exception as e:
        logging.error(f"Error in verify: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



async def handle_authorized_user(client: TelegramClient) -> Dict[str, Union[str, Dict]]:
    """Handle actions after the user is authorized."""
    me = await client.get_me()
    me_dict = process_bytes_in_dict(me.to_dict())
    logging.debug(f"User logged in: {me}")
    return {"status": "logged_in", "user": jsonable_encoder(me_dict)}

async def logout(phone: PhoneNumber) -> Dict[str, str]:
    """Log out from Telegram and clean up the session."""
    try:
        client = sessions.get(phone.phone)
        if client:
            if not client.is_connected():
                await client.connect()
            await client.log_out()
            logging.debug(f"Successfully logged out for phone: {phone.phone}")

            del sessions[phone.phone]
            cancel_active_task(phone.phone)

            return {
                "status": "success",
                "message": f"Client {phone.phone} successfully removed"
            }

        return {
            "status": "error",
            "message": "No active client"
        }

    except Exception as e:
        logging.error(f"Logout failed for {phone.phone}: {str(e)}")
        raise Exception(f"Failed to logout: {str(e)}")

def cancel_active_task(phone_number: str):
    # Misalkan Anda memiliki struktur task yang menyimpan aktifitas
    if phone_number in active_tasks:
        task = active_tasks[phone_number]
        if not task.done():
            task.cancel()  # Membatalkan task yang aktif
        del active_tasks[phone_number]  # Menghapus dari daftar task aktif


def process_bytes_in_dict(data: dict) -> dict:
    """Recursively process bytes in a dictionary and convert them to strings."""
    for key, value in data.items():
        if isinstance(value, bytes):
            data[key] = value.decode('utf-8', errors='replace')
        elif isinstance(value, dict):
            data[key] = process_bytes_in_dict(value)
        elif isinstance(value, list):
            data[key] = [process_bytes_in_dict(v) if isinstance(v, dict) else v for v in value]
    return data


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, username: str) -> User:
    return db.query(User).filter(User.username == username).first()

async def authenticate_user(db: Session, username: str, password: str) -> User:
    user = get_user(db, username)
    if user is None or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logging.warning("Username is None in payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username)
    except JWTError as e:
        logging.error(f"JWT error occurred: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
