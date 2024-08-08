from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from app.models.telegram_model import sessions
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.utils.utils import sanitize_filename, extract_and_join_channels
import re

async def read_all_messages(phone: str, channel_identifier: str, limit: Optional[int] = None) -> Dict[str, Any]:
    client = sessions.get(phone)
    if not client:
        raise HTTPException(status_code=404, detail="Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        # Check if identifier is an ID or username
        try:
            # Try to get entity by ID
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        except ValueError:
            # Not an integer, so assume it's a username
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            entity = await client.get_entity(channel_identifier)

        # Fallback if username is not available
        if not entity.username:
            channel_name = str(entity.id)
        else:
            channel_name = entity.username

        all_messages = []
        offset_id = 0
        remaining_limit = limit if limit is not None else float('inf')  # Use infinity if limit is None

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
                media_info = None

                # Handle media
                if message.media:
                    media_type = "unknown"
                    media_path = None

                    if isinstance(message.media, MessageMediaPhoto):
                        media_type = "photo"
                        file_extension = 'jpg'  # Assume jpg for photos
                        file_name = next(
                            (attr.file_name for attr in message.media.photo.sizes if hasattr(attr, 'file_name')), 
                            f"photo_{message.id}.{file_extension}"
                        )
                        file_name = sanitize_filename(file_name)  # Clean the file name
                        media_path = get_file_url(message.media.photo.id, channel_name, file_name)
                    elif isinstance(message.media, MessageMediaDocument):
                        media_type = "file"  # For files like docs
                        file = message.media.document
                        # Safely handle file_name
                        file_name = 'unknown_file'
                        if hasattr(file, 'attributes') and file.attributes:
                            for attr in file.attributes:
                                if hasattr(attr, 'file_name'):
                                    file_name = attr.file_name
                                    break
                        file_name = sanitize_filename(file_name)  # Clean the file name
                        media_path = get_file_url(file.id, channel_name, file_name)
                    
                    media_info = {
                        "type": media_type,
                        "path": media_path
                    }

                # Detect mentions of channels in message text
                #if message.message:
                #    await extract_and_join_channels(client, message.message)

                all_messages.append({
                    "username": channel_name,
                    "sender_id": message.sender_id,
                    "text": message.message,
                    "date": message.date.isoformat(),
                    "media": media_info
                })

            offset_id = messages.messages[-1].id
            remaining_limit -= len(messages.messages)

        return {
            "status": "messages_received",
            "total_messages_read": len(all_messages),
            "messages": all_messages
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read messages: {str(e)}")
    finally:
        await client.disconnect()

def get_file_url(file_id: str, channel_username: str, file_name: Optional[str] = None) -> str:
    # Construct file path
    if file_name:
        file_path = f"dragonfly/telegram/{channel_username}/{file_name}"
    else:
        file_path = f"dragonfly/telegram/{channel_username}/{file_id}"
    
    # Construct URL
    return f"https://dragonfly.sgp1.digitaloceanspaces.com/{file_path}"
