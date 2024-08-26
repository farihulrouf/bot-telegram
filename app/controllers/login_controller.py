import logging
from telethon.errors import SessionPasswordNeededError, FloodWaitError, InviteHashExpiredError, InviteHashInvalidError
from telethon import TelegramClient, errors
from app.models.telegram_model import sessions

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
    finally:
        await client.disconnect()
