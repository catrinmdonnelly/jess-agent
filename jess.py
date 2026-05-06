"""
Jess — daily Instagram agent.

Runs three times a day (default UK time):

    08:30  — mode=plan          (Claude → image gen → hook card → upload, save state)
    12:00  — mode=publish_slot_1 (read state, post carousel slot 1)
    18:00  — mode=publish_slot_2 (read state, post carousel slot 2)

Each post is a 2-slide carousel:
    slide 1 — hook card (text on a brand-colour background, rendered with PIL)
    slide 2 — generated illustration (style is controlled by your prompt library)

Each run picks its mode from the current local hour. GitHub Actions cron fires
in UTC, so we schedule one cron per slot for BST and one for GMT for UK users.
The script ignores cron fires that fall on the wrong local hour.

Exit code 0 on success, 1 on any step failing.
"""

from __future__ import annotations

import base64
import json
import os
import re
import smtplib
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
CONFIG = ROOT / "config"
EXCHANGE = ROOT / "exchange"
PLANS = ROOT / "plans"
IMAGES = ROOT / "images"
FONTS_DIR = ROOT / "fonts"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"

TIMEZONE = ZoneInfo(os.environ.get("AGENT_TIMEZONE", "Europe/London"))

MODES = {"plan", "publish_slot_1", "publish_slot_2", "skip"}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def env(name: str, required: bool = True, default: str = "") -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def now_local() -> datetime:
    return datetime.now(TIMEZONE)


def today_key() -> str:
    return now_local().strftime("%Y-%m-%d")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def read_if_exists(path: Path, fallback: str = "") -> str:
    return path.read_text() if path.exists() else fallback


def hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"invalid hex colour: {s!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ─── Mode dispatch ─────────────────────────────────────────────────────────────

def determine_mode() -> str:
    """Pick the run mode from the current local hour, unless overridden by JESS_MODE env."""
    forced = env("JESS_MODE", required=False).strip()
    if forced:
        if forced not in MODES:
            raise RuntimeError(f"Invalid JESS_MODE: {forced}. Must be one of {MODES}.")
        return forced

    plan_hour = int(env("JESS_PLAN_HOUR", required=False, default="8"))
    slot1_hour = int(env("JESS_SLOT1_HOUR", required=False, default="12"))
    slot2_hour = int(env("JESS_SLOT2_HOUR", required=False, default="18"))

    hour = now_local().hour
    if hour == plan_hour:
        return "plan"
    if hour == slot1_hour:
        return "publish_slot_1"
    if hour == slot2_hour:
        return "publish_slot_2"
    return "skip"


# ─── Result tracking ───────────────────────────────────────────────────────────

@dataclass
class SlotResult:
    slot: int
    moment: str = ""
    hook: str = ""
    caption: str = ""
    hashtags: str = ""
    hook_image_path: str = ""
    hook_image_url: str = ""
    scene_image_path: str = ""
    scene_image_url: str = ""
    scene_source: str = ""
    host: str = ""
    media_id: str = ""
    prepared: bool = False
    posted: bool = False
    error: str = ""


@dataclass
class RunResult:
    mode: str
    date: str
    started_at: str
    slots: list[SlotResult] = field(default_factory=list)
    planning_error: str = ""
    posting_error: str = ""
    fully_successful: bool = False

    @property
    def summary_line(self) -> str:
        if self.mode == "plan":
            ok = sum(1 for s in self.slots if s.prepared)
            return f"Jess plan: {ok}/{len(self.slots) or 2} ready"
        if self.mode.startswith("publish_slot_"):
            slot = self.mode[-1]
            posted = any(s.posted for s in self.slots)
            return f"Jess slot {slot}: {'posted' if posted else 'failed'}"
        return f"Jess ({self.mode})"


# ─── Step 1: Plan ──────────────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """You are Jess, an Instagram content lead.

Each day you plan two Instagram posts, one for midday and one for evening.

Each post is a 2-slide carousel:
  - Slide 1: a hook card (one jarring sentence, rendered as text on a brand-colour background)
  - Slide 2: an illustration of the scene (the style is described in your image prompt library)

Each post has:
  1. A moment (what's actually happening for the person in the scene)
  2. A hook line — ONE sentence, max 95 characters. Jarring. Names something specific. Must make someone stop scrolling.
  3. A 2-3 sentence caption teaser (sets up the moment, does not resolve it). This is the Instagram caption.
  4. A 3-4 paragraph story in third person (a small narrative arc, for reference / future expansion)
  5. An image brief for slide 2 (specific enough to generate a useful image — describe the scene, the mood, what's in frame, what isn't. NO text in the illustration.)
  6. Exactly 5 hashtags from the bank

Rules:
  - Hook must be ONE sentence, under 95 characters. Short is better. Jarring is better.
  - Never the same environment two days in a row
  - Mix tones (one warm, one quieter)
  - Rotate hashtag sets
  - Full sentences, conversational. No em dashes. No staccato fragments.
  - No generic AI phrases. No "unlock", "empower", "leverage", "take to the next level".

Output strict JSON only, no prose, matching this schema:
{
  "posts": [
    {
      "slot": 1,
      "moment": "short description",
      "hook": "one jarring sentence, under 95 characters",
      "caption": "2-3 sentence teaser",
      "story": "3-4 paragraphs, third person",
      "image_brief": "detailed image prompt, no text in image",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
    },
    { "slot": 2, "...": "same shape" }
  ]
}"""


def load_system_prompt() -> str:
    custom = read_if_exists(CONFIG / "system-prompt.md", "")
    return custom.strip() if custom.strip() else DEFAULT_SYSTEM_PROMPT


def generate_plan() -> dict:
    """Call Claude to generate today's 2 posts. Returns parsed JSON dict."""
    log("plan: asking Claude for today's two posts")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed — run: pip install -r requirements.txt")

    brand = read_if_exists(CONFIG / "brand-voice.md",
                           "(brand-voice.md missing — fill in config/brand-voice.md)")
    hashtags = read_if_exists(CONFIG / "hashtag-bank.md",
                              "(hashtag-bank.md missing — fill in config/hashtag-bank.md)")
    prompts = read_if_exists(CONFIG / "image-prompt-library.md",
                             "(image-prompt-library.md missing — fill in config/image-prompt-library.md)")

    recent_plans = []
    for i in range(1, 8):
        path = PLANS / f"{(now_local() - timedelta(days=i)).strftime('%Y-%m-%d')}.md"
        if path.exists():
            recent_plans.append(f"--- {path.stem} ---\n{path.read_text()}")

    direction = read_if_exists(EXCHANGE / "cleo-direction-latest.md",
                               "(no weekly direction this week)")
    seo_trends = read_if_exists(EXCHANGE / "seo-trends-latest.md",
                                "(no SEO trend findings this week)")

    user_message = f"""Today is {now_local().strftime('%A %d %B %Y')}.

BRAND VOICE:
{brand}

HASHTAG BANK:
{hashtags}

IMAGE PROMPT LIBRARY (use this style for the slide 2 illustration):
{prompts}

WEEKLY DIRECTION (from your strategy agent, if any — follow this if it's here):
{direction}

SEO TRENDS (search angles to weave in where natural):
{seo_trends}

LAST 7 DAYS OF POSTS (for variety, do not repeat):
{chr(10).join(recent_plans) if recent_plans else '(none — this is a fresh start)'}

Plan today's two posts. Return JSON only."""

    client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=env("ANTHROPIC_MODEL", required=False, default="claude-opus-4-6"),
        max_tokens=4000,
        system=load_system_prompt(),
        messages=[{"role": "user", "content": user_message}],
    )

    text = resp.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    plan = json.loads(text)
    if "posts" not in plan or len(plan["posts"]) != 2:
        raise RuntimeError(f"Plan JSON malformed: expected 2 posts, got {plan}")

    PLANS.mkdir(exist_ok=True)
    md_path = PLANS / f"{today_key()}.md"
    md_path.write_text(_plan_to_markdown(plan))
    log(f"  plan saved: {md_path.relative_to(ROOT)}")

    return plan


def _plan_to_markdown(plan: dict) -> str:
    business = env("BUSINESS_NAME", required=False, default="Jess")
    out = [f"# {business} Instagram — {today_key()}\n"]
    for p in plan["posts"]:
        slot1_hour = int(env("JESS_SLOT1_HOUR", required=False, default="12"))
        slot2_hour = int(env("JESS_SLOT2_HOUR", required=False, default="18"))
        hour = slot1_hour if p["slot"] == 1 else slot2_hour
        out.append(f"### POST {p['slot']} — {now_local().strftime('%A %d %B')}, {hour:02d}:00\n")
        out.append(f"**Moment:** {p['moment']}\n")
        out.append(f"**Hook (slide 1):** {p['hook']}\n")
        out.append(f"**Caption:**\n\n{p['caption']}\n")
        out.append(f"**Story (reference):**\n\n{p['story']}\n")
        out.append(f"**Image brief (slide 2):** {p['image_brief']}\n")
        out.append(f"**Hashtags:** {' '.join(p['hashtags'])}\n")
        out.append("---\n")
    return "\n".join(out)


# ─── Step 2a: Generate hook card (slide 1) ─────────────────────────────────────

DEFAULT_BG = "#1a2332"           # ink navy
DEFAULT_TEXT = "#f5efe6"         # warm off-white
DEFAULT_ACCENT = "#eba18a"       # soft coral

FONT_REGULAR_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
FONT_ITALIC_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf"
FONT_REGULAR_NAME = "DisplayFont[wght].ttf"
FONT_ITALIC_NAME = "DisplayFont-Italic[wght].ttf"


def _ensure_fonts() -> None:
    """Download display font files if not cached. Override URLs via FONT_REGULAR_URL / FONT_ITALIC_URL."""
    FONTS_DIR.mkdir(exist_ok=True)
    pairs = [
        (FONT_REGULAR_NAME, env("FONT_REGULAR_URL", required=False, default=FONT_REGULAR_URL)),
        (FONT_ITALIC_NAME, env("FONT_ITALIC_URL", required=False, default=FONT_ITALIC_URL)),
    ]
    for name, url in pairs:
        path = FONTS_DIR / name
        if path.exists() and path.stat().st_size > 10_000:
            continue
        log(f"  fetching font: {name}")
        req = Request(url, headers={"User-Agent": "jess-agent/1.0"})
        with urlopen(req, timeout=30) as resp:
            path.write_bytes(resp.read())


def _load_font(size: int, weight: int = 400, italic: bool = False):
    from PIL import ImageFont
    name = FONT_ITALIC_NAME if italic else FONT_REGULAR_NAME
    font = ImageFont.truetype(str(FONTS_DIR / name), size=size)
    try:
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    return font


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def build_hook_card(hook_text: str, out_path: Path) -> None:
    """Render the slide-1 hook card — text on a brand-colour background, 1080x1080 PNG."""
    from PIL import Image, ImageDraw

    _ensure_fonts()

    bg = hex_to_rgb(env("BRAND_BG_COLOR", required=False, default=DEFAULT_BG))
    text_color = hex_to_rgb(env("BRAND_TEXT_COLOR", required=False, default=DEFAULT_TEXT))
    accent_color = hex_to_rgb(env("BRAND_ACCENT_COLOR", required=False, default=DEFAULT_ACCENT))

    business_name = env("BUSINESS_NAME", required=False, default="").upper()
    instagram_handle = env("INSTAGRAM_HANDLE", required=False, default="")

    SIZE = 1080
    MARGIN_X = 110
    TOP_WORDMARK_Y = 70
    BOTTOM_HANDLE_Y = SIZE - 90
    TEXT_BLOCK_TOP = 200
    TEXT_BLOCK_BOTTOM = SIZE - 180

    img = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(img)

    if business_name:
        wordmark = "   ".join(business_name)  # tracked-out spacing
        wm_font = _load_font(26, weight=400)
        wbb = draw.textbbox((0, 0), wordmark, font=wm_font)
        draw.text(
            ((SIZE - (wbb[2] - wbb[0])) / 2, TOP_WORDMARK_Y),
            wordmark, font=wm_font, fill=accent_color,
        )

    if instagram_handle:
        hn_font = _load_font(24, weight=400, italic=True)
        hbb = draw.textbbox((0, 0), instagram_handle, font=hn_font)
        draw.text(
            ((SIZE - (hbb[2] - hbb[0])) / 2, BOTTOM_HANDLE_Y),
            instagram_handle, font=hn_font, fill=text_color,
        )

    max_width = SIZE - 2 * MARGIN_X
    max_height = TEXT_BLOCK_BOTTOM - TEXT_BLOCK_TOP

    chosen_font = None
    chosen_lines: list[str] = []
    chosen_size = 48
    for size in (104, 96, 88, 80, 72, 64, 56, 48, 42, 38):
        trial_font = _load_font(size, weight=700)
        lines = _wrap_text(hook_text, trial_font, max_width, draw)
        line_height = int(size * 1.28)
        total_height = line_height * len(lines)
        widest = max(
            (draw.textbbox((0, 0), ln, font=trial_font)[2] -
             draw.textbbox((0, 0), ln, font=trial_font)[0]) for ln in lines
        ) if lines else 0
        if total_height <= max_height and widest <= max_width:
            chosen_font = trial_font
            chosen_lines = lines
            chosen_size = size
            break
    if chosen_font is None:
        chosen_font = _load_font(38, weight=700)
        chosen_lines = _wrap_text(hook_text, chosen_font, max_width, draw)
        chosen_size = 38

    line_height = int(chosen_size * 1.28)
    total_height = line_height * len(chosen_lines)
    y = TEXT_BLOCK_TOP + (max_height - total_height) // 2

    for line in chosen_lines:
        bbox = draw.textbbox((0, 0), line, font=chosen_font)
        x = (SIZE - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=chosen_font, fill=text_color)
        y += line_height

    img.save(out_path, format="PNG", optimize=True)
    log(f"  hook card rendered: {out_path.name} ({chosen_size}pt, {len(chosen_lines)} lines)")


# ─── Step 2b: Illustrate (slide 2) ─────────────────────────────────────────────

def generate_image(prompt: str, out_path: Path) -> str:
    """Generate one image, returning the source used ('gemini' or 'openai'). Raises on total failure."""
    log(f"  generating image: {out_path.name}")

    try:
        return _generate_with_gemini(prompt, out_path)
    except Exception as e:
        log(f"  gemini failed ({e}) — falling back to OpenAI")

    try:
        return _generate_with_openai(prompt, out_path)
    except Exception as e:
        raise RuntimeError(f"both image backends failed: {e}")


def _generate_with_gemini(prompt: str, out_path: Path) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=env("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=env("GEMINI_MODEL", required=False, default="gemini-2.0-flash-exp"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    candidates = getattr(resp, "candidates", None) or []
    if not candidates:
        feedback = getattr(resp, "prompt_feedback", None)
        block_reason = getattr(feedback, "block_reason", None) if feedback else None
        raise RuntimeError(
            "gemini returned no candidates"
            + (f" (block_reason={block_reason})" if block_reason else "")
        )

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) if content else None
    if not parts:
        finish_reason = getattr(candidates[0], "finish_reason", None)
        raise RuntimeError(
            "gemini returned empty content"
            + (f" (finish_reason={finish_reason})" if finish_reason else "")
        )

    for part in parts:
        if getattr(part, "inline_data", None):
            out_path.write_bytes(part.inline_data.data)
            _crop_white_border(out_path)
            return "gemini"
    raise RuntimeError("gemini returned no image data in response")


def _generate_with_openai(prompt: str, out_path: Path) -> str:
    api_key = env("OPENAI_API_KEY", required=False)
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set — no fallback configured")

    body = json.dumps({
        "model": env("OPENAI_IMAGE_MODEL", required=False, default="gpt-image-1"),
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1,
    }).encode()
    req = Request("https://api.openai.com/v1/images/generations", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    resp = urlopen(req, timeout=90)
    result = json.loads(resp.read().decode())
    b64 = result["data"][0]["b64_json"]
    out_path.write_bytes(base64.b64decode(b64))
    return "openai"


def _crop_white_border(path: Path) -> None:
    try:
        from PIL import Image, ImageChops
        img = Image.open(path).convert("RGB")
        original = img.size
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bbox = ImageChops.difference(img, bg).getbbox()
        if bbox:
            pad = 4
            w, h = img.size
            bbox = (
                max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                min(w, bbox[2] + pad), min(h, bbox[3] + pad),
            )
            img.crop(bbox).resize(original, Image.LANCZOS).save(path)
    except Exception as e:
        log(f"  (border crop skipped: {e})")


# ─── Step 3: Upload ────────────────────────────────────────────────────────────

def upload_image(path: Path) -> tuple[str, str]:
    """Upload image and return (public_url, host_used). Tries Cloudinary then WordPress."""
    if env("CLOUDINARY_CLOUD_NAME", required=False):
        try:
            url = _upload_cloudinary(path)
            return url, "cloudinary"
        except Exception as e:
            log(f"  cloudinary failed ({e}) — falling back to WordPress")

    if env("WP_SITE_URL", required=False):
        url = _upload_wordpress(path)
        return url, "wordpress"

    raise RuntimeError(
        "No image host configured. Set CLOUDINARY_CLOUD_NAME + CLOUDINARY_UPLOAD_PRESET, "
        "or WP_SITE_URL + WP_USERNAME + WP_PASSWORD. See SETUP.md."
    )


def _upload_cloudinary(path: Path) -> str:
    cloud_name = env("CLOUDINARY_CLOUD_NAME")
    preset = env("CLOUDINARY_UPLOAD_PRESET")

    boundary = f"CloudinaryBoundary{int(time.time())}"
    filename = path.name
    data = path.read_bytes()
    mime = "image/png"

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="upload_preset"\r\n\r\n'
        f"{preset}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

    req = Request(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        data=body, method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    resp = urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())
    url = result.get("secure_url")
    if not url:
        raise RuntimeError(f"cloudinary response missing secure_url: {result}")
    return url


def _upload_wordpress(path: Path) -> str:
    site = env("WP_SITE_URL").rstrip("/")
    user = env("WP_USERNAME")
    password = env("WP_PASSWORD")

    data = path.read_bytes()
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()

    req = Request(f"{site}/wp-json/wp/v2/media", data=data, method="POST")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "image/png")
    req.add_header("Content-Disposition", f'attachment; filename="{path.name}"')

    resp = urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())
    url = result.get("source_url")
    if not url:
        raise RuntimeError(f"wordpress response missing source_url: {result}")
    return url


# ─── Step 4: Post to Instagram (carousel) ──────────────────────────────────────

def meta_request(endpoint: str, params: dict, method: str = "POST") -> dict:
    url = f"https://graph.facebook.com/v21.0/{endpoint}"
    if method == "GET":
        url += "?" + urlencode(params)
        req = Request(url)
    else:
        req = Request(url, data=urlencode(params).encode(), method="POST")
    try:
        resp = urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except HTTPError as e:
        raise RuntimeError(f"meta api {endpoint}: {e.code} {e.read().decode()}")


def post_carousel(image_urls: list[str], caption: str) -> str:
    if not image_urls:
        raise RuntimeError("post_carousel needs at least one image url")

    ig_id = env("META_INSTAGRAM_ACCOUNT_ID")
    token = env("META_PAGE_ACCESS_TOKEN")

    item_ids: list[str] = []
    for i, url in enumerate(image_urls, 1):
        log(f"  creating carousel item {i}/{len(image_urls)}")
        result = meta_request(f"{ig_id}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        })
        item_id = result.get("id")
        if not item_id:
            raise RuntimeError(f"no item id in meta response: {result}")
        item_ids.append(item_id)

    log("  waiting for Meta to process carousel items")
    time.sleep(10)

    log("  creating carousel container")
    result = meta_request(f"{ig_id}/media", {
        "media_type": "CAROUSEL",
        "caption": caption,
        "children": ",".join(item_ids),
        "access_token": token,
    })
    creation_id = result.get("id")
    if not creation_id:
        raise RuntimeError(f"no carousel creation id: {result}")

    time.sleep(5)
    log("  publishing carousel")
    result = meta_request(f"{ig_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    media_id = result.get("id")
    if not media_id:
        raise RuntimeError(f"publish failed, no media id: {result}")
    return media_id


def build_caption(post: dict) -> str:
    parts = [post["caption"].strip(), "", " ".join(post["hashtags"])]
    return "\n".join(parts)


# ─── Step 5: Report + email ────────────────────────────────────────────────────

def write_report(run: RunResult) -> Path:
    ts = now_local().strftime("%Y-%m-%d-%H%M")
    path = REPORTS / f"jess-{ts}-{run.mode}.json"
    path.parent.mkdir(exist_ok=True)

    if run.fully_successful:
        status = "completed"
        headline = run.summary_line
        actions: list[str] = []
    else:
        status = "needs_input"
        error_bits = [run.planning_error, run.posting_error] + [s.error for s in run.slots if s.error]
        headline = f"Jess {run.mode}: failed — {'; '.join(b for b in error_bits if b)[:140]}"
        actions = [
            "Check the GitHub Actions run page for full logs",
            "Re-run the workflow manually once the issue is fixed",
        ]

    payload = {
        "agent": "jess",
        "agent_display": "Jess — Instagram",
        "timestamp": now_local().strftime("%Y-%m-%dT%H:%M:%S"),
        "status": status,
        "headline": headline,
        "summary": json.dumps(asdict(run), indent=2, default=str),
        "actions_needed": actions,
        "files_created": [
            p for s in run.slots
            for p in (s.hook_image_path, s.scene_image_path)
            if p
        ],
        "full_brief_path": f"plans/{run.date}.md",
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    log(f"  report written: {path.relative_to(ROOT)}")
    return path


def send_failure_email(run: RunResult) -> None:
    to_addr = env("FAILURE_EMAIL_TO", required=False)
    if not to_addr:
        log("  (email alert skipped — FAILURE_EMAIL_TO not set)")
        return
    host = env("FAILURE_EMAIL_SMTP_HOST", required=False, default="smtp.gmail.com")
    from_addr = env("FAILURE_EMAIL_FROM", required=False, default=to_addr)
    password = env("FAILURE_EMAIL_SMTP_PASS", required=False)
    if not password:
        log("  (email alert skipped — FAILURE_EMAIL_SMTP_PASS not set)")
        return

    run_url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"

    body = [
        f"Jess's {run.mode} run had a problem on {run.date}.",
        "",
        f"Summary: {run.summary_line}",
        "",
    ]
    if run.planning_error:
        body.append(f"Planning: {run.planning_error}")
    if run.posting_error:
        body.append(f"Posting:  {run.posting_error}")
    for s in run.slots:
        if s.error:
            body.append(f"Slot {s.slot}: {s.error}")
    body.extend(["", f"GitHub Actions run: {run_url}", ""])

    msg = EmailMessage()
    msg["Subject"] = f"Jess: {run.mode} failed on {run.date}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content("\n".join(body))

    with smtplib.SMTP_SSL(host, 465, timeout=30) as smtp:
        smtp.login(from_addr, password)
        smtp.send_message(msg)
    log(f"  failure email sent to {to_addr}")


# ─── Daily state file ──────────────────────────────────────────────────────────

STATE_DIR = LOGS / "daily-state"


def save_daily_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"{today_key()}.json"
    path.write_text(json.dumps(state, indent=2, default=str))
    log(f"  state saved: {path.relative_to(ROOT)}")


def load_daily_state() -> dict:
    path = STATE_DIR / f"{today_key()}.json"
    if not path.exists():
        raise RuntimeError(
            f"no state file for {today_key()} — morning plan run either hasn't happened "
            f"yet or failed. Re-run with JESS_MODE=plan first."
        )
    return json.loads(path.read_text())


# ─── Posted log ────────────────────────────────────────────────────────────────

LOG_PATH = LOGS / "posted-log.json"


def load_posted_log() -> dict:
    if not LOG_PATH.exists():
        return {}
    return json.loads(LOG_PATH.read_text())


def save_to_posted_log(key: str, data: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_posted_log()
    existing[key] = data
    LOG_PATH.write_text(json.dumps(existing, indent=2, default=str))


def already_posted(slot: int) -> bool:
    key = f"{today_key()}-slot{slot}"
    return key in load_posted_log()


# ─── Phases ────────────────────────────────────────────────────────────────────

def run_plan(run: RunResult) -> int:
    log("mode: plan")
    run.slots = [SlotResult(slot=1), SlotResult(slot=2)]

    try:
        plan = generate_plan()
    except Exception as e:
        traceback.print_exc()
        run.planning_error = f"planning failed: {e}"
        write_report(run)
        send_failure_email(run)
        return 1

    posts_by_slot = {p["slot"]: p for p in plan["posts"]}

    for slot_result in run.slots:
        slot = slot_result.slot
        post = posts_by_slot.get(slot)
        if not post:
            slot_result.error = f"plan missing slot {slot}"
            continue

        slot_result.moment = post["moment"]
        slot_result.hook = post["hook"]
        slot_result.caption = post["caption"]
        slot_result.hashtags = " ".join(post["hashtags"])

        hook_path = IMAGES / f"{today_key()}-slot{slot}-hook.png"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            build_hook_card(post["hook"], hook_path)
            slot_result.hook_image_path = str(hook_path.relative_to(ROOT))
        except Exception as e:
            traceback.print_exc()
            slot_result.error = f"hook card generation failed: {e}"
            continue

        scene_path = IMAGES / f"{today_key()}-slot{slot}-scene.png"
        scene_ok = False
        try:
            slot_result.scene_source = generate_image(post["image_brief"], scene_path)
            slot_result.scene_image_path = str(scene_path.relative_to(ROOT))
            scene_ok = True
        except Exception as e:
            log(f"  scene generation failed ({e}) — will use hook card as fallback")
            slot_result.scene_source = "hook_fallback"

        try:
            hook_url, host = upload_image(hook_path)
            slot_result.hook_image_url = hook_url
            slot_result.host = host

            if scene_ok:
                scene_url, _ = upload_image(scene_path)
                slot_result.scene_image_url = scene_url
            else:
                slot_result.scene_image_url = hook_url

            slot_result.prepared = True
            log(f"  slot {slot} prepared: {host} ({'hook + scene' if scene_ok else 'hook only'})")
        except Exception as e:
            traceback.print_exc()
            slot_result.error = f"image upload failed: {e}"
            continue

    state = {
        "date": today_key(),
        "planned_at": now_local().isoformat(),
        "posts": [
            {
                "slot": s.slot,
                "moment": s.moment,
                "hook": s.hook,
                "caption_raw": posts_by_slot[s.slot]["caption"],
                "hashtags": posts_by_slot[s.slot]["hashtags"],
                "caption_final": build_caption(posts_by_slot[s.slot]),
                "hook_image_url": s.hook_image_url,
                "scene_image_url": s.scene_image_url,
                "hook_image_path": s.hook_image_path,
                "scene_image_path": s.scene_image_path,
                "scene_source": s.scene_source,
                "host": s.host,
            }
            for s in run.slots if s.prepared
        ],
    }
    save_daily_state(state)

    run.fully_successful = all(s.prepared for s in run.slots)
    write_report(run)

    if not run.fully_successful:
        send_failure_email(run)
        return 1

    log(f"done — {run.summary_line}")
    return 0


def run_publish(run: RunResult, slot: int) -> int:
    log(f"mode: publish_slot_{slot}")
    run.slots = [SlotResult(slot=slot)]
    sr = run.slots[0]

    if already_posted(slot):
        sr.posted = True
        sr.error = "already posted today (log says so)"
        log(f"  slot {slot} already posted — nothing to do")
        run.fully_successful = True
        write_report(run)
        return 0

    try:
        state = load_daily_state()
    except Exception as e:
        log(f"  ERROR: {e}")
        sr.error = str(e)
        run.posting_error = str(e)
        write_report(run)
        send_failure_email(run)
        return 1

    post_state = next((p for p in state["posts"] if p["slot"] == slot), None)
    if not post_state:
        msg = f"state has no prepared post for slot {slot}"
        log(f"  ERROR: {msg}")
        sr.error = msg
        run.posting_error = msg
        write_report(run)
        send_failure_email(run)
        return 1

    sr.moment = post_state["moment"]
    sr.hook = post_state.get("hook", "")
    sr.caption = post_state["caption_raw"]
    sr.hashtags = " ".join(post_state["hashtags"])
    sr.hook_image_path = post_state["hook_image_path"]
    sr.hook_image_url = post_state["hook_image_url"]
    sr.scene_image_path = post_state["scene_image_path"]
    sr.scene_image_url = post_state["scene_image_url"]
    sr.scene_source = post_state["scene_source"]
    sr.host = post_state["host"]

    try:
        media_id = post_carousel(
            [post_state["hook_image_url"], post_state["scene_image_url"]],
            post_state["caption_final"],
        )
        sr.media_id = media_id
        sr.posted = True
        save_to_posted_log(f"{today_key()}-slot{slot}", {
            "slot": slot,
            "media_id": media_id,
            "host": sr.host,
            "hook_image_url": sr.hook_image_url,
            "scene_image_url": sr.scene_image_url,
            "scene_source": sr.scene_source,
            "posted_at": now_local().isoformat(),
        })
        log(f"  slot {slot} posted: carousel media id {media_id}")
    except Exception as e:
        traceback.print_exc()
        sr.error = f"posting failed: {e}"
        run.posting_error = sr.error

    run.fully_successful = sr.posted
    write_report(run)

    if not run.fully_successful:
        send_failure_email(run)
        return 1

    log(f"done — {run.summary_line}")
    return 0


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    mode = determine_mode()
    run = RunResult(mode=mode, date=today_key(), started_at=now_local().isoformat())

    log(f"jess — {mode} run for {run.date} (local hour: {now_local().hour:02d})")

    # Plan-only mode lets you see what Jess would post before going live.
    if mode == "plan" and env("JESS_PLAN_ONLY", required=False) == "true":
        log("plan-only mode — no image generation or posting")
        run.slots = [SlotResult(slot=1), SlotResult(slot=2)]
        try:
            generate_plan()
        except Exception as e:
            run.planning_error = f"planning failed: {e}"
        write_report(run)
        return 0

    if mode == "plan":
        return run_plan(run)
    if mode == "publish_slot_1":
        return run_publish(run, 1)
    if mode == "publish_slot_2":
        return run_publish(run, 2)

    log(f"skipping — current local hour ({now_local().hour}) is not a scheduled slot. "
        f"Set JESS_MODE env var to force a specific run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
