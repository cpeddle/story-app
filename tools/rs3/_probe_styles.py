"""Probe Recraft API for valid style IDs."""
import httpx
from pathlib import Path

env = {}
for line in Path(r'c:\projects\personal\story-app\tools\.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k, _, v = line.partition('=')
        env[k.strip()] = v.strip().strip('"')

key = env['RECRAFT_API_KEY']
styles_to_test = [
    'flat_illustration', 'flat_vector', 'flat_design', 'icon',
    'realistic_image', 'digital_illustration', 'vector_illustration',
    'line_art', 'sketch', 'pixel_art', 'watercolor',
]

print("Testing Recraft style IDs:")
for style in styles_to_test:
    r = httpx.post(
        'https://external.api.recraft.ai/v1/images/generations',
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json={'prompt': 'test', 'style': style, 'n': 1, 'size': '1024x1024'},
        timeout=60,
    )
    if r.status_code == 200:
        data = r.json().get('data', [{}])
        url = data[0].get('url', 'no url') if data else 'no data'
        print(f"  VALID:   {style}")
    else:
        msg = r.json().get('message', r.text[:100])
        print(f"  INVALID: {style!r} — {msg}")
