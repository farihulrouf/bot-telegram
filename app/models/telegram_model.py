from pydantic import BaseModel
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerUser
from dotenv import load_dotenv
import os
import asyncio

# Muat variabel lingkungan dari file .env
load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

# Dictionary untuk menyimpan sesi aktif
sessions = {}

class PhoneNumber(BaseModel):
    phone: str

class VerificationCode(BaseModel):
    phone: str
    code: str
    password: str = None

def create_client(phone: str) -> TelegramClient:
    # Menggunakan file sesi yang dinamai dengan nomor telepon
    session_file = f"sessions/{phone}.session"
    return TelegramClient(session_file, int(api_id), api_hash)

async def read_messages(phone: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")

    if not client.is_connected():
        await client.connect()

    messages = []

    async def handler(event):
        messages.append({
            "sender_id": event.sender_id,
            "text": event.message.text,
            "chat_id": event.chat_id
        })

    client.add_event_handler(handler, events.NewMessage)

    await asyncio.sleep(10)  # Tunggu 10 detik atau sesuaikan sesuai kebutuhan

    await client.disconnect()
    return {"status": "messages_received", "messages": messages}



