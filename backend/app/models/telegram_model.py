import os
import time
import asyncio
import logging
from typing import Dict, List,Optional
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

class ChannelGroup(BaseModel):
    name_channel_group: str
    id_channel_group: int  # ID dari channel atau group
    status: bool


# Definisikan model respons untuk anggota
class MemberResponse(BaseModel):
    id: int  # ID pengguna
    username: Optional[str] = "No Username"  # Username pengguna
    phone: Optional[str]  # Nomor telepon pengguna

# Definisikan model respons untuk detail channel
class ChannelDetailResponse(BaseModel):
    id: int  # ID unik channel
    name: str  # Nama channel
    username: Optional[str]  # Username channel
    participants_count: int  # Jumlah peserta dalam channel
    admins_count: int  # Jumlah admin di channel
    banned_count: int  # Jumlah peserta yang dilarang
    description: Optional[str]  # Deskripsi channel
    created_at: str  # Tanggal pembuatan channel
    members: List[MemberResponse]  # Daftar anggota



class BulkSendMessageRequest(BaseModel):
    phone: str
    recipients: List[str]
    message: str

class ChannelNamesResponseAll(BaseModel):
    total_channels: int
    total_groups: int
    channels_groups: List[ChannelGroup]

def create_client(phone: str) -> TelegramClient:
    session_file = f"sessions/{phone}.session"
    return TelegramClient(session_file, int(API_ID), API_HASH)


def sanitize_filename(filename: str) -> str:
    return "".join(c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename)
