from fastapi import HTTPException
from typing import Dict
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from app.models.telegram_model import sessions, ChannelNamesResponseAll  # Asumsi Anda menyimpan session di sini
from typing import List, Dict, Any
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import PeerChannel, Channel, Chat, PeerChannel
from telethon.errors.rpcerrorlist import ChannelsTooMuchError

import logging
async def send_message(phone: str, recipient: str, message: str) -> Dict[str, str]:
    """Send a message to a user, group, or channel."""
    print("check", phone)

    client: TelegramClient = sessions.get(phone)

    if client is None:
        return {
            "status": "error",
            "message": "No active client session found."
        }

    try:
        if not client.is_connected():
            await client.connect()

        # Mengirim pesan
        await client.send_message(recipient, message)

        return {
            "status": "success",
            "message": "Message sent successfully."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send message: {str(e)}"
        }


async def send_bulk_message(phone: str, recipients: List[str], message: str) -> List[Dict[str, str]]:
    """Send a message to multiple users, groups, or channels."""
    client: TelegramClient = sessions.get(phone)

    if client is None:
        return [{
            "status": "error",
            "message": "No active client session found."
        }]

    results = []
    
    try:
        if not client.is_connected():
            await client.connect()

        for recipient in recipients:
            try:
                await client.send_message(recipient, message)
                results.append({
                    "recipient": recipient,
                    "status": "success",
                    "message": "Message sent successfully."
                })
            except Exception as e:
                results.append({
                    "recipient": recipient,
                    "status": "error",
                    "message": f"Failed to send message to {recipient}: {str(e)}"
                })

        return results

    except Exception as e:
        return [{
            "status": "error",
            "message": f"Failed to send bulk messages: {str(e)}"
        }]

# Fungsi utama untuk mendapatkan semua channel dan group
async def get_all_channels(phone: str) -> ChannelNamesResponseAll:
    # Mendapatkan client dari sesi yang tersedia berdasarkan nomor telepon
    client = sessions.get(phone)

    if not client:
        logging.error(f"Session not found for phone: {phone}")
        raise HTTPException(status_code=404, detail="Session not found")

    logging.debug(f"Session found for phone: {phone}")

    # Menghubungkan client jika belum terkoneksi
    if not client.is_connected():
        logging.debug(f"Connecting client for phone: {phone}")
        await client.connect()

    try:
        # Mengambil dialog dari client
        dialogs = await client.get_dialogs()
        logging.debug(f"Retrieved dialogs for phone: {phone}")

        channels = []
        groups = []

        # Iterasi melalui semua dialog untuk memisahkan channel dan group
        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel):
                name = f"@{entity.username}" if entity.username else f"@{entity.title}"
                channels.append({
                    'name_channel_group': name, 
                    'status': True,  # Status True untuk channel
                    'id_channel_group': entity.id  # ID dari channel
                })
            elif isinstance(entity, Chat):
                name = f"@{entity.title}"
                groups.append({
                    'name_channel_group': name, 
                    'status': False,  # Status False untuk group
                    'id_channel_group': entity.id  # ID dari group
                })

        logging.debug(f"Extracted channel and group names for phone: {phone}")

        # Membuat respons dari data channel dan group yang diperoleh
        response = ChannelNamesResponseAll(
            total_channels=len(channels),
            total_groups=len(groups),
            channels_groups=channels + groups  # Gabungkan channels dan groups
        )

        logging.debug(f"Client disconnected for phone: {phone}")
        # Jika Anda ingin mendisconnect client setelah selesai, aktifkan baris berikut
        # await client.disconnect()

        return response

    except ChannelsTooMuchError as e:
        logging.error(f"Failed to get channels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")
    except Exception as e:
        logging.error(f"Failed to get channels and groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels and groups: {str(e)}")