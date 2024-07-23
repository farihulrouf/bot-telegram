from fastapi import FastAPI
from app.views import telegram_view

app = FastAPI()

# Mengimpor router
app.include_router(telegram_view.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
