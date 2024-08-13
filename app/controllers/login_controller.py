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
    finally:
        await client.disconnect()
