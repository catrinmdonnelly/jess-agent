# Jess

A daily Instagram agent. Jess plans two posts in the morning, generates the images, and publishes them as carousels at midday and evening. All on autopilot.

She runs three times a day on GitHub Actions. By the time you're at your desk, the day's posts are already lined up. By dinner, they've published.

> **Status:** Free to use. Take the code, point it at your business. MIT licensed.

## What you get every day

- **A daily plan** at `plans/YYYY-MM-DD.md`. Two posts, each with: a moment, a hook line, a caption, a story, an image brief, hashtags.
- **Two two-slide carousels** posted to Instagram. Slide 1 is a hook card (one jarring sentence on a brand-colour background, your fonts and colours). Slide 2 is a generated illustration in your visual style.
- **Posted log** at `logs/posted-log.json`. Every carousel that's gone live, with media IDs.

## What it costs

About £8 to £12 a month at typical use:
- Anthropic API for planning: ~£3
- Gemini API for image generation: free tier covers most users; ~£2 if you exceed it
- Cloudinary: free tier (25 GB) covers years of carousel images
- GitHub Actions: free at this volume

## What you'll need before you start

This is the most involved of the three agents to set up. Plan an hour the first time.

1. A GitHub account
2. An [Anthropic API key](https://console.anthropic.com)
3. A [Google AI Studio API key](https://aistudio.google.com/apikey) for Gemini
4. An Instagram **business or creator account** connected to a **Facebook page**. Personal Instagram accounts won't work.
5. A [Meta developer account](https://developers.facebook.com), an app, and a long-lived page access token
6. A [Cloudinary account](https://cloudinary.com) (free)
7. About 60 minutes for first-time setup. The Meta token is the slow part.

## How it works

**08:30** — Jess reads your config (brand voice, hashtags, image style), reads any direction from upstream agents, and asks Claude to plan today's two posts. She generates both hook cards (PIL with your brand colours) and both illustrations (Gemini, OpenAI fallback). Uploads everything to Cloudinary. Saves state.

**12:00** — Reads the morning's state and posts carousel slot 1 to Instagram via the Meta Graph API.

**18:00** — Same for slot 2.

If anything breaks at any point, she emails you and writes a Station inbox JSON.

## Set up

See [SETUP.md](SETUP.md). The Meta side is the most fiddly. The rest is straightforward.

## Running it locally

```sh
cp .env.example .env
# fill in every required key in .env

pip install -r requirements.txt

# To plan only, without posting (great for first runs):
JESS_MODE=plan JESS_PLAN_ONLY=true python jess.py

# To plan and prepare images:
JESS_MODE=plan python jess.py

# To post slot 1 (after a successful plan run):
JESS_MODE=publish_slot_1 python jess.py
```

## Customising

- **Brand colours.** Set `BRAND_BG_COLOR`, `BRAND_TEXT_COLOR`, `BRAND_ACCENT_COLOR` to any hex codes. Hook cards use them.
- **Display font.** Override `FONT_REGULAR_URL` and `FONT_ITALIC_URL` with any variable-weight TTF on a public URL. Defaults to Playfair Display from Google Fonts.
- **Wordmark and handle.** Set `BUSINESS_NAME` and `INSTAGRAM_HANDLE`. They appear at the top and bottom of every hook card.
- **Voice and approach.** Edit `config/system-prompt.md` to give Jess a different personality. Leave it blank to use the default.
- **Image style.** Edit `config/image-prompt-library.md`. This decides how every illustration looks.
- **Schedule.** Defaults are 08:30 / 12:00 / 18:00 UK. Change `JESS_PLAN_HOUR`, `JESS_SLOT1_HOUR`, `JESS_SLOT2_HOUR` and the cron lines in the workflow.
- **Plan-only mode.** Set `JESS_PLAN_ONLY=true` to see what Jess would post without going live. Useful for a few days before flipping to real posting.

## The bigger picture

Jess is one of three agents that work together if you run all of them:

| Agent | Role | Cadence |
|-------|------|---------|
| **[Cleo](https://github.com/catrinmdonnelly/cleo-agent)** | Weekly growth strategy. Reads what's happening, decides the focus. | Mondays |
| **[Alex](https://github.com/catrinmdonnelly/alex-agent)** | SEO. Pulls Search Console, finds rising queries and declining pages. | Wednesdays |
| **Jess** | Social content. Plans and posts daily Instagram carousels. | Daily |

Each one runs on its own. Together, Jess reads Cleo's weekly direction and Alex's trend findings before planning each day, so the daily content connects to the week's strategy and the search angles that matter.

## Help

Issues and pull requests welcome. The Meta token step is where most people get stuck — open an issue with which step is failing and what you've tried.

## Licence

MIT. See [LICENSE](LICENSE).
