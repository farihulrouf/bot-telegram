import os
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient

# Load environment variables from .env file
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

# Dictionary for active sessions and clients
sessions = {}  # Pastikan sessions didefinisikan di sini

# Daftar origins yang diizinkan
origins = [
    "http://localhost:8080",  # Ganti dengan URL frontend Anda
    # Tambahkan lebih banyak origin jika diperlukan
]

def create_client(phone: str) -> TelegramClient:
    session_file = f"sessions/{phone}.session"
    return TelegramClient(session_file, int(API_ID), API_HASH)

# Fungsi untuk menambahkan middleware CORS
def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # Daftar origins yang diizinkan
        allow_credentials=True,
        allow_methods=["*"],  # Atau ['GET', 'POST', ...] untuk membatasi metode
        allow_headers=["*"],  # Atau list khusus header yang diizinkan
    )
