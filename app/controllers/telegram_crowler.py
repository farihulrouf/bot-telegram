import os
import io
import time
import logging
import mimetypes
import sys
from telethon import TelegramClient
from app.models.telegram_model import create_client, read_sender, read_message, sessions, ChannelNamesResponse, ChannelNamesResponseAll, ChannelDetailResponse
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import PeerChannel, User, Channel, Chat
from telethon.tl.functions.messages import GetHistoryRequest
from app.utils.utils import upload_file_to_spaces
import re
from typing import Optional
from app.controllers.webhook import webhook_push
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()

webhook_url = os.getenv('WEBHOOK_URL')

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

        group_id = entity.id
        entity_type = "group"
        if isinstance(entity,Channel):
            if entity.broadcast:
                entity_type = "channel"
        elif isinstance(entity,Chat):
            None
        else:
            return

        # result = []
        offset_id = 0

        # Initialize remaining_limit with the provided limit or None
        remaining_limit = limit
        total_messages_read = 0

        senders = {}

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

            new_senders = []
            for user in messages.users:
                if not user.id in senders:
                    sender = await read_sender(client, user)
                    senders[user.id] = sender
                    new_senders.append(sender)

            # simpan ke webhook
            section_webhook = "senders"
            await webhook_push(section_webhook, new_senders)

            # Log number of messages received
            logging.debug(f"Number of messages received: {len(messages.messages)}")

            if not messages.messages:
                break
            
            new_events = []
            for message in messages.messages:
                
                sender = None
                pid = None

                if message.from_id == None:
                    if isinstance(message.peer_id, PeerChannel):
                        pid = message.peer_id.channel_id
                    elif isinstance(message.peer_id, PeerChat):
                        pid = message.peer_id.chat_id

                    if pid in senders:
                        sender = senders[pid]
                    else:
                        entity = await client.get_entity(pid)
                        sender = await read_sender(client, entity)
                else:
                    if isinstance(message.peer_id, PeerChannel):
                        pid = message.peer_id.channel_id
                    elif isinstance(message.peer_id, PeerChat):
                        pid = message.peer_id.chat_id
                    elif isinstance(message.peer_id, PeerUser):
                        pid = message.peer_id.user_id
                    sender = senders[pid]

                event = await read_message(client, message, sender)
                new_events.append(event)

                # result.append(event)
                total_messages_read += 1

            offset_id = messages.messages[-1].id  # Update offset_id to the last message ID

            # simpan ke webhook
            section_webhook = "group_messages"
            await webhook_push(section_webhook, {
                "phone": phone,
                "channel": channel_identifier,
                "data": new_events
            })

            # Break the loop if limit has been reached
            if remaining_limit is not None:
                remaining_limit -= len(messages.messages)
                if remaining_limit <= 0:
                    break

            time.sleep(5)

        # await client.disconnect()
        return {"status": "messages_received", "total_messages_read": total_messages_read}

    except Exception as e:
        # await client.disconnect()
        raise Exception(f"Failed to get messages: {str(e)}")
