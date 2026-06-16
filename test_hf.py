import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("HUGGINGFACE_API_KEY")

MODEL = "betuldanismaz/dentai-gemma2-9b-oral-pathology"
URL = f"https://router.huggingface.co/hf-inference/models/{MODEL}"

headers = {"Authorization": f"Bearer {token}"}
payload = {
    "inputs": "<bos><start_of_turn>user\nHello, are you working?<end_of_turn>\n<start_of_turn>model\n",
    "parameters": {"max_new_tokens": 50, "return_full_text": False},
}

print(f"Calling: {URL}")
r = requests.post(URL, headers=headers, json=payload, timeout=60)
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")
