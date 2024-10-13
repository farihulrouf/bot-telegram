import asyncio
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
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        elif channel_identifier.isdigit():
            entity_id = int(channel_identifier)
            entity = await client.get_entity(entity_id)
        else:
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
            entity = await client.get_entity(channel_identifier)

        # Memastikan entity adalah Channel atau Chat yang valid
        if isinstance(entity, (Channel, Chat)):
            full_channel = await client(GetFullChannelRequest(channel=entity))

            # Ambil peserta
            participants = []
            offset = 0
            limit = 100  # Jumlah anggota yang diambil per permintaan

            while True:
                # Ambil peserta dengan delay untuk menghindari rate limiting
                part = await client(GetParticipantsRequest(
                    channel=entity,
                    filter=ChannelParticipantsSearch(""),  # Ambil semua anggota
                    offset=offset,
                    limit=limit,
                    hash=0
                ))

                # Tambahkan peserta yang diambil ke daftar peserta
                participants.extend(part.users)

                # Debugging: Tampilkan jumlah peserta yang diambil sejauh ini
                print(f"Fetched {len(participants)} participants so far...")

                # Jika tidak ada lagi peserta, keluar dari loop
                if not part.users:
                    break

                # Update offset untuk permintaan berikutnya
                offset += len(part.users)

                # Tambahkan delay untuk menghindari rate limiting
                await asyncio.sleep(2)

            # Siapkan data anggota
            members = [{
                "id": user.id,
                "username": user.username or "No Username",
                "phone": user.phone
            } for user in participants]  # Sertakan semua pengguna

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