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


async def get_all_channels(phone: str) -> ChannelNamesResponseAll:
    client = sessions.get(phone)

    if not client:
        logging.error(f"Session not found for phone: {phone}")
        raise HTTPException(status_code=404, detail="Session not found")

    logging.debug(f"Session found for phone: {phone}")

    if not client.is_connected():
        logging.debug(f"Connecting client for phone: {phone}")
        await client.connect()

    try:
        dialogs = await client.get_dialogs()
        logging.debug(f"Retrieved dialogs for phone: {phone}")

        channels = []
        groups = []

        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel):
                name = f"@{entity.username}" if entity.username else f"@{entity.title}"
                channels.append({'name_channel_group': name, 'status': True})
            elif isinstance(entity, Chat):
                name = f"@{entity.title}"
                groups.append({'name_channel_group': name, 'status': False})

        logging.debug(f"Extracted channel and group names for phone: {phone}")

        response = ChannelNamesResponseAll(
            total_channels=len(channels),
            total_groups=len(groups),
            channels_groups=channels + groups
        )

        logging.debug(f"Client disconnected for phone: {phone}")
        # Jika Anda ingin mendisconnect, aktifkan baris berikut
        # await client.disconnect()

        return response

    except ChannelsTooMuchError as e:
        logging.error(f"Failed to get channels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")
    except Exception as e:
        logging.error(f"Failed to get channels and groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels and groups: {str(e)}")