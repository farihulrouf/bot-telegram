import os
import io
import time
import re
import asyncio
import paramiko
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import PeerChannel
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Gunakan kredensial Anda
api_id = 22346896
api_hash = '468c3ff322a27be3a054a4f2c057f177'
phone_number = '+6285280933757'

# Server details
SERVER_IP = '128.199.76.91'
SFTP_USERNAME = 'peratan'
SSH_KEY_PATH = '/home/farihul/.ssh/id_rsa'
PASSPHRASE = 'peruvian'

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the session file path relative to the 'sessions' directory
session_dir = os.path.join(script_dir, 'sessions')
session_file_path = os.path.join(session_dir, f'{phone_number}.session')

# Ensure the sessions directory exists
os.makedirs(session_dir, exist_ok=True)

# Set correct permissions for the sessions directory and files
os.chmod(session_dir, 0o755)
for root, dirs, files in os.walk(session_dir):
    for d in dirs:
        os.chmod(os.path.join(root, d), 0o755)
    for f in files:
        os.chmod(os.path.join(root, f), 0o644)

# Ensure the media directory exists
media_dir = os.path.join(script_dir, 'media')
os.makedirs(media_dir, exist_ok=True)

# Function to display download progress
def report_progress(transferred, total):
    if total > 0:  # Prevent division by zero
        percentage = (transferred / total) * 100
        speed = transferred / (time.time() - start_time)
        print(f'Download Progress: {percentage:.2f}% | Speed: {speed / 1024:.2f} KB/s')
    else:
        print('Download Progress: 0.00% | Speed: 0.00 KB/s')

# Function to display upload progress
def progress_callback(transferred, total):
    if total > 0:  # Prevent division by zero
        percentage = (transferred / total) * 100
        print(f'Upload Progress: {percentage:.2f}%')
    else:
        print('Upload Progress: 0.00%')

# Function to upload file to the server
async def upload_file_to_server(file_stream: io.BytesIO, remote_file_path: str):
    try:
        # Create an SSH transport object
        transport = paramiko.Transport((SERVER_IP, 22))
        
        # Load the private key with passphrase
        private_key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH, password=PASSPHRASE)
        
        # Connect to the server using the transport object and private key
        transport.connect(username=SFTP_USERNAME, pkey=private_key)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Ensure the stream is at the beginning
        file_stream.seek(0) 
        
        # Upload the file
        sftp.putfo(file_stream, remote_file_path, callback=progress_callback)
        print(f"File uploaded successfully to {remote_file_path}")
        
        # Verify uploaded file size
        remote_file_size = sftp.stat(remote_file_path).st_size
        file_stream.seek(0, io.SEEK_END)
        local_file_size = file_stream.tell()
        
        if remote_file_size == local_file_size:
            print(f"File size matches: {remote_file_size} bytes")
        else:
            print(f"Size mismatch: Local size = {local_file_size}, Remote size = {remote_file_size}")
        
        sftp.close()
        transport.close()
    except Exception as e:
        print(f"Error uploading file: {e}")

# Function to extract and join Telegram channels from message text
async def extract_and_join_channels(client, message_text):
    # Regex to find @mentions which could be channel usernames
    channel_mentions = re.findall(r'@(\w+)', message_text)
    if channel_mentions:
        print("Detected Telegram channels:")
        for mention in channel_mentions:
            print(f"Joining channel: {mention}")
            try:
                await client(JoinChannelRequest(mention))
                print(f"Successfully joined channel: {mention}")
            except Exception as e:
                print(f"Error joining channel {mention}: {e}")
    else:
        print("No Telegram channels found in message.")

# Function to ensure joining a channel or group
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

class Media(BaseModel):
    type: str
    path: str

class Message(BaseModel):
    username: str
    sender_id: int
    text: str
    date: str
    media: Optional[Media] = None

class MessagesResponse(BaseModel):
    status: str
    messages: List[Message]

async def process_and_upload_messages(client, history):
    global start_time
    messages = []
    for message in history.messages:
        media_info = None
        if message.media:
            # Track download start time
            start_time = time.time()
            
            # Download media to an in-memory file-like object
            file_stream = io.BytesIO()
            await client.download_media(message.media, file_stream, progress_callback=report_progress)
            
            # Extract filename from the document
            if hasattr(message.media, 'document') and message.media.document:
                file_name = message.media.document.attributes[0].file_name if message.media.document.attributes else 'unknown_file'
                media_type = 'document'
            else:
                file_name = 'unknown_file'
                media_type = 'unknown'
            
            print(f'File downloaded to memory as: {file_name}')
            
            # Define remote file path
            remote_file_path = os.path.join('/home/peratan/media/files', file_name)
            
            # Upload file to server
            await upload_file_to_server(file_stream, remote_file_path)
            
            media_info = {
                "type": media_type,
                "path": remote_file_path
            }
        
        messages.append(Message(
            username=message.sender.username if message.sender else "unknown",
            sender_id=message.sender_id,
            text=message.message,
            date=message.date.isoformat(),
            media=Media(**media_info) if media_info else None
        ))
        
        # Extract and join Telegram channels from the message text
        await extract_and_join_channels(client, message.message)
    
    return messages

@app.get("/api/get_messages", response_model=MessagesResponse)
async def get_messages(start_message_id: int = Query(0, description="Start message ID")):
    client = TelegramClient(session_file_path, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone_number)
        await client.sign_in(phone_number, input('Masukkan kode yang dikirim ke Telegram: '))

    # ID channel atau username
    channel_username = 'xcloudurl'

    # Ensure we have joined the channel or group
    await ensure_joined(client, channel_username)

    # ID channel atau username
    channel_entity = await client.get_entity(channel_username)

    print("Check channel", channel_username, 'and entity', channel_entity)

    messages = []
    while True:
        history = await client(GetHistoryRequest(
            peer=PeerChannel(channel_entity.id),
            limit=1500,  # Adjust limit as needed
            offset_date=None,
            offset_id=start_message_id,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))

        if not history.messages:
            break  # Break the loop if no more messages are found

        # Process messages and upload files
        new_messages = await process_and_upload_messages(client, history)
        messages.extend(new_messages)

        # Update start_message_id to the last message ID we processed
        start_message_id = history.messages[-1].id

    # Disconnect Telegram client
    await client.disconnect()

    return MessagesResponse(
        status="messages_received",
        messages=messages
    )

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
