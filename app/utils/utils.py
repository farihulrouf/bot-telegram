import os
import re
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import logging
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import PeerChannel
from dotenv import load_dotenv

load_dotenv()

space_endpoint = os.getenv('SPACES_ENDPOINT', '')
space_bucket = os.getenv('SPACES_BUCKET', '')
space_folder = os.getenv('SPACES_FOLDER', '')
space_access_key = os.getenv('SPACES_ACCESS_KEY', '')
space_secret_key = os.getenv('SPACES_SECRET_KEY', '')

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
        client.upload_fileobj(file_stream, bucket, path, ExtraArgs={'ACL': 'public-read', 'ContentDisposition': 'inline'})
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

def upload_profile_avatar(file_stream, filename):
    try:
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name='sgp1',
                                endpoint_url=space_endpoint,
                                aws_access_key_id=space_access_key,
                                aws_secret_access_key=space_secret_key)

        path = f"media/tg/a/{filename}"

        # Upload file with public-read ACL
        client.upload_fileobj(file_stream, space_bucket, path, ExtraArgs={'ACL': 'public-read', 'ContentDisposition': 'inline'})
        logging.info(f"File uploaded successfully to DigitalOcean Spaces: {path}")

        # Construct file URL
        file_url = f"{space_endpoint}/{space_bucket}/{path}"
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


def upload_post_media(file_stream, group_id, date_folder, filename):
    try:
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name='sgp1',
                                endpoint_url=space_endpoint,
                                aws_access_key_id=space_access_key,
                                aws_secret_access_key=space_secret_key)

        path = f"media/tg/p/{group_id}/{date_folder}/{filename}"

        # Upload file with public-read ACL
        client.upload_fileobj(file_stream, space_bucket, path, ExtraArgs={'ACL': 'public-read', 'ContentDisposition': 'inline'})
        logging.info(f"File uploaded successfully to DigitalOcean Spaces: {path}")

        # Construct file URL
        file_url = f"{space_endpoint}/{space_bucket}/{path}"
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
