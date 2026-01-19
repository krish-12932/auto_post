import os
from dotenv import load_dotenv

load_dotenv()

# Sahi Tareeka: Hum 'KEYS' use karte hain, values nahi. Values .env file me hain.
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OWNER_ID = os.getenv("OWNER_ID")

if not all([BOT_TOKEN, CHANNEL_ID, OWNER_ID]):
    print("❌ ERROR: Values missing in .env file!")
    print(f"BOT_TOKEN: {BOT_TOKEN}")
    print(f"CHANNEL_ID: {CHANNEL_ID}")
    print(f"OWNER_ID: {OWNER_ID}")
    raise ValueError("Missing configuration. Please check .env file.")
else:
    print("✅ Configuration loaded successfully.")
