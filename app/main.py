from fastapi import FastAPI
import asyncio
import os  # Pastikan modul os diimpor
from app.models.telegram_model import create_client, read_messages, sessions
from app.views import telegram_view
app = FastAPI()

# Fungsi untuk mendapatkan nomor telepon dari nama file session
def get_phone_number_from_session_file():
    session_files = os.listdir('sessions')
    for session_file in session_files:
        if session_file.endswith('.session'):
            phone_number = session_file.split('.')[0]
            return phone_number
    return None

# Mengambil nomor telepon dari file session
phone_number = get_phone_number_from_session_file()

if not phone_number:
    raise ValueError("No session file found or invalid session file format.")

# Mengimpor router
app.include_router(telegram_view.router)

@app.on_event("startup")
async def startup_event():
    # Buat dan simpan client
    client = create_client(phone_number)
    sessions[phone_number] = client
    # Jalankan fungsi read_messages di background
    asyncio.create_task(read_messages(phone_number))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
