import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import logging
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import PeerChannel
import re

def sanitize_filename(filename):
    return "".join([c if c.isalnum() or c in ['_', '.', '-'] else '_' for c in filename])

def upload_file_to_spaces(file_stream, file_name, channel_name, access_key, secret_key, endpoint, bucket, folder):
    try:
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name='sgp1',
                                endpoint_url=endpoint,
                                aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key)

        path = f"{folder}/{channel_name}/{file_name}"

        # Upload file with public-read ACL
        client.upload_fileobj(file_stream, bucket, path, ExtraArgs={'ACL': 'public-read'})
        logging.info(f"File uploaded successfully to DigitalOcean Spaces: {path}")

        # Construct file URL
        file_url = f"{endpoint}/{bucket}/{path}"
        return file_url

    except NoCredentialsError:
        logging.error("Credentials not available for DigitalOcean Spaces.")
        raise Exception("Credentials not available for DigitalOcean Spaces.")
    except PartialCredentialsError:
        logging.error("Incomplete credentials for DigitalOcean Spaces.")
        raise Exception("Incomplete credentials for DigitalOcean Spaces.")
    except Exception as e:
        logging.error(f"Failed to upload file to DigitalOcean Spaces: {e}")
        raise Exception(f"Failed to upload file to DigitalOcean Spaces: {e}")



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
