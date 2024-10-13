from fastapi import HTTPException
from app.models.telegram_model import sessions
import logging
from telethon.tl.types import Channel, Chat, ChannelParticipantsSearch
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.sync import TelegramClient

async def get_channel_details(phone: str, channel_identifier: str):
    client = sessions.get(phone)
    if not client:
        raise Exception("Session not found")
    
    if not client.is_connected():
        await client.connect()

    try:
        entity = None

        # Menentukan apakah identifier adalah ID atau username
        if channel_identifier.startswith('-') and channel_identifier[1:].isdigit():
            # Menganggap sebagai ID negatif
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        elif channel_identifier.isdigit():
            # Menganggap sebagai ID positif
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        else:
            # Menganggap sebagai username
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            entity = await client.get_entity(channel_identifier)

        # Memastikan entity adalah Channel atau Chat yang valid
        if isinstance(entity, (Channel, Chat)):
            full_channel = await client(GetFullChannelRequest(channel=entity))

            # Ambil peserta
            participants = await client(GetParticipantsRequest(
                channel=entity,
                filter=ChannelParticipantsSearch(""),  # Ambil semua anggota
                offset=0,  # Mulai dari awal
                limit=100,  # Batasi jumlah yang diambil
                hash=0  # Set hash ke 0
            ))

            # Debugging: Periksa jumlah peserta yang diambil
            print(f"Number of participants fetched: {len(participants.users)}")

            # Siapkan data anggota
            members = [{
                "id": user.id,  # ID pengguna
                "username": user.username or "No Username",  # Username
                "phone": user.phone  # Nomor telepon
            } for user in participants.users if user.phone]  # Hanya menyertakan pengguna dengan nomor telepon

            # Debugging: Periksa data anggota yang diambil
            print("Check data members:", members)

            # Siapkan informasi channel
            channel_info = {
                "id": entity.id,
                "name": entity.title or "No Title",
                "username": entity.username or "No Username",
                "participants_count": full_channel.full_chat.participants_count or 0,
                "admins_count": full_channel.full_chat.admins_count or 0,
                "banned_count": full_channel.full_chat.kicked_count or 0,
                "description": full_channel.full_chat.about or "",
                "created_at": entity.date.isoformat() if entity.date else "Unknown",
                "members": members  # Sertakan anggota dalam respons
            }

            # Kembalikan informasi channel dengan anggota
            return {"status": "success", "channel_info": channel_info}

        else:
            raise Exception("The identifier does not correspond to a channel or group.")
    
    except Exception as e:
        raise Exception(f"Failed to get channel details: {str(e)}")

