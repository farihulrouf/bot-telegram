from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, Channel, Chat, Message, User, PeerUser, PeerChannel, PeerChat
from app.utils.utils import upload_profile_avatar, upload_post_media
from app.controllers.webhook import webhook_push
from pydantic import BaseModel
from typing import Optional
import os
import io
import sys
import time
import asyncio
import requests
import mimetypes
from typing import Dict, List, Union
import logging
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
webhook_url = os.getenv('WEBHOOK_URL')

# Dictionary untuk menyimpan sesi aktif
sessions = {}

# Active clients
active_clients: Dict[str, asyncio.Task] = {}

senders = {}
start_time = time.time()

class FileDetails(BaseModel):
    name: str
    size: int

class ListDataResponse(BaseModel):
    status: str
    total_files: int
    files: List[FileDetails]

class WebhookPayload(BaseModel):
    sender_id: int
    chat_id: int
    message: str
    date: str
    media: str = None
    
class ContactResponse(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    username: Optional[str]

class ChannelGroup(BaseModel):
    name_channel_group: str
    status: bool

class ChannelDetailResponse(BaseModel):
    id: int
    name: str
    username: str
    participants_count: int
    admins_count: int
    banned_count: int
    description: str
    created_at: str

class ChannelNamesResponseAll(BaseModel):
    total_channels: int
    total_groups: int
    channels_groups: List[ChannelGroup]
    
class SendMessageRequest(BaseModel):
    phone: str
    recipient: str
    message: str

class ChannelNamesResponse(BaseModel):
    total_channel: int
    name_channel: List[str]

class TextRequest(BaseModel):
    text: str

class JoinRequest(BaseModel):
    phone: str
    username_channel: str

class PhoneNumber(BaseModel):
    phone: str

class VerificationCode(BaseModel):
    phone: str
    code: str
    password: str = None

class GroupSearchRequest(BaseModel):
    phone: str
    query: str

def create_client(phone: str) -> TelegramClient:
    # Menggunakan file sesi yang dinamai dengan nomor telepon
    session_file = f"sessions/{phone}.session"
    return TelegramClient(session_file, int(api_id), api_hash)

def sanitize_filename(filename):
    return "".join([c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename])

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

async def read_sender(client: TelegramClient, sender: Union[User, Channel, Chat], group_id):
    
    original_id = sender.id
    username = sender.username
    phone = None
    name = None
    fullname = None
    avatar = None
    url = None
    bio = None
    is_private = sender.restricted
    is_verified = sender.verified
    is_premium = None
    is_bot = None

    if isinstance(sender, User):
        phone = sender.phone
        is_bot = sender.bot
        is_premium = sender.premium
        name = sender.first_name if sender.first_name else ""
        if sender.last_name:
            name = name +" "+ sender.last_name
    elif isinstance(sender, Channel):
        name = sender.title
    elif isinstance(sender, Chat):
        name = sender.title

    fullname = name

    # download image profile
    if sender.photo != None:    
        file_stream = io.BytesIO()
        result = await client.download_profile_photo(sender, file=file_stream)
        if result:
            file_stream.seek(0)
            avatar = upload_profile_avatar(file_stream, f"{original_id}-jpg", "image/jpg")

    return {
        "original_id": original_id,
        "username": username,
        "phone": phone,
        "name": name,
        "fullname": fullname,
        "avatar": avatar,
        "url": url,
        "bio": bio,
        "is_private": is_private,
        "is_verified": is_private,
        "is_premium": is_premium,
        "is_bot": is_bot,
        "group_id": group_id
    }


async def read_message(client: TelegramClient, message: Message, sender: {}):

    group_id = None
    sender_id = sender["original_id"]
    sender_name = sender["name"]
    sender_username = sender["username"]
    sender_avatar = sender["avatar"]

    # detect group or channel
    if isinstance(message.peer_id, PeerChannel):
        group_id = message.peer_id.channel_id
    elif isinstance(message.peer_id, PeerChat):
        group_id = message.peer_id.chat_id
    else:
        group_id = sender_id

    # elif sender_id:
    #     print(f"---- get sender {sender_id}")
    #     print("--- peer_id")
    #     print(message.peer_id)
    #     print("--- from_id")
    #     print(message.from_id)

    #     try:
    #         sender_entity = await client.get_entity(sender_id)
    #     except Exception as e:
    #         sender_entity = await client.get_user_from_chat(sender_id)

    #     sender_id = sender_entity.id
    #     sender_username = sender_entity.username
    #     if isinstance(sender_entity,User):
    #         sender_name = sender_entity.first_name if sender_entity.first_name else ""
    #         if sender_entity.last_name:
    #             sender_name = sender_name +" "+ sender_entity.last_name
    #     elif isinstance(sender_entity,Channel) or isinstance(sender_entity,Chat):
    #         sender_name = sender_entity.title if sender_entity.title else ""

    #     # download image profile
    #     file_stream = io.BytesIO()
    #     result = await client.download_profile_photo(sender_entity, file=file_stream)
    #     if result:
    #         file_stream.seek(0)
    #         sender_avatar = upload_profile_avatar(file_stream, f"{sender_id}-jpg")

    #     senders[sender_id] = {
    #         "id": sender_id,
    #         "username": sender_username,
    #         "name": sender_name,
    #         "avatar": sender_avatar
    #     }

    message_data = {
        'original_id': message.id,
        'group_id': group_id,
        'sender_id': sender_id,
        'sender_name': sender_name,
        'sender_username': sender_username,
        'sender_avatar': sender_avatar,
        'post': message.message if message.message else "",
        # 'url' => $item['url'],
        'view_count': message.views,
        'comment_count': message.replies.replies if message.replies else None,
        'forward_count': message.forwards,
        # 'download_count' => 0,
        "reply_to_user": None,
        "reply_to_post": None,
        "reply_to_top": None,
        "forwarded_from_user": None,
        "forwarded_from_msg": None,
        # 'engagement' => $engagement,
        'type': 'post',
        'time': int(message.date.timestamp()),
        "file_type": None,
        "file_name": None,
        "file_url": None,
        "mimetype": None,
    }

    if message.reply_to != None:
        message_data["type"] = "reply"
        message_data["reply_to_top"] = message.reply_to.reply_to_top_id
        message_data["reply_to_post"] = message.reply_to.reply_to_msg_id
        message_data["reply_to_user"] = message.reply_to.reply_to_peer_id

    if message.fwd_from != None:
        message_data["type"] = "reply"
        if isinstance(message.fwd_from.from_id, PeerChat): # group
            message_data["forwarded_from_user"] = message.fwd_from.from_id.chat_id
        elif isinstance(message.fwd_from.from_id, PeerChannel): # channel
            message_data["forwarded_from_user"] = message.fwd_from.from_id.channel_id
        elif isinstance(message.fwd_from.from_id, PeerUser): # user
            message_data["forwarded_from_user"] = message.fwd_from.from_id.user_id

    if message.media:
        try:
            file_stream = io.BytesIO()
            file_name = ''
            file_extension = ''
            remote_file_path = ''
            mime_type = ''

            global start_time
            start_time = time.time()

            # print("---------- message media -----------")
            # print(message.media)

            needUpload = False

            if isinstance(message.media, MessageMediaPhoto):
                needUpload = True
                logging.debug(f"Downloading photo media from message ID: {message.id}")
                file_path = await client.download_media(message.media.photo, file=file_stream, progress_callback=report_progress)
                file_extension = 'jpg'
                mime_type = "image/jpg"
                file_name = next((attr.file_name for attr in message.media.photo.sizes if hasattr(attr, 'file_name')), f"photo_{message.id}.{file_extension}")

            elif isinstance(message.media, MessageMediaDocument):
                # needUpload = True
                logging.debug(f"Downloading document media from message ID: {message.id}")
                # doc = message.media.document
                # await client.download_media(doc, file=file_stream, progress_callback=report_progress)
                # mime_type = doc.mime_type
                # file_extension = mimetypes.guess_extension(mime_type) or '.bin'
                # file_name = next((attr.file_name for attr in doc.attributes if hasattr(attr, 'file_name')), f"{message.id}{file_extension}")

            else:
                # needUpload = False
                logging.debug(f"Downloading other media from message ID: {message.id}")
                # await client.download_media(message.media, file=file_stream, progress_callback=report_progress)
                # mime_type = message.media.mime_type if hasattr(message.media, 'mime_type') else 'application/octet-stream'
                # file_extension = mimetypes.guess_extension(mime_type) or 'bin'
                # file_name = f"{message.id}-{message_data['time']}.{file_extension}"

            # Sanitize file name
            file_name = sanitize_filename(file_name)
                        
            file_stream.seek(0)
            logging.debug(f"Uploading file with name: {file_name}")
            # uploaded_file_url = upload_file_to_spaces(file_stream, file_name, channel_name, access_key, secret_key, endpoint, bucket, folder)

            mime_type = mimetypes.guess_type(file_name)[0]
            media_type = "document"
            if mime_type:
                if mime_type.startswith('image/'):
                    media_type = "image"
                elif mime_type.startswith('video/'):
                    media_type = "video"
                elif mime_type.startswith('audio/'):
                    media_type = "audio"
                elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                    media_type = "document"
                else:
                    media_type = "file"

            date_folder = message.date.strftime('%Y%m%d')

            uploaded_file_url = ""
            if needUpload:
                uploaded_file_url = upload_post_media(file_stream, group_id, date_folder, file_name, mime_type)

            message_data["mimetype"] = mime_type
            message_data["file_type"] = media_type
            message_data["file_name"] = file_name
            message_data["file_url"] = uploaded_file_url

            logging.debug(f"Uploaded file URL: {uploaded_file_url}")
                            
            if not uploaded_file_url:
                raise Exception("File upload returned an invalid URL.")

            

        except Exception as e:
            logging.error(f"Error downloading or uploading media: {e}")
            message_data["media"] = {"type": "error", "path": None}

    return message_data


async def listen_messages(phone: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")

    if not client.is_connected():
        await client.connect()

    async def handle_message(event):
        global senders

        print("... incoming ...")

        user = await event.get_sender()

        # user_id = None
        # if user != None:
        #     user_id = user.id

        if user.id in senders:
            sender = senders[user.id]
        else:
            group_id = None
            if isinstance(event.message.peer_id, PeerChannel):
                group_id = event.message.peer_id.channel_id
            elif isinstance(event.message.peer_id, PeerChat):
                group_id = event.message.peer_id.chat_id

            sender = await read_sender(client, user, group_id)

            section_webhook = "senders"
            await webhook_push(section_webhook, [sender])

        event = await read_message(client, event.message, sender)

        section_webhook = "single_message"
        await webhook_push(section_webhook, event)

    # Tambahkan event handler untuk menangani pesan baru
    client.add_event_handler(handle_message, events.NewMessage)

    if await client.is_user_authorized():
        # Menjaga agar client tetap terhubung dan aktif untuk memproses pesan
        try:
            await client.run_until_disconnected()
        except KeyboardInterrupt:
            print("Disconnected due to user interrupt")
        # finally:
        #     await client.disconnect()
    # else:
    #     await client.disconnect()

    return {"status": "messages_received"}
