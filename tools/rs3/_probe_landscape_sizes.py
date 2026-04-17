"""Probe Recraft API for valid landscape sizes."""
import httpx
from pathlib import Path

env = {}
env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")

key = env["RECRAFT_API_KEY"]
API_URL = "https://external.api.recraft.ai/v1/images/generations"

sizes = ["1792x1024", "1820x1024", "1536x1024", "1707x1024", "1024x576", "1365x768"]
print("Probing landscape sizes for vector_illustration...")
for size in sizes:
    r = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"prompt": "flat vector scene background test", "style": "vector_illustration", "n": 1, "size": size},
        timeout=90,
    )
    if r.status_code == 200:
        data = r.json()
        url = data.get("data", [{}])[0].get("url", "no url")
        print(f"  VALID  : {size}  -> {url[:60]}...")
    else:
        try:
            msg = r.json().get("message", r.text[:120])
        except Exception:
            msg = r.text[:120]
        print(f"  INVALID: {size}  -> {msg}")
