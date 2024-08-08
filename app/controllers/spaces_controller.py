import boto3
from botocore.client import Config
import os

def list_objects_in_folder(bucket, folder):
    try:
        # Initialize a session using the DigitalOcean Spaces endpoint
        s3 = boto3.client('s3',
                          endpoint_url=os.getenv('SPACES_ENDPOINT'),
                          aws_access_key_id=os.getenv('SPACES_ACCESS_KEY'),
                          aws_secret_access_key=os.getenv('SPACES_SECRET_KEY'),
                          config=Config(signature_version='s3v4'))

        # Ensure the folder ends with a '/'
        if not folder.endswith('/'):
            folder += '/'

        # Log the folder we are trying to list
        print(f"Listing objects in bucket: {bucket}, folder: {folder}")

        response = s3.list_objects_v2(Bucket=bucket, Prefix=folder)

        # Log the response for debugging
        print(f"Response: {response}")

        if 'Contents' in response and response['Contents']:
            files = [{'name': obj['Key'], 'size': obj['Size']} for obj in response['Contents']]
            return {'status': 'success', 'files': files}
        else:
            return {'status': 'error', 'detail': 'No files found in the specified folder'}
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"Error occurred: {error_message}")
        return {'status': 'error', 'detail': f"Failed to list data: {error_message}"}
