import logging
from telethon.errors import SessionPasswordNeededError , FloodWaitError, InviteHashExpiredError, InviteHashInvalidError
from telethon import TelegramClient, events, utils, errors
from telethon.tl.types import PeerChannel, ChatPhoto, UserProfilePhoto, ChannelFull, InputPhoneContact, InputUser, ChannelParticipantsSearch
from telethon.tl.functions.contacts import GetContactsRequest, SearchRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetHistoryRequest, GetFullChatRequest
from app.models.telegram_model import PhoneNumber, VerificationCode, create_client, sessions, ChannelNamesResponse, ChannelNamesResponseAll, ChannelDetailResponse
from app.models.telegram_model import active_clients, listen_messages, read_sender, read_message
from telethon.tl.types import Channel, Chat, MessageMediaPhoto, MessageMediaDocument, MessageMediaUnsupported
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest, GetFullChannelRequest, GetParticipantsRequest
from app.utils.utils import upload_file_to_spaces  # Pastikan path impor sesuai dengan struktur direktori Anda
from telethon.errors.rpcerrorlist import ChannelsTooMuchError
from telethon.tl.types import PeerUser, PeerChat, PeerChannel, User, Channel, Chat
from fastapi.encoders import jsonable_encoder
from app.controllers.webhook import webhook_push
from app.utils.utils import upload_profile_avatar, upload_post_media
from typing import Optional
import asyncio
import base64
import os
import re
import io
import paramiko
import mimetypes
import time
import sys

from dotenv import load_dotenv

from typing import Dict, List
load_dotenv()


async def detail(phone: str, strid: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        if strid.startswith('@'):
            strid = strid[1:]
        
        eid = None
        if strid.isdigit():
            eid = int(strid)
        else:
            eid = strid

        entity = await client.get_entity(eid)
        # print(entity)

        # channel_info = {
        #         "id": entity.id,
        #         "name": entity.title or "No Title",
        #         "username": entity.username or "No Username",
        #         "participants_count": full_channel.full_chat.participants_count or 0,
        #         "admins_count": full_channel.full_chat.admins_count or 0,
        #         "banned_count": full_channel.full_chat.kicked_count or 0,
        #         "description": full_channel.full_chat.about or "",
        #         "created_at": entity.date.isoformat() if entity.date else "Unknown"
        #     }

        # Channel(
        #     id=1976881783, 
        #     title='Grup ASN UNTAD Palu Sulteng',
        #     photo=ChatPhotoEmpty(),
        #     date=datetime.datetime(2023, 9, 30, 2, 26, 47, tzinfo=datetime.timezone.utc), 
        #     creator=False, left=True, broadcast=False, 
        #     verified=False, megagroup=True, 
        #     restricted=False, signatures=False, min=False, 
        #     scam=False, has_link=False, has_geo=False, 
        #     slowmode_enabled=False, call_active=False, call_not_empty=False, 
        #     fake=False, gigagroup=False, noforwards=False, 
        #     join_to_send=False, join_request=False, forum=False, 
        #     stories_hidden=False, stories_hidden_min=True, 
        #     stories_unavailable=True, access_hash=-534482594599969747, 
        #     username='ASN_UNTAD_Palu_Sulteng', restriction_reason=[], 
        #     admin_rights=None, banned_rights=None, 
        #     default_banned_rights=ChatBannedRights(until_date=datetime.datetime(2038, 1, 19, 3, 14, 7, tzinfo=datetime.timezone.utc), 
        #     view_messages=False, send_messages=False, send_media=False, 
        #     send_stickers=False, send_gifs=False, send_games=False, 
        #     send_inline=False, embed_links=False, send_polls=False, 
        #     change_info=True, invite_users=False, pin_messages=True, 
        #     manage_topics=False, send_photos=False, send_videos=False, 
        #     send_roundvideos=False, send_audios=False, send_voices=False, 
        #     send_docs=False, send_plain=False), participants_count=None, 
        #     usernames=[], stories_max_id=None, color=None, profile_color=None, 
        #     emoji_status=None, level=None
        # )

        return {"status": "success", "data": entity}
    except Exception as e:
        raise Exception(f"Failed to send message: {str(e)}")


async def join(phone: str, username_channel: str):
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
        entity = await client.get_entity(username_channel)

        ctype = "group"
        if isinstance(entity,Channel):
            ctype = "channel"

        avatar = ""
        if entity.photo != None:    
            file_stream = io.BytesIO()
            result = await client.download_profile_photo(entity, file=file_stream)
            if result:
                file_stream.seek(0)
                avatar = upload_profile_avatar(file_stream, f"{entity.id}-jpg")

        response = []
        response.append({
            'name' : (entity.title.encode("ascii", "ignore")).decode(),
            'original_id' : entity.id,
            'username' : entity.username,
            'avatar' : avatar,
            'url': "https://t.me/"+ entity.username,
            'created_at' : int(entity.date.timestamp()),
            'type' : ctype,
            'members' : entity.participants_count,
            'chats' : None,
            'access_hash' : entity.access_hash
        })

        section_webhook = "group_search"
        await webhook_push(section_webhook, {
            "query": "",
            "data": response
        })

        # channel_info = {
        #         "id": entity.id,
        #         "name": entity.title or "No Title",
        #         "username": entity.username or "No Username",
        #         "participants_count": full_channel.full_chat.participants_count or 0,
        #         "admins_count": full_channel.full_chat.admins_count or 0,
        #         "banned_count": full_channel.full_chat.kicked_count or 0,
        #         "description": full_channel.full_chat.about or "",
        #         "created_at": entity.date.isoformat() if entity.date else "Unknown"
        #     }

        logging.debug(f"Successfully joined the channel: {username_channel}")
        return {"status": "success", "data": response}
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


async def leave(phone: str, username_channel: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        if username_channel.startswith('@'):
            username_channel = username_channel[1:]

        await client(LeaveChannelRequest(username_channel))
        logging.debug(f"Successfully leave the channel: {username_channel}")
        return {"status": "success", "channel": username_channel}
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
    
    
async def search(phone: str, query: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        result = await client(SearchRequest(q=query,limit=100))

        response = []

        # takeout jika title tidak mengandung keyword
        for o in result.chats:
            # if query.lower() not in o.title.lower():
            #     continue

            time.sleep(3)
            messages = await client.get_messages(o, limit=1) #pass your own args

            ctype = "group"
            if isinstance(o,Channel):
                ctype = "channel"

            # need to download
            # photo=ChatPhoto(photo_id=5771857011674299893
            avatar = ""
            if o.photo != None:    
                file_stream = io.BytesIO()
                result = await client.download_profile_photo(o, file=file_stream)
                if result:
                    file_stream.seek(0)
                    avatar = upload_profile_avatar(file_stream, f"{o.id}-jpg")

            response.append({
                'name' : (o.title.encode("ascii", "ignore")).decode(),
                'original_id' : o.id,
                'username' : o.username,
                'avatar' : avatar,
                'url': "https://t.me/"+ o.username,
                'created_at' : int(o.date.timestamp()),
                'type' : ctype,
                'members' : o.participants_count,
                'chats' : messages.total,
                'access_hash' : o.access_hash
            })
    
        # # ambil data users
        # for o in result.users:
        #     name = o.first_name if str(o.last_name) == 'None' else o.first_name +' '+ o.last_name
        #     response.append({
        #         'name' : (name.encode("ascii", "ignore")).decode(),
        #         'original_id' : o.id,
        #         'username' : o.username,
        #         'created_at' : '',
        #         'type' : 'user',
        #         'members' : 0,
        #         'chats' : 0,
        #         'access_hash' : o.access_hash
        #     })

        section_webhook = "group_search"
        await webhook_push(section_webhook, {
            "query": query,
            "data": response
        })
        
        logging.debug(f"Successfully search group: {query}")

        return {"status": "success", "query": query, "data": response}
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
    

async def get_chats(
    phone: str,
    channel_identifier: str,
    limit: Optional[int] = None,  # Default to None if not provided
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

        print("-- start pulling...")

        while True:
            # Set batch_limit to 100 or the remaining_limit if it is specified
            batch_limit = 50 if remaining_limit is None else min(50, remaining_limit)
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

            print(f"-- got {len(messages.messages)} messages")

            # Log number of messages received
            logging.debug(f"Number of messages received: {len(messages.messages)}")

            new_senders = []
            for user in messages.users:
                if not user.id in senders:
                    sender = await read_sender(client, user, group_id)
                    senders[user.id] = sender
                    new_senders.append(sender)

            # simpan ke webhook
            section_webhook = "senders"
            await webhook_push(section_webhook, new_senders)

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
                else:
                    if isinstance(message.from_id, PeerChannel):
                        pid = message.from_id.channel_id
                    elif isinstance(message.from_id, PeerChat):
                        pid = message.from_id.chat_id
                    elif isinstance(message.from_id, PeerUser):
                        pid = message.from_id.user_id

                if pid in senders:
                    sender = senders[pid]
                else:
                    user = await client.get_entity(pid)
                    sender = await read_sender(client, user, group_id)

                print(f"-- reading message -> {total_messages_read}")

                event = await read_message(client, message, sender)
                new_events.append(event)

                # result.append(event)
                total_messages_read += 1
                offset_id = message.id

            # offset_id = messages.messages[-1].id  # Update offset_id to the last message ID

            print(f"-- offset-id {offset_id}")

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

            print(f"-- remaining {remaining_limit} messages")

            time.sleep(5)

        # await client.disconnect()
        return {"status": "messages_received", "total_messages_read": total_messages_read}

    except Exception as e:
        # await client.disconnect()
        raise Exception(f"Failed to get messages: {str(e)}")


async def get_members(
    phone: str,
    channel_identifier: str,
    limit: Optional[int] = None,  # Default to None if not provided
):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        entity = await client.get_entity(channel_identifier)
        group_id = entity.id

        members = await client.get_participants(entity, aggressive=True)

        iterx = 0
        itermax = len(members)

        senders = []
        for member in members:
            sender = await read_sender(client, member, group_id)
            senders.append(sender)

            iterx += 1
            if (iterx == itermax or iterx%20 == 0):
                section_webhook = "senders"
                await webhook_push(section_webhook, senders)
                senders = []

        return {"status": "success"}

    except Exception as e:
        # await client.disconnect()
        raise Exception(f"Failed to get contacts: {str(e)}")