import hmac
import hashlib
import base64
import time
from config.api_config import API_KEY, API_SECRET

def generate_auth_headers(method, path, body=''):
    timestamp = str(int((time.time() + 300) * 1_000_000))
    message = f"{API_KEY}{timestamp}{method}{path}{body}"
    
    secret_bytes = base64.b64decode(API_SECRET)
    signature = hmac.new(
        secret_bytes,
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    signature_b64 = base64.b64encode(signature).decode('ascii')
    
    return {
        'Arkham-Api-Key': API_KEY,
        'Arkham-Expires': timestamp,
        'Arkham-Signature': signature_b64,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }