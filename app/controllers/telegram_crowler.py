import os
import io
import time
import logging
import mimetypes
import sys
from telethon import TelegramClient
from app.models.telegram_model import create_client, sessions, ChannelNamesResponse, ChannelNamesResponseAll, ChannelDetailResponse
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.messages import GetHistoryRequest
from app.utils.utils import upload_file_to_spaces
# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Function to display download progress
def report_progress(transferred, total):
    if total > 0:
        percentage = (transferred / total) * 100
        speed = transferred / (time.time() - start_time)
        print(f'Download Progress: {percentage:.2f}% | Speed: {speed / 1024:.2f} KB/s')
    else:
        print('Download Progress: 0.00% | Speed: 0.00 KB/s')

# Function to display upload progress
def progress_callback(transferred, total):
    if total > 0:
        percentage = (transferred / total) * 100
        print(f'Upload Progress: {percentage:.2f}%')
    else:
        print('Upload Progress: 0.00%')

def sanitize_filename(filename):
    return "".join([c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename])

async def get_channel_messages(
    phone: str,
    channel_username: str,
    limit: int = 10,
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
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]

        entity = await client.get_entity(channel_username)
        channel_name = entity.username or str(entity.id)

        result = []
        offset_id = 0
        remaining_limit = limit

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

            offset_id = messages.messages[-1].id
            remaining_limit -= len(messages.messages)

        await client.disconnect()
        return {"status": "messages_received", "messages": result}

    except Exception as e:
        await client.disconnect()
        raise Exception(f"Failed to get messages: {str(e)}")
