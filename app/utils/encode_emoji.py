# utils/encode_emoji.py

import base64

def encode_emoji_to_base64(emoji: str) -> str:
    # Convert the emoji to bytes using UTF-8 encoding
    emoji_bytes = emoji.encode('utf-8')
    # Encode the bytes to a base64 string
    base64_bytes = base64.b64encode(emoji_bytes)
    # Convert the base64 bytes to a string and return
    return base64_bytes.decode('utf-8')
