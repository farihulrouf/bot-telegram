from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, Channel, Chat
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import requests
from typing import Dict, List
import logging
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
webhook_url = os.getenv('WEBHOOK_URL')

# Dictionary untuk menyimpan sesi aktif
sessions = {}

# Active clients
active_clients: Dict[str, asyncio.Task] = {}


class FileDetails(BaseModel):
    name: str
    size: int

class ListDataResponse(BaseModel):
    status: str
    total_files: int
    files: List[FileDetails]

class WebhookPayload(BaseModel):
    sender_id: int
    chat_id: int
    message: str
    date: str
    media: str = None
    
class ContactResponse(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    username: Optional[str]

class ChannelGroup(BaseModel):
    name_channel_group: str
    status: bool

class ChannelDetailResponse(BaseModel):
    id: int
    name: str
    username: str
    participants_count: int
    admins_count: int
    banned_count: int
    description: str
    created_at: str

class ChannelNamesResponseAll(BaseModel):
    total_channels: int
    total_groups: int
    channels_groups: List[ChannelGroup]
    
class SendMessageRequest(BaseModel):
    phone: str
    recipient: str
    message: str

class ChannelNamesResponse(BaseModel):
    total_channel: int
    name_channel: List[str]

class TextRequest(BaseModel):
    text: str

class JoinRequest(BaseModel):
    phone: str
    username_channel: str

class PhoneNumber(BaseModel):
    phone: str

class VerificationCode(BaseModel):
    phone: str
    code: str
    password: str = None

class GroupSearchRequest(BaseModel):
    phone: str
    query: str

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

    async def handle_message(event):
        # Buat payload untuk dikirim ke webhook
        payload = {
            'sender_id': event.sender_id,
            'chat_id': event.chat_id,
            'message': event.message.message,
            'date': event.message.date.isoformat()
        }

        print("Received message:")
        print(f"Sender ID: {event.sender_id}")
        print(f"Chat ID: {event.chat_id}")
        print(f"Message: {event.message.message}")
        print(f"Date: {event.message.date.isoformat()}")

        # Tambahkan media jika ada
        if isinstance(event.message.media, MessageMediaPhoto):
            payload['media'] = 'photo'
        elif isinstance(event.message.media, MessageMediaDocument):
            payload['media'] = 'document'
        
        # Kirim payload ke webhook
        try:
            #response = requests.post(webhook_url, json=payload)
            #response.raise_for_status()
            logging.info(f"Payload sent successfully: {payload}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send payload: {e}")

    # Tambahkan event handler untuk menangani pesan baru
    client.add_event_handler(handle_message, events.NewMessage)

    if await client.is_user_authorized():
        # Menjaga agar client tetap terhubung dan aktif untuk memproses pesan
        try:
            await client.run_until_disconnected()
        except KeyboardInterrupt:
            print("Disconnected due to user interrupt")
        finally:
            await client.disconnect()
    else:
        await client.disconnect()

    return {"status": "messages_received"}
