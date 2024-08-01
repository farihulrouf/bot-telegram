# app/utils/utils.py

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import logging

def upload_file_to_spaces(file_stream, file_name, channel_id, access_key, secret_key, endpoint, bucket, folder):
    try:
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name='sgp1',
                                endpoint_url=endpoint,
                                aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key)

        path = f"{folder}/{channel_id}/{file_name}"

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
