"""Check API key availability and probe Recraft sizes."""
import httpx
from pathlib import Path

env_path = Path(r"c:\projects\personal\story-app\tools\.env")
env = {}
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")

recraft_key = env.get("RECRAFT_API_KEY", "")
openai_key = env.get("OPENAI_API_KEY", "")
print(f"RECRAFT_API_KEY length : {len(recraft_key)}")
print(f"OPENAI_API_KEY  length : {len(openai_key)} {'(usable)' if len(openai_key) > 20 else '(empty/absent)'}")

# Also probe a few more sizes for Recraft
if recraft_key:
    API_URL = "https://external.api.recraft.ai/v1/images/generations"
    for size in ["1024x768", "768x1024", "512x512", "1024x1024"]:
        r = httpx.post(
            API_URL,
            headers={"Authorization": f"Bearer {recraft_key}", "Content-Type": "application/json"},
            json={"prompt": "test", "style": "vector_illustration", "n": 1, "size": size},
            timeout=90,
        )
        status = "VALID" if r.status_code == 200 else f"INVALID: {r.json().get('message', r.text[:80])}"
        print(f"  Recraft {size:12s}: {status}")
