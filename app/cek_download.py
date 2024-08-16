import os
import io
import time
import logging
import mimetypes
import sys
import argparse
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.messages import GetHistoryRequest
from botocore.client import Config
import boto3

# Constants for DigitalOcean Spaces
SPACES_ENDPOINT = os.getenv('SPACES_ENDPOINT', 'https://dragonfly.sgp1.digitaloceanspaces.com')
SPACES_BUCKET = os.getenv('SPACES_BUCKET', 'dragonfly')
SPACES_FOLDER = os.getenv('SPACES_FOLDER', 'telegram')
SPACES_ACCESS_KEY = os.getenv('SPACES_ACCESS_KEY', 'DO00LR3ADUB2HA4J4H8P')
SPACES_SECRET_KEY = os.getenv('SPACES_SECRET_KEY', 'liLT7kLOA4/pi1nfMoafjGVldBzPdYVP2RBVJkjqsqw')

# Set up logging
logging.basicConfig(level=logging.DEBUG)

start_time = None

def report_progress(transferred, total):
    if total > 0:
        percentage = (transferred / total) * 100
        speed = transferred / (time.time() - start_time)
        bar_length = 40
        filled_length = int(bar_length * transferred // total)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\rDownload Progress: |{bar}| {percentage:.2f}% | Speed: {speed / 1024:.2f} KB/s')
        sys.stdout.flush()
    else:
        sys.stdout.write('\rDownload Progress: |' + '-' * 40 + '| 0.00% | Speed: 0.00 KB/s')
        sys.stdout.flush()

def progress_callback(bytes_transferred, total):
    if total:
        percentage = (bytes_transferred / total) * 100
        bar_length = 40
        filled_length = int(bar_length * bytes_transferred // total)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\rUpload Progress: |{bar}| {percentage:.2f}%')
        sys.stdout.flush()
    else:
        sys.stdout.write('\rUpload Progress: |' + '-' * 40 + '| 0.00%')
        sys.stdout.flush()

def sanitize_filename(filename):
    return "".join([c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename])

def upload_file_to_spaces(file_stream, bucket, file_path):
    s3 = boto3.client('s3',
                      endpoint_url=SPACES_ENDPOINT,
                      aws_access_key_id=SPACES_ACCESS_KEY,
                      aws_secret_access_key=SPACES_SECRET_KEY,
                      config=Config(signature_version='s3v4'))

    try:
        s3.upload_fileobj(
            file_stream,
            bucket,
            file_path,
            ExtraArgs={'ACL': 'public-read'}  # Set permissions to public-read
        )
        print(f"\nUpload Successful: {file_path} to {SPACES_ENDPOINT}/{bucket}/{file_path}")
    except Exception as e:
        print(f"\nUpload failed: {e}")

async def get_channel_messages(phone, channel_identifier, limit=None):
    session_file = f"app/{phone}.session"
    print(f"Checking for session file: {session_file}")

    if not os.path.isfile(session_file):
        raise Exception(f"Session file for {phone} not found. Expected file: {session_file}")

    client = TelegramClient(session_file, api_id=22346896, api_hash='468c3ff322a27be3a054a4f2c057f177')

    try:
        await client.connect()

        try:
            entity = await client.get_entity(channel_identifier)
            channel_name = entity.username if entity.username else str(entity.id)
            entity_type = "channel" if entity.broadcast else "group"
            logging.debug(f"Entity identified as a {entity_type}: {channel_name}")

            result = []
            offset_id = 0
            remaining_limit = limit
            total_messages_read = 0

            while True:
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
                            file_size = 0
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

                            file_name = sanitize_filename(file_name)
                            file_stream.seek(0)
                            file_size = file_stream.tell()

                            logging.debug(f"Uploading file with name: {file_name}")

                            file_path = f"{SPACES_FOLDER}/{channel_name}/{file_name}"
                            upload_file_to_spaces(file_stream, SPACES_BUCKET, file_path)

                            uploaded_file_url = f"{SPACES_ENDPOINT}/{SPACES_BUCKET}/{file_path}"
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

                offset_id = messages.messages[-1].id
                if remaining_limit is not None:
                    remaining_limit -= len(messages.messages)
                    if remaining_limit <= 0:
                        break

            return result

        except Exception as e:
            logging.error(f"Error fetching messages: {e}")
            return {"error": str(e)}

    finally:
        await client.disconnect()

async def main():
    parser = argparse.ArgumentParser(description="Telegram Channel Message Downloader")
    parser.add_argument("--phone", required=True, help="Phone number associated with the Telegram account")
    parser.add_argument("--channel", required=True, help="Username or ID of the channel to fetch messages from")
    parser.add_argument("--limit", type=int, help="Number of messages to fetch (default: None, fetch all available messages)")
    args = parser.parse_args()

    messages = await get_channel_messages(args.phone, args.channel, args.limit)
    print(messages)

if __name__ == "__main__":
    asyncio.run(main())
