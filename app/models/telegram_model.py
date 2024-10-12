import os
import time
import asyncio
import logging
from typing import Dict, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Load environment variables from .env file
load_dotenv()

# Constants for API credentials
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

# Dictionary for active sessions and clients
sessions: Dict[str, TelegramClient] = {}
active_clients: Dict[str, asyncio.Task] = {}

# Global variables
senders = {}
start_time = time.time()


class PhoneNumber(BaseModel):
    phone: str


class VerificationCode(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None


class SendMessageRequest(BaseModel):
    phone: str  # Nomor telepon pengirim
    recipient: str  # Username atau nomor telepon penerima
    message: str  # Pesan yang akan dikirim


def create_client(phone: str) -> TelegramClient:
    session_file = f"sessions/{phone}.session"
    return TelegramClient(session_file, int(API_ID), API_HASH)


def sanitize_filename(filename: str) -> str:
    return "".join(c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename)
