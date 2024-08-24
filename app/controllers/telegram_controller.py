import logging
from telethon.errors import SessionPasswordNeededError , FloodWaitError, InviteHashExpiredError, InviteHashInvalidError
from telethon import TelegramClient, events, utils, errors
from telethon.tl.types import PeerChannel, ChatPhoto, UserProfilePhoto, ChannelFull, InputPhoneContact, InputUser, ChannelParticipantsSearch
from telethon.tl.functions.contacts import GetContactsRequest, SearchRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetHistoryRequest, GetFullChatRequest
from app.models.telegram_model import PhoneNumber, VerificationCode, create_client, sessions, ChannelNamesResponse, ChannelNamesResponseAll, ChannelDetailResponse
from app.models.telegram_model import active_clients, listen_messages
from telethon.tl.types import Channel, Chat, MessageMediaPhoto, MessageMediaDocument, MessageMediaUnsupported
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest, GetFullChannelRequest, GetParticipantsRequest
from app.utils.utils import upload_file_to_spaces  # Pastikan path impor sesuai dengan struktur direktori Anda
from telethon.errors.rpcerrorlist import ChannelsTooMuchError
from fastapi.encoders import jsonable_encoder
from app.controllers.webhook import webhook_push
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

SERVER_IP = os.getenv('SERVER_IP')
SFTP_USERNAME = os.getenv('SFTP_USERNAME')
SSH_KEY_PATH = os.getenv('SSH_KEY_PATH')
PASSPHRASE = os.getenv('PASSPHRASE')

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
        # if client:
        #     await client.disconnect()
        raise Exception(f"Failed to login: {str(e)}")

async def verify(code: VerificationCode):
    client = sessions.get(code.phone)
    if not client:
        raise Exception("Session not found")

    if not client.is_connected():
        await client.connect()

    try:
        await client.sign_in(code.phone, code.code)

        if await client.is_user_authorized():
            me = await client.get_me()
            me_dict = me.to_dict()
            me_dict = process_bytes_in_dict(me_dict)  # Process bytes if any
            logging.debug(f"User logged in: {me}")

            active_clients[code.phone] = asyncio.create_task(listen_messages(code.phone))

            section_webhook = "update_bot_status"
            await webhook_push(section_webhook, {"phone": code.phone})

            return {"status": "logged_in", "user": jsonable_encoder(me_dict)}

        elif code.password:
            await client.sign_in(password=code.password)
            me = await client.get_me()
            me_dict = me.to_dict()
            me_dict = process_bytes_in_dict(me_dict)  # Process bytes if any
            logging.debug(f"User logged in with 2FA: {me}")

            active_clients[code.phone] = asyncio.create_task(listen_messages(code.phone))

            section_webhook = "update_bot_status"
            await webhook_push(section_webhook, {"phone": code.phone})

            return {"status": "logged_in", "user": jsonable_encoder(me_dict)}

        else:
            raise Exception("2FA required but no password provided")

    except SessionPasswordNeededError:
        logging.debug("2FA is required for this account")
        return {"status": "2fa_required"}

    except Exception as e:
        logging.error(f"Failed to verify code: {str(e)}")
        raise Exception(f"Failed to verify code: {str(e)}")

async def logout(phone: PhoneNumber):
    client = sessions.get(phone.phone)
    try:
        if client:
            if not client.is_connected():
                await client.connect()

            await client.log_out()
            logging.debug(f"Successfully logged out for phone: {phone.phone}")
            del sessions[phone.phone]

            section_webhook = "update_bot_status"
            await webhook_push(section_webhook, {"phone": phone.phone})

            # remove task
            task = active_clients.pop(phone.phone, None)
            if not task is None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    return {"status": f"Task for phone {phone.phone} was cancelled"}
                except Exception as e:
                    return {"status": f"Task for phone {phone.phone} raised an exception: {str(e)}"}
        else:
            logging.warning(f"No active session found for phone: {phone.phone}")
            return {"status": "no_active_session"}
        return {"status": "logout success"}
    except Exception as e:
        # if client:
        #     await client.disconnect()
        raise Exception(f"Failed to logout: {str(e)}")

async def status(phone: PhoneNumber):
    client = sessions.get(phone.phone)
    try:
        status = 0
        if client:
            if client.is_connected():
                await client.connect()

            if await client.is_user_authorized():
                status = 1

        return {"status": status}
    except Exception as e:
        # if client:
        #     await client.disconnect()
        raise Exception(f"Failed to get status: {str(e)}")

def process_bytes_in_dict(data):
    for key, value in data.items():
        if isinstance(value, bytes):
            data[key] = value.decode('utf-8', errors='replace')
        elif isinstance(value, dict):
            data[key] = process_bytes_in_dict(value)
        elif isinstance(value, list):
            data[key] = [process_bytes_in_dict(v) if isinstance(v, dict) else v for v in value]
    return data

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
    # finally:
    #     await client.disconnect()

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
    # finally:
    #     await client.disconnect()

async def channel_leave(phone: str, username_channel: str):
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
        return {"status": "leave_channel", "channel": username_channel}
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
    # finally:
    #     await client.disconnect()

async def group_search(phone: str, query: str):
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

            response.append({
                'name' : (o.title.encode("ascii", "ignore")).decode(),
                'original_id' : o.id,
                'username' : o.username,
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

        return {"status": "group_search", "query": query, "data": response}
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
    # finally:
    #     await client.disconnect()

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
        if not isinstance(channel_username, str):
            raise TypeError("channel_username must be a string")

        if channel_username.startswith('@'):
            channel_username = channel_username[1:]

        # Get the entity for the channel
        entity = await client.get_entity(channel_username)

        all_channel_names = []
        total_message_read = 0
        offset_id = 0
        remaining_limit = limit

        while remaining_limit > 0:
            batch_limit = min(remaining_limit, 100)  # Maximum number of messages per batch is 100
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
                if message.message:
                    # Extract channel names from message text
                    response: ChannelNamesResponse = extract_channel_names(message.message)
                    all_channel_names.extend(response.name_channel)
                    total_message_read += 1

            # Update the offset_id for the next batch
            offset_id = messages.messages[-1].id
            remaining_limit -= len(messages.messages)

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
    # finally:
    #     await client.disconnect()


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

async def get_all_contacts(phone: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        contacts = await client(GetContactsRequest(hash=0))
        contact_list = []

        for contact in contacts.users:
            contact_info = {
                "id": contact.id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "phone": contact.phone,
                "username": contact.username
            }
            contact_list.append(contact_info)
        
        # await client.disconnect()
        return {"status": "success", "contacts": contact_list}

    except Exception as e:
        # await client.disconnect()
        raise Exception(f"Failed to get contacts: {str(e)}")

async def get_user_details(phone: str, username: str):
    client = sessions.get(phone)
    
    if not client:
        return {"error": "Session not found or user not logged in"}

    try:
        user = await client.get_input_entity(username)
        full_user = await client(GetFullUserRequest(user))
        #print(full_user)
        # Extracting user details from the full_user object
        user_details = {
            "id": full_user.users[0].id,
            "username": full_user.users[0].username,
            "first_name": full_user.users[0].first_name,
            "last_name": full_user.users[0].last_name,
            "phone": full_user.users[0].phone,
            "bio": full_user.full_user.about,
        }
        
        # Handling profile photo
        if isinstance(full_user.full_user.profile_photo, UserProfilePhoto):
            profile_photo = full_user.full_user.profile_photo
            # Here you can convert the photo reference to a base64 string or URL
            # For simplicity, we'll convert the file reference to base64
            photo_reference = base64.b64encode(profile_photo.file_reference).decode('utf-8')
            user_details["profile_photo"] = photo_reference
        else:
            user_details["profile_photo"] = None
        
        return user_details
    except Exception as e:
        return {"error": str(e)}


async def upload_file_to_server(file_stream: io.BytesIO, remote_file_path: str, server_ip: str, sftp_username: str, ssh_key_path: str, passphrase: str):
    try:
        # Create an SSH transport object
        transport = paramiko.Transport((server_ip, 22))
        
        # Load the private key with passphrase
        private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path, password=passphrase)
        
        # Connect to the server using the transport object and private key
        transport.connect(username=sftp_username, pkey=private_key)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Upload the file stream directly
        with sftp.open(remote_file_path, 'wb') as remote_file:
            logging.debug(f"Uploading file to {remote_file_path}")
            remote_file.write(file_stream.getvalue())
        
        sftp.close()
        transport.close()
        logging.info(f"File uploaded successfully to {remote_file_path}")

    except Exception as e:
        logging.error(f"Error uploading file: {e}")

async def get_all_channels(phone: str) -> ChannelNamesResponseAll:
    client = sessions.get(phone)
    if not client:
        logging.error(f"Session not found for phone: {phone}")
        raise HTTPException(status_code=404, detail="Session not found")
    logging.debug(f"Session found for phone: {phone}")

    if not client.is_connected():
        logging.debug(f"Connecting client for phone: {phone}")
        await client.connect()

    try:
        dialogs = await client.get_dialogs()
        logging.debug(f"Retrieved dialogs for phone: {phone}")

        channels = []
        groups = []

        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel):
                name = f"@{entity.username}" if entity.username else f"@{entity.title}"
                channels.append({'name_channel_group': name, 'status': True})
            elif isinstance(entity, Chat):
                name = f"@{entity.title}"
                groups.append({'name_channel_group': name, 'status': False})

        logging.debug(f"Extracted channel and group names for phone: {phone}")

        response = ChannelNamesResponseAll(
            total_channels=len(channels),
            total_groups=len(groups),
            channels_groups=channels + groups
        )

        # await client.disconnect()
        logging.debug(f"Client disconnected for phone: {phone}")

        return response

    except ChannelsTooMuchError as e:
        logging.error(f"Failed to get channels: {str(e)}")
        # await client.disconnect()
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")
    except Exception as e:
        logging.error(f"Failed to get channels and groups: {str(e)}")
        # await client.disconnect()
        raise HTTPException(status_code=500, detail=f"Failed to get channels and groups: {str(e)}")
