import re
import logging
from typing import Dict, Any, Optional
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Channel  # Mengimpor hanya Channel
from fastapi import HTTPException
from app.models.telegram_model import sessions

# Mengatur level logging
logging.basicConfig(level=logging.DEBUG)

# Regex untuk mendeteksi URL
URL_REGEX = re.compile(r'(https?://[^\s]+)')

async def read_all_messages(phone: str, channel_identifier: str, limit: Optional[int] = None) -> Dict[str, Any]:
    client = sessions.get(phone)
    if not client:
        raise HTTPException(status_code=404, detail="Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        # Mencoba mendapatkan entitas dengan ID atau username
        try:
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        except ValueError:
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            entity = await client.get_entity(channel_identifier)

        # Memastikan entitas adalah Channel
        if not isinstance(entity, Channel):
            raise HTTPException(status_code=400, detail="Provided identifier is not a channel.")

        channel_name = entity.username if entity.username else str(entity.id)

        all_messages = []
        offset_id = 0
        remaining_limit = limit if limit is not None else float('inf')

        while remaining_limit > 0:
            batch_limit = min(remaining_limit, 100)
            messages = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=batch_limit,
                max_id=0,
                min_id=0,
                hash=0
            ))

            if not messages.messages:
                break

            for message in messages.messages:
                print("cek data", message)

                # Deteksi dan proses URL dalam teks pesan
                urls = URL_REGEX.findall(message.message or "")
                # URL yang diproses sekarang diabaikan

                all_messages.append({
                    "username": channel_name,
                    "sender_id": message.sender_id,
                    "text": message.message,
                    "date": message.date.isoformat(),
                    "views": message.views,
                    "forwards": message.forwards,
                    "edit_date": message.edit_date,
                })

            offset_id = messages.messages[-1].id
            remaining_limit -= len(messages.messages)

        return {
            "status": "messages_received",
            "total_messages_read": len(all_messages),
            "messages": all_messages
        }

    except Exception as e:
        logging.error(f"Failed to read messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read messages: {str(e)}")
