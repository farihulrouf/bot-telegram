from fastapi import FastAPI, BackgroundTasks
import asyncio
import os
from app.models.telegram_model import create_client, sessions, active_clients
from app.views import telegram_view

app = FastAPI()

# Mengimpor router
app.include_router(telegram_view.router)

@app.on_event("startup")
async def startup_event():
    # Mulai mendengarkan pesan untuk setiap nomor telepon di sessions
    for phone, client in sessions.items():
        # Menambahkan client ke active_clients
        active_clients[phone] = client
        # Anda bisa melakukan operasi lain di sini jika diperlukan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
