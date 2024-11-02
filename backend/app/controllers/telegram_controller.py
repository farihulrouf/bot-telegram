from fastapi import HTTPException
from typing import Dict
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from app.models.telegram_model import sessions, ChannelNamesResponseAll, SendMessageRequest  # Asumsi Anda menyimpan session di sini
from typing import List, Dict, Any
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import PeerChannel, Channel, Chat, PeerChannel
from telethon.errors.rpcerrorlist import ChannelsTooMuchError
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.types import Contact
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def send_message(request: SendMessageRequest):
    """Send a message to a Telegram group or channel."""
    client: TelegramClient = sessions.get(request.phone)

    if client is None:
        return {
            "status": "error",
            "message": "No active client session found."
        }

    try:
        if not client.is_connected():
            await client.connect()

        # Mengirim pesan berdasarkan tipe
        if request.type == "text":
            await client.send_message(request.recipient, request.message)
            return {
                "status": "success",
                "message": "Text message sent successfully."
            }
        elif request.type in ["image", "video", "file"]:
            await client.send_file(request.recipient, request.message, caption=request.caption)
            return {
                "status": "success",
                "message": f"{request.type.capitalize()} sent successfully."
            }
        else:
            return {
                "status": "error",
                "message": "Unsupported message type."
            }

    except Exception as e:
        logging.error(f"Failed to send message: {str(e)}")  # Mencatat error ke log
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
        logger.error(f"Session not found for phone: {phone}")
        raise HTTPException(status_code=404, detail="Session not found")

    logger.debug(f"Session found for phone: {phone}")

    # Menghubungkan client jika belum terkoneksi
    if not client.is_connected():
        logger.debug(f"Connecting client for phone: {phone}")
        await client.connect()

    try:
        # Mengambil dialog dari client
        dialogs = await client.get_dialogs()
        logger.debug(f"Retrieved {len(dialogs)} dialogs for phone: {phone}")

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

        logger.debug(f"Extracted {len(channels)} channels and {len(groups)} groups for phone: {phone}")

        # Membuat respons dari data channel dan group yang diperoleh
        response = ChannelNamesResponseAll(
            total_channels=len(channels),
            total_groups=len(groups),
            channels_groups=channels + groups  # Gabungkan channels dan groups
        )
        
        #logger.debug(f"Total channels: {response.total_channels}, Total groups: {response.total_groups}")

        # Jika Anda ingin mendisconnect client setelah selesai, aktifkan baris berikut
        # await client.disconnect()

        return response

    except ChannelsTooMuchError as e:
        logger.error(f"Failed to get channels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get channels and groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels and groups: {str(e)}")


async def get_all_contacts(phone: str) -> Dict[str, Any]:
    """Get all contacts for a given phone session."""
    client = sessions.get(phone)

    if not client:
        logger.error(f"Session not found for phone: {phone}")
        raise HTTPException(status_code=404, detail="Session not found")

    logger.debug(f"Session found for phone: {phone}")

    if not client.is_connected():
        logger.debug(f"Connecting client for phone: {phone}")
        await client.connect()

    try:
        contacts = await client(GetContactsRequest(0))  # 0 untuk mengambil semua kontak
        logger.debug(f"Retrieved {len(contacts.contacts)} contacts for phone: {phone}")

        contact_list = []
        
        for contact in contacts.contacts:
            if isinstance(contact, Contact):
                # Ambil user_id dari contact
                user_id = contact.user_id  # user_id dari Contact
                username = None
                # Ambil informasi pengguna menggunakan user_id
                if user_id:
                    try:
                        user = await client.get_entity(user_id)
                        username = f"@{user.username}" if user.username else None

                    except Exception as e:
                        logger.warning(f"Could not retrieve user for contact {contact}: {str(e)}")

                contact_list.append({
                    "username": username,
                    "id_user": user_id,
                })

        return {
            "total_contact": len(contact_list),
            "contacts": contact_list
        }

    except Exception as e:
        logger.error(f"Failed to get contacts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get contacts: {str(e)}")