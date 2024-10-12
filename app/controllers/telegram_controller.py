from typing import Dict
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from app.models.telegram_model import sessions  # Asumsi Anda menyimpan session di sini

async def send_message(phone: str, recipient: str, message: str) -> Dict[str, str]:
    """Send a message to a user, group, or channel."""
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
