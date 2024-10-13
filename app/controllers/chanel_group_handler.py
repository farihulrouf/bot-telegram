from fastapi import HTTPException
from app.models.telegram_model import  sessions
import logging
from telethon.tl.types import InputChannel, Channel, Chat
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest


async def get_channel_details(phone: str, channel_identifier: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        entity = None

        # Determine if the identifier is an ID or username
        if channel_identifier.startswith('-') and channel_identifier[1:].isdigit():
            # Treat as a negative ID
            try:
                entity_id = int(channel_identifier)
                entity = await client.get_entity(entity_id)
            except Exception as e:
                # await client.disconnect()
                raise Exception(f"Failed to fetch by ID: {str(e)}")
        elif channel_identifier.isdigit():
            # Treat as a positive ID
            try:
                entity_id = int(channel_identifier)
                entity = await client.get_entity(entity_id)
            except Exception as e:
                # await client.disconnect()
                raise Exception(f"Failed to fetch by ID: {str(e)}")
        else:
            # Treat as a username
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            try:
                entity = await client.get_entity(channel_identifier)
            except Exception as e:
                # await client.disconnect()
                raise Exception(f"Failed to fetch by username: {str(e)}")

        # Ensure that the entity is a valid Channel or Chat
        if isinstance(entity, (Channel, Chat)):
            full_channel = await client(GetFullChannelRequest(channel=entity))
            print("check",full_channel )
            # Handle None values by providing default values
            channel_info = {
                "id": entity.id,
                "name": entity.title or "No Title",
                "username": entity.username or "No Username",
                "participants_count": full_channel.full_chat.participants_count or 0,
                "admins_count": full_channel.full_chat.admins_count or 0,
                "banned_count": full_channel.full_chat.kicked_count or 0,
                "description": full_channel.full_chat.about or "",
                "created_at": entity.date.isoformat() if entity.date else "Unknown"
            }

            # await client.disconnect()
            return {"status": "success", "channel_info": channel_info}

        else:
            # await client.disconnect()
            raise Exception("The identifier does not correspond to a channel or group.")
    
    except Exception as e:
        # await client.disconnect()
        raise Exception(f"Failed to get channel details: {str(e)}")
