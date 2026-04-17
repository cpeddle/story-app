"""
RS-6 N-7 — Default vs Pro Model Comparison
Generates the same scene and sprite using multiple Nano Banana models to evaluate
whether the Pro model credit premium produces meaningfully better output quality.

Models compared:
    nano-banana         (default, 1 credit) = gemini-2.5-flash-image
    nanobanan-2         (Pro, 3 credits)    = unknown underlying model
    nanobanan-2-2k      (Pro 2K, 4 credits)  = high-res variant

Usage:
    python tools/rs6/n7_model_comparison.py

Outputs (all in assets/rs6/model-comparison/):
    throne-room-nano-banana.png
    throne-room-nanobanan-2.png
    throne-room-nanobanan-2-2k.png
    princess-nano-banana.png
    princess-nanobanan-2.png
    princess-nanobanan-2-2k.png
    prompt-log.md entries

NOTE: Pro models require a Pro account. If the account does not have Pro access,
those generations will return 402 or 403 and be logged as skipped.

Preconditions:
    tools/.env: NB_API_KEY=nb_...
"""

import requests
from datetime import datetime
from pathlib import Path
from _image_utils import download_image


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / "tools" / ".env"
OUT_DIR = REPO_ROOT / "assets" / "rs6" / "model-comparison"
PROMPT_LOG = REPO_ROOT / "assets" / "rs6" / "prompt-log.md"
BASE_URL = "https://www.nananobanana.com/api/v1"

# Update to confirmed landscape ratio from N-2
LANDSCAPE_RATIO = "16:9"

MODELS = [
    {"name": "nano-banana",    "credits": 1, "pro": False},
    {"name": "imagine_x_1",    "credits": 1, "pro": False},
    {"name": "nanobanan-2",    "credits": 3, "pro": True},
    {"name": "nanobanan-2-2k", "credits": 4, "pro": True},
]

TESTS = [
    {
        "id": "throne-room",
        "aspect_ratio": LANDSCAPE_RATIO,
        "prompt": (
            "Fairy tale castle throne room interior. Flat geometric kawaii illustration style. "
            "Flat colour fills, bold outlines. Stone floor, ornate throne, colourful banners. "
            "Two arched doorways left and right. Bright warm colours. Wide landscape. "
            "No characters. No gradients, no shading."
        ),
    },
    {
        "id": "princess",
        "aspect_ratio": "1:1",
        "prompt": (
            "Full-body chibi kawaii princess character. Flat geometric shapes, bold black outline. "
            "Pink ballgown, golden crown, brown hair. Plain white background. "
            "No gradients, no shadows. Complete figure head to toe, centred, square canvas."
        ),
    },
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def append_prompt_log(entry: str) -> None:
    PROMPT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPT_LOG, "a", encoding="utf-8") as f:
        f.write("\n" + entry + "\n")


def generate_sync(api_key: str, prompt: str, model: str, aspect_ratio: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "prompt": prompt,
        "selectedModel": model,
        "mode": "sync",
        "aspectRatio": aspect_ratio,
    }
    resp = requests.post(f"{BASE_URL}/generate", headers=headers, json=payload, timeout=120)
    if resp.status_code == 402:
        raise RuntimeError(f"Insufficient credits for model '{model}' (402)")
    if resp.status_code == 403:
        raise RuntimeError(f"Model '{model}' requires Pro account (403 Forbidden)")
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    env = load_env(ENV_FILE)
    api_key = env.get("NB_API_KEY", "")
    if not api_key:
        print("ERROR: NB_API_KEY not found in tools/.env")
        return

    print("=== RS-6 N-7 — Default vs Pro Model Comparison ===")
    print(f"Models: {', '.join(m['name'] for m in MODELS)}")
    print(f"Tests:  {', '.join(t['id'] for t in TESTS)}\n")

    for test in TESTS:
        test_id = test["id"]
        print(f"--- {test_id} ---")
        for model_info in MODELS:
            model_name = model_info["name"]
            # safe filename: replace & with -
            safe_model = model_name.replace("&", "-")
            dest = OUT_DIR / f"{test_id}-{safe_model}.png"
            if dest.exists():
                print(f"  {model_name}: already exists, skipping")
                continue
            try:
                result = generate_sync(api_key, test["prompt"], model_name, test["aspect_ratio"])
                warning = result.get("success") is False and result.get("warning")
                if warning:
                    print(f"  {model_name}: ⚠️  Content safety warning")
                image_urls = result.get("imageUrls", [])
                if image_urls:
                    download_image(image_urls[0], dest)
                    print(f"  {model_name}: ✅ [{model_info['credits']} credits] Saved → {dest.relative_to(REPO_ROOT)}")
                    append_prompt_log(
                        f"## {test_id}-{model_name} — {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"**Tool:** Nano Banana API (`{model_name}`)\n"
                        f"**Mode:** text-to-image (model comparison)\n"
                        f"**Aspect ratio:** {test['aspect_ratio']}\n"
                        f"**Prompt:** {test['prompt']}\n"
                        f"**Credits per image:** {model_info['credits']}\n"
                        f"**Generation ID:** {result.get('generationId', '?')}\n"
                        f"**Credits used:** {result.get('creditsUsed', '?')}\n"
                        f"**Quality vs nano-banana default:** [fill in: noticeably better / equivalent / worse]\n"
                        f"**Credit premium justification:** [fill in: yes / no]\n"
                    )
                else:
                    print(f"  {model_name}: ERROR — no imageUrls: {result}")
            except RuntimeError as exc:
                print(f"  {model_name}: SKIPPED — {exc}")
            except Exception as exc:
                print(f"  {model_name}: ERROR — {exc}")
        print()

    print("=== N-7 complete ===")
    print("Review assets/rs6/model-comparison/ — side-by-side comparison of all models")
    print("Rate: noticeably better / equivalent / worse for each Pro model vs default")
    print("Record credit-cost vs quality verdict in RS-6 §7 (Pipeline Recommendation)")


if __name__ == "__main__":
    main()
