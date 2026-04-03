import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from agent package dir (where ADK expects it)
_agent_dir = Path(__file__).resolve().parent.parent
load_dotenv(_agent_dir / ".env")

from google import genai

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
