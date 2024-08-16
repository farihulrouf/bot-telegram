import os
import io
import time
import logging
import mimetypes
import sys
from telethon import TelegramClient
from app.models.telegram_model import create_client, sessions, ChannelNamesResponse, ChannelNamesResponseAll, ChannelDetailResponse
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import PeerChannel
from telethon.tl.functions.messages import GetHistoryRequest
from app.utils.utils import upload_file_to_spaces
import re
from typing import Optional

# Set up logging
#logging.basicConfig(level=logging.DEBUG)

# Function to display download progress
def report_progress(transferred, total):
    if total > 0:
        percentage = (transferred / total) * 100
        speed = transferred / (time.time() - start_time)
        bar_length = 40  # Length of the progress bar
        filled_length = int(bar_length * transferred // total)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\rDownload Progress: |{bar}| {percentage:.2f}% | Speed: {speed / 1024:.2f} KB/s')
        sys.stdout.flush()
    else:
        sys.stdout.write('\rDownload Progress: |' + '-' * 40 + '| 0.00% | Speed: 0.00 KB/s')
        sys.stdout.flush()

# Function to display upload progress
def progress_callback(transferred, total):
    if total > 0:
        percentage = (transferred / total) * 100
        bar_length = 40  # Length of the progress bar
        filled_length = int(bar_length * transferred // total)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\rUpload Progress: |{bar}| {percentage:.2f}%')
        sys.stdout.flush()
    else:
        sys.stdout.write('\rUpload Progress: |' + '-' * 40 + '| 0.00%')
        sys.stdout.flush()

# Ensure to call this function before starting the download/upload to initialize `start_time`
start_time = time.time()

def sanitize_filename(filename):
    return "".join([c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename])

async def extract_and_join_channels(client, message_text):
    channel_mentions = re.findall(r'@(\w+)', message_text)
    if channel_mentions:
        print("Detected Telegram channels:")
        for mention in channel_mentions:
            print(f"Joining channel: {mention}")
            await ensure_joined(client, mention)
    else:
        print("No Telegram channels found in message.")

async def ensure_joined(client, username):
    try:
        entity = await client.get_entity(username)
        if isinstance(entity, PeerChannel):
            print(f"Already a member of {username}.")
        else:
            print(f"Joining {username}...")
            await client(JoinChannelRequest(username))
            print(f"Successfully joined {username}.")
    except Exception as e:
        print(f"Error joining {username}: {e}")



async def get_channel_messages(
    phone: str,
    channel_identifier: str,
    limit: Optional[int] = None,  # Default to None if not provided
    endpoint: str = os.getenv('SPACES_ENDPOINT'),
    bucket: str = os.getenv('SPACES_BUCKET'),
    folder: str = os.getenv('SPACES_FOLDER'),
    access_key: str = os.getenv('SPACES_ACCESS_KEY'),
    secret_key: str = os.getenv('SPACES_SECRET_KEY')
):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    logging.debug(f"Session found for phone: {phone}")

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
            entity_type = "channel"
        else:  # Assume it's a group
            channel_name = entity.title if entity.title else "Group Description"
            entity_type = "group"

        # Log the identified entity type
        logging.debug(f"Entity identified as a {entity_type}: {channel_name}")

        result = []
        offset_id = 0

        # Initialize remaining_limit with the provided limit or None
        remaining_limit = limit
        total_messages_read = 0

        while True:
            # Set batch_limit to 100 or the remaining_limit if it is specified
            batch_limit = 100 if remaining_limit is None else min(100, remaining_limit)
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

            # Log number of messages received
            logging.debug(f"Number of messages received: {len(messages.messages)}")

            if not messages.messages:
                break

            for message in messages.messages:

                sender_username = None
                if message.sender_id:
                    sender_entity = await client.get_entity(message.sender_id)
                    sender_username = sender_entity.username

                message_data = {
                    "username": sender_username,
                    "sender_id": message.sender_id,
                    "text": message.message if message.message else "",
                    "date": message.date.isoformat(),
                    "media": None
                }

                if message.media:
                    try:
                        file_stream = io.BytesIO()
                        file_name = ''
                        file_extension = ''
                        remote_file_path = ''

                        global start_time
                        start_time = time.time()

                        if isinstance(message.media, MessageMediaPhoto):
                            logging.debug(f"Downloading photo media from message ID: {message.id}")
                            await client.download_media(message.media.photo, file=file_stream, progress_callback=report_progress)
                            file_extension = 'jpg'
                            file_name = next((attr.file_name for attr in message.media.photo.sizes if hasattr(attr, 'file_name')), f"photo_{message.id}.{file_extension}")

                        elif isinstance(message.media, MessageMediaDocument):
                            doc = message.media.document
                            logging.debug(f"Downloading document media from message ID: {message.id}")
                            await client.download_media(doc, file=file_stream, progress_callback=report_progress)
                            mime_type = doc.mime_type
                            file_extension = mimetypes.guess_extension(mime_type) or '.bin'
                            file_name = next((attr.file_name for attr in doc.attributes if hasattr(attr, 'file_name')), f"{doc.id}{file_extension}")

                        else:
                            logging.debug(f"Downloading other media from message ID: {message.id}")
                            await client.download_media(message.media, file=file_stream, progress_callback=report_progress)
                            mime_type = message.media.mime_type if hasattr(message.media, 'mime_type') else 'application/octet-stream'
                            file_extension = mimetypes.guess_extension(mime_type) or 'bin'
                            file_name = f"{message.media.id}.{file_extension}"

                        # Sanitize file name
                        file_name = sanitize_filename(file_name)
                       
                        file_stream.seek(0)
                        logging.debug(f"Uploading file with name: {file_name}")
                        uploaded_file_url = upload_file_to_spaces(file_stream, file_name, channel_name, access_key, secret_key, endpoint, bucket, folder)
                        
                        logging.debug(f"Uploaded file URL: {uploaded_file_url}")
                        
                        if not uploaded_file_url:
                            raise Exception("File upload returned an invalid URL.")

                        mime_type = mimetypes.guess_type(file_name)[0]
                        media_type = "document"
                        if mime_type:
                            if mime_type.startswith('image/'):
                                media_type = "photo"
                            elif mime_type.startswith('video/'):
                                media_type = "video"
                            elif mime_type.startswith('audio/'):
                                media_type = "audio"
                            elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                                media_type = "document"
                            else:
                                media_type = "file"

                        message_data["media"] = {
                            "type": media_type,
                            "path": uploaded_file_url
                        }

                    except Exception as e:
                        logging.error(f"Error downloading or uploading media: {e}")
                        message_data["media"] = {"type": "error", "path": None}

                result.append(message_data)
                total_messages_read += 1

            offset_id = messages.messages[-1].id  # Update offset_id to the last message ID

            # Break the loop if limit has been reached
            if remaining_limit is not None:
                remaining_limit -= len(messages.messages)
                if remaining_limit <= 0:
                    break

        await client.disconnect()
        return {"status": "messages_received", "total_messages_read": total_messages_read, "messages": result}

    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to get messages: {str(e)}")
