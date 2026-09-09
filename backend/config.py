import os
from dotenv import load_dotenv

load_dotenv()

# Gemini LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Database
DB_PATH = os.getenv("DB_PATH")

# BLE
BLE_DEVICE_NAME = os.getenv("BLE_DEVICE_NAME", "BHOOMI_PROBE")
BLE_CHARACTERISTIC_UUID = os.getenv(
    "BLE_CHARACTERISTIC_UUID", "0000ffe1-0000-1000-8000-00805f9b34fb"
)
BLE_ENABLED = os.getenv("BLE_ENABLED").lower() == "true"

# BUFFER SIZE
BUFFER_TARGET_SIZE = int(os.getenv("BUFFER_TARGET_SIZE"))

# LOCAL SLM
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LOCAL_SLM_MODEL = os.getenv("LOCAL_SLM_MODEL", "gemma2:2b")
LOCAL_SLM_TIMEOUT_SECONDS = int(os.getenv("LOCAL_SLM_TIMEOUT_SECONDS", "30"))