import re
import logging
from typing import List, Dict, Any, Optional
from telethon.tl.functions.messages import GetHistoryRequest, ImportChatInviteRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError, ChatAdminRequiredError
from fastapi import HTTPException
from app.models.telegram_model import sessions
from app.utils.utils import sanitize_filename
from app.utils.encode_emoji import encode_emoji_to_base64

# Regex for detecting URLs
URL_REGEX = re.compile(r'(https?://[^\s]+)')

async def read_all_messages(phone: str, channel_identifier: str, limit: Optional[int] = None) -> Dict[str, Any]:
    client = sessions.get(phone)
    if not client:
        raise HTTPException(status_code=404, detail="Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        # Determine if identifier is an ID or username
        try:
            # Try to get entity by ID
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        except ValueError:
            # Not an integer, assume it's a username
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            entity = await client.get_entity(channel_identifier)

        # Determine if the entity is a channel or group
        if entity.broadcast:  # This checks if it's a channel
            channel_name = entity.username if entity.username else str(entity.id)
        else:  # Assume it's a group
            channel_name = entity.title if entity.title else "Group Description"

        all_messages = []
        offset_id = 0
        remaining_limit = limit if limit is not None else float('inf')  # Use infinity if no limit

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
                    media_info = await handle_media(message, channel_name)

                # Detect and process URLs in message text
                urls = URL_REGEX.findall(message.message or "")
                for url in urls:
                    if "t.me/joinchat/" in url:
                        await process_invite_url(url, client)
                
                # Handle reactions
                reactions_info = None
                if message.reactions:
                    reactions_info = {
                        "results": [
                            {
                                "reaction": encode_emoji_to_base64(reaction.reaction.emoticon),
                                "count": reaction.count
                            }
                            for reaction in message.reactions.results
                        ],
                        "min": message.reactions.min,
                        "can_see_list": message.reactions.can_see_list,
                        "reactions_as_tags": message.reactions.reactions_as_tags,
                        "recent_reactions": message.reactions.recent_reactions
                    }
                else:
                    reactions_info = None  # Explicitly set to None if reactions are not present

                all_messages.append({
                    "username": channel_name,
                    "sender_id": message.sender_id,
                    "text": message.message,
                    "date": message.date.isoformat(),
                    "media": media_info,
                    "views": message.views,
                    "forwards": message.forwards,
                    "edit_date": message.edit_date,
                    "reactions": reactions_info
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
    finally:
        await client.disconnect()

async def handle_media(message, channel_name):
    media_info = {
        "type": "unknown",
        "path": None
    }

    if isinstance(message.media, MessageMediaPhoto):
        media_info["type"] = "photo"
        file_extension = 'jpg'
        file_name = next(
            (attr.file_name for attr in message.media.photo.sizes if hasattr(attr, 'file_name')), 
            f"photo_{message.id}.{file_extension}"
        )
        file_name = sanitize_filename(file_name)
        media_info["path"] = get_file_url(message.media.photo.id, channel_name, file_name)
    
    elif isinstance(message.media, MessageMediaDocument):
        media_info["type"] = "file"
        file = message.media.document
        file_name = 'unknown_file'
        if hasattr(file, 'attributes') and file.attributes:
            for attr in file.attributes:
                if hasattr(attr, 'file_name'):
                    file_name = attr.file_name
                    break
        file_name = sanitize_filename(file_name)
        media_info["path"] = get_file_url(file.id, channel_name, file_name)
    
    return media_info

async def process_invite_url(url, client):
    try:
        invite_code = url.split('t.me/joinchat/')[-1]
        await client(ImportChatInviteRequest(invite_code))
        logging.info(f"Joined group via URL: {url}")
    except (FloodWaitError, ChatAdminRequiredError) as e:
        logging.error(f"Failed to join group via URL: {url}, Error: {str(e)}")
    except Exception as e:
        logging.error(f"Error processing URL: {url}, Error: {str(e)}")

def get_file_url(file_id: str, channel_username: str, file_name: Optional[str] = None) -> str:
    file_path = f"dragonfly/telegram/{channel_username}/{file_name or file_id}"
    return f"https://dragonfly.sgp1.digitaloceanspaces.com/{file_path}"
