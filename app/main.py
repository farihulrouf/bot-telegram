from fastapi import FastAPI
import asyncio
import os
from app.models.telegram_model import create_client, read_messages, sessions
from app.views import telegram_view

app = FastAPI()

# Mengimpor router
app.include_router(telegram_view.router)

@app.on_event("startup")
async def startup_event():
    # Mulai mendengarkan pesan untuk setiap nomor telepon di sessions
    for phone, client in sessions.items():
        if not client.is_connected():
            await client.connect()

        # Mulai mendengarkan pesan
        asyncio.create_task(read_messages(phone))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
