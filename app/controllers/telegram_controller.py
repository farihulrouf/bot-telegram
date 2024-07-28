import logging
from telethon.errors import SessionPasswordNeededError , FloodWaitError, InviteHashExpiredError, InviteHashInvalidError
from telethon import TelegramClient, events, utils, errors
from telethon.tl.types import PeerChannel, ChannelFull
from telethon.tl.functions.messages import GetHistoryRequest
from app.models.telegram_model import PhoneNumber, VerificationCode, create_client, sessions, ChannelNamesResponse, ChannelNamesResponseAll, ChannelDetailResponse
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
import asyncio
import os
import re
from typing import Dict, List

logging.basicConfig(level=logging.DEBUG)

media_dirs = ['media/photos/', 'media/videos/', 'media/files/']
for media_dir in media_dirs:
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)

async def send_message(phone: str, recipient: str, message: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        if recipient.startswith('@'):
            recipient = recipient[1:]

        entity = await client.get_entity(recipient)
        await client.send_message(entity, message)
        return {"status": "message_sent"}
    except Exception as e:
        raise Exception(f"Failed to send message: {str(e)}")

async def login(phone: PhoneNumber):
    client = create_client(phone.phone)
    await client.connect()

    try:
        await client.send_code_request(phone.phone)
        sessions[phone.phone] = client
        logging.debug(f"Session created and stored for phone: {phone.phone}")
        return {"status": "code_sent"}
    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to send code: {str(e)}")

async def verify(code: VerificationCode):
    client = sessions.get(code.phone)
    if not client:
        raise Exception("Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        await client.sign_in(code.phone, code.code)
        if client.is_user_authorized():
            me = await client.get_me()
            logging.debug(f"User logged in: {me}")
            return {"status": "logged_in", "user": me.to_dict()}
        else:
            if code.password:
                await client.sign_in(password=code.password)
                me = await client.get_me()
                logging.debug(f"User logged in with 2FA: {me}")
                return {"status": "logged_in", "user": me.to_dict()}
            else:
                raise Exception("2FA required")
    except SessionPasswordNeededError:
        return {"status": "2fa_required"}
    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to verify code: {str(e)}")
    
async def join_channel(channel_username, phone_number, client):
    try:
        await client.start(phone_number)
        # Bergabung dengan saluran
        await client(JoinChannelRequest(channel_username))
        print(f"Successfully joined the channel: {channel_username}")
    except errors.FloodWaitError as e:
        print(f"Must wait for {e.seconds} seconds before trying again.")
    except errors.InviteHashExpiredError:
        print("The invite link has expired.")
    except errors.InviteHashInvalidError:
        print("The invite link is invalid.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.disconnect()

async def get_channel_messages(phone: str, channel_username: str, limit: int = 10):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    logging.debug(f"Session found for phone: {phone}")

    if not client.is_connected():
        await client.connect()

    try:
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]

        entity = await client.get_entity(channel_username)
        messages = await client(GetHistoryRequest(
            peer=entity,
            offset_id=0,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))

        result = []
        for message in messages.messages:
            logging.debug(f"Message: {message}")
            sender_username = None
            if message.sender_id:
                sender_entity = await client.get_entity(message.sender_id)
                sender_username = sender_entity.username
            message_data = {
                "username": sender_username,
                "sender_id": utils.resolve_id(message.sender_id)[0],
                "text": message.message if message.message else "",
                "date": message.date.isoformat(),
                "media": None
            }

            try:
                if isinstance(message.media, MessageMediaPhoto):
                    logging.debug(f"Photo detected: {message.media.photo}")
                    output_path = "media/photos/"
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                    media_path = await client.download_media(message.media.photo, file=output_path)
                    logging.debug(f"Downloaded photo to: {media_path}")
                    if media_path:
                        message_data["media"] = {"type": "photo", "path": media_path}
                elif isinstance(message.media, MessageMediaDocument):
                    doc = message.media.document
                    if doc.mime_type.startswith('video'):
                        logging.debug(f"Video detected: {doc}")
                        output_path = "media/videos/"
                        if not os.path.exists(output_path):
                            os.makedirs(output_path)
                        media_path = await client.download_media(doc, file=output_path)
                        logging.debug(f"Downloaded video to: {media_path}")
                        if media_path:
                            message_data["media"] = {"type": "video", "path": media_path}
                    elif doc.mime_type.startswith('application'):
                        logging.debug(f"Document detected: {doc}")
                        output_path = "media/files/"
                        if not os.path.exists(output_path):
                            os.makedirs(output_path)
                        media_path = await client.download_media(doc, file=output_path)
                        logging.debug(f"Downloaded document to: {media_path}")
                        if media_path:
                            message_data["media"] = {"type": "document", "path": media_path}
                    else:
                        logging.debug(f"Unknown document type detected: {doc}")
                        output_path = "media/files/"
                        if not os.path.exists(output_path):
                            os.makedirs(output_path)
                        media_path = await client.download_media(doc, file=output_path)
                        logging.debug(f"Downloaded unknown document to: {media_path}")
                        if media_path:
                            message_data["media"] = {"type": "unknown", "path": media_path}
                else:
                    logging.debug(f"Unknown media detected: {message.media}")
                    output_path = "media/files/"
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                    media_path = await client.download_media(message.media, file=output_path)
                    logging.debug(f"Downloaded unknown media to: {media_path}")
                    if media_path:
                        message_data["media"] = {"type": "unknown", "path": media_path}
            except Exception as e:
                logging.error(f"Error downloading media: {e}")
                message_data["media"] = {"type": "error", "path": None}

            result.append(message_data)

        await client.disconnect()
        return {"status": "messages_received", "messages": result}

    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to get messages: {str(e)}")
    
async def join_subscribe(phone: str, username_channel: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        if username_channel.startswith('@'):
            username_channel = username_channel[1:]

        # Bergabung dengan saluran
        await client(JoinChannelRequest(username_channel))
        logging.debug(f"Successfully joined the channel: {username_channel}")
        return {"status": "joined_channel", "channel": username_channel}
    except FloodWaitError as e:
        logging.error(f"Must wait for {e.seconds} seconds before trying again.")
        return {"status": "flood_wait", "seconds": e.seconds}
    except InviteHashExpiredError:
        logging.error("The invite link has expired.")
        return {"status": "invite_link_expired"}
    except InviteHashInvalidError:
        logging.error("The invite link is invalid.")
        return {"status": "invite_link_invalid"}
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        await client.disconnect()

def extract_channel_names(text: str) -> ChannelNamesResponse:
    # Regular expression to find words starting with @
    channel_names = re.findall(r'@\w+', text)
    
    # Remove duplicates by converting to a set and back to a list
    channel_names = list(set(channel_names))
    
    # Create and return a ChannelNamesResponse object
    return ChannelNamesResponse(
        total_channel=len(channel_names),
        name_channel=channel_names
    )

async def read_and_join_channels(phone: str, channel_username: str, limit: int = 10):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        # Ensure channel_username is a string and process it
        if not isinstance(channel_username, str):
            raise TypeError("channel_username must be a string")

        if channel_username.startswith('@'):
            channel_username = channel_username[1:]

        # Get the entity for the channel
        entity = await client.get_entity(channel_username)
        
        # Get recent messages from the channel
        messages = await client(GetHistoryRequest(
            peer=entity,
            offset_id=0,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))

        all_channel_names = []
        total_message_read = 0
        
        for message in messages.messages:
            if message.message:
                # Extract channel names from message text
                response: ChannelNamesResponse = extract_channel_names(message.message)
                all_channel_names.extend(response.name_channel)
                total_message_read += 1
        
        # Remove duplicates
        all_channel_names = list(set(all_channel_names))
        
        # Join each channel
        join_responses = []
        for channel in all_channel_names:
            if channel.startswith('@'):
                channel = channel[1:]
            
            try:
                await client(JoinChannelRequest(channel))
                join_responses.append({"channel": channel, "status": "joined"})
            except FloodWaitError as e:
                join_responses.append({"channel": channel, "status": f"flood_wait_error: {e.seconds} seconds"})
            except InviteHashExpiredError:
                join_responses.append({"channel": channel, "status": "invite_hash_expired"})
            except InviteHashInvalidError:
                join_responses.append({"channel": channel, "status": "invite_hash_invalid"})
            except Exception as e:
                join_responses.append({"channel": channel, "status": f"error: {str(e)}"})

        return {
            "status": "completed",
            "total_message_read": total_message_read,
            "join_responses": join_responses
        }
    
    except Exception as e:
        raise Exception(f"Failed to read messages and join channels: {str(e)}")
    finally:
        await client.disconnect()

async def get_all_channels(phone: str) -> ChannelNamesResponseAll:
    client = sessions.get(phone)
    if not client:
        logging.error(f"Session not found for phone: {phone}")
        raise Exception("Session not found")
    logging.debug(f"Session found for phone: {phone}")

    if not client.is_connected():
        logging.debug(f"Connecting client for phone: {phone}")
        await client.connect()

    try:
        dialogs = await client.get_dialogs()
        logging.debug(f"Retrieved dialogs for phone: {phone}")

        channels = [
            {'name_channel': f"@{dialog.entity.username}"}
            for dialog in dialogs
            if dialog.is_channel and dialog.entity.username
        ]
        logging.debug(f"Extracted channel names for phone: {phone}")

        await client.disconnect()
        logging.debug(f"Client disconnected for phone: {phone}")

        response = ChannelNamesResponseAll(
            total_channels=len(channels),
            channels=channels
        )
        
        return response
    except Exception as e:
        logging.error(f"Failed to get channels: {str(e)}")
        await client.disconnect()
        raise Exception(f"Failed to get channels: {str(e)}")
    

async def get_channel_details(phone: str, channel_username: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]

        entity = await client.get_entity(channel_username)
        full_channel = await client(GetFullChannelRequest(channel=entity))

        # Handle None values by providing a default value
        channel_info = {
            "id": entity.id,
            "name": entity.title,
            "username": entity.username,
            "participants_count": full_channel.full_chat.participants_count or 0,
            "admins_count": full_channel.full_chat.admins_count or 0,
            "banned_count": full_channel.full_chat.kicked_count or 0,
            "description": full_channel.full_chat.about or "",
            "created_at": entity.date.isoformat()
        }

        await client.disconnect()
        return {"status": "success", "channel_info": channel_info}

    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to get channel details: {str(e)}")
