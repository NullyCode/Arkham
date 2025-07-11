import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_KEY = os.getenv('ARKHAM_API_KEY', '-')
API_SECRET = os.getenv('ARKHAM_API_SECRET', '-')
BASE_URL = 'https://arkm.com/api'
WS_URL = 'wss://arkm.com/ws'