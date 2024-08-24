import logging
import requests
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv('WEBHOOK_URL')

async def webhook_push(section: str, data):
    headers = {"Content-Type": "application/json"}
    params = {
        "section": section,
        "data": data
    }
    response = requests.post(webhook_url, headers=headers, data=json.dumps(params))
    print("\n response:")
    print(section)
    print(response)