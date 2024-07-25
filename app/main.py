from fastapi import FastAPI
import asyncio
from app.models.telegram_model import create_client, read_messages, PhoneNumber, sessions

app = FastAPI()

# Nomor telepon yang digunakan
phone_number = '+6285280933757'  # Ganti dengan nomor telepon Anda

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
