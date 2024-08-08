from fastapi import FastAPI
import asyncio
import os  # Pastikan modul os diimpor
from app.models.telegram_model import create_client, read_messages, sessions
from app.views import telegram_view
app = FastAPI()



# Mengimpor router
app.include_router(telegram_view.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
