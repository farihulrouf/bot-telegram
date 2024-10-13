# app/utils/utils.py

import os
from telethon import TelegramClient

# Load environment variables from .env file
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

# Dictionary for active sessions and clients
sessions = {}  # Pastikan sessions didefinisikan di sini

def create_client(phone: str) -> TelegramClient:
    session_file = f"sessions/{phone}.session"
    return TelegramClient(session_file, int(API_ID), API_HASH)
