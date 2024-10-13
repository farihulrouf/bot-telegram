import logging
import os
import asyncio
from typing import Dict, Union
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from fastapi.encoders import jsonable_encoder
from app.models.telegram_model import PhoneNumber, VerificationCode, create_client, sessions, active_clients

# Load environment variables
load_dotenv()

def list_devices(query: str = None) -> Dict[str, Union[str, list]]:
    """List devices based on the query."""
    devices = [v for v in sessions.keys() if query is None or query in v]
    return {
        "status": "success",
        "data": devices
    }

async def login(phone: PhoneNumber) -> Dict[str, str]:
    """Log in to Telegram using the specified phone number."""
    try:
        client = create_client(phone.phone)
        await client.connect()
        await client.send_code_request(phone.phone)
        sessions[phone.phone] = client
        logging.debug(f"Session created and stored for phone: {phone.phone}")
        return {"status": "code_sent"}
    except Exception as e:
        logging.error(f"Login failed for {phone.phone}: {str(e)}")
        raise Exception(f"Failed to login: {str(e)}")

async def verify(code: VerificationCode) -> Dict[str, Union[str, Dict]]:
    """Verify the login code and sign in the user."""
    try:
        client = sessions.get(code.phone)
        if not client:
            raise Exception("Session not found")

        if not client.is_connected():
            await client.connect()

        await client.sign_in(code.phone, code.code)

        if await client.is_user_authorized():
            return await handle_authorized_user(client)

        elif code.password:
            await client.sign_in(password=code.password)
            return await handle_authorized_user(client)
        else:
            raise Exception("2FA required but no password provided")

    except SessionPasswordNeededError:
        logging.debug("2FA is required for this account")
        return {"status": "2fa_required"}
    except Exception as e:
        logging.error(f"Failed to verify code: {str(e)}")
        raise Exception(f"Failed to verify code: {str(e)}")

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
