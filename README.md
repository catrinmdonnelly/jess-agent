# Jess

A daily Instagram agent for small businesses.

Most small businesses know they should be posting more. They don't, because every post is a daily decision and the friction wins. The brand owner is busy making the thing or running the business, not writing captions. So they post twice a month and feel guilty about it.

Jess removes the decision. Every morning at 08:30, she plans the day's two posts. Generates the images. By midday and evening, the carousels are live on Instagram. You don't see her work unless something breaks. You wake up to "we posted today, here's what went out."

> **Status:** Free to use. Take the code, point it at your business. MIT licensed.

## What Jess actually does for a business

Take a small ceramic plant pot brand. £40k/month, two people, no marketing team. The owner is in the workshop making pots, not writing Instagram captions. She tried hiring a freelancer last year, £400/month, posted twice a week, content felt off-brand, cancelled after three months. Since then: maybe three posts a month when she remembers.

With Jess running, here's what a typical day looks like:

> **08:30** Jess reads the brand voice file ("we sell handmade ceramic plant pots, our wedge is irregular hand-shaped pieces big chains can't sell, audience is plant people aged 30-50") and the image style ("watercolour illustrations, lived-in not flat-lay, soft palette, human presence welcome").
>
> She picks today's two moments: the day someone realises the plant they've been killing actually wants neglect, and the moment a pot you bought a year ago becomes the one with a chip you secretly love most. Writes hooks for each. Generates the watercolour scenes via Gemini. Renders the hook cards in your brand colours and font. Uploads everything to Cloudinary. Saves state.
>
> **12:00** Posts the first carousel. Hook card slide 1, watercolour slide 2, caption with the teaser, five hashtags from your bank.
>
> **18:00** Posts the second carousel.

That's the value. Not the brilliance of any single post. **Consistent presence on a channel where you'd otherwise post twice a month.** Two carousels a day, 700 a year, while you do everything else.

## Who Jess helps

- A small business with an Instagram **business or creator account** (personal accounts won't work, the API doesn't allow it)
- Owners who want to post daily but don't because there's never time
- Owners who'd otherwise pay £400+/month for a social media manager
- Anyone who's tried "post 5x a week" and quit by week 3

## Who Jess doesn't help

- Personal Instagram accounts (you need to convert to Business or Creator first, free)
- Brands that need photographs of real products (Jess illustrates, doesn't photograph your stuff)
- Owners who can't write a sharp `brand-voice.md`. Garbage in, garbage out.
- Anyone expecting viral results. Jess gets you consistent. Virality is a different game.

## What success looks like after a year

Not viral posts. **Twelve months of consistent daily posting without burning out.** A library of 700+ posts that compound. Followers up because the algorithm rewards consistency. The occasional post that breaks out because the hook landed. You stopped feeling guilty about Instagram.

## What you get

Every day, automatically:
- **Two Instagram carousels** posted to your account at 12:00 and 18:00 local time
- **A daily plan** at `plans/YYYY-MM-DD.md` so you can see what went out
- **The images** at `images/YYYY-MM-DD-slot1-*.png` and `slot2-*.png`, in case you want to repurpose them
- **A posted log** at `logs/posted-log.json`, every carousel's media ID

## What it costs

About £8 to £12 a month at typical use:
- **Anthropic API** for planning: ~£3
- **Gemini API** for image generation: free tier covers most users (1500 requests/day on the experimental image model)
- **Cloudinary**: free tier (25 GB) covers years of carousels
- **GitHub Actions**: free at this volume

## What you'll need before you start

This is the most involved of the three agents to set up because Instagram requires a Meta developer app and a long-lived access token. Plan an hour the first time. After that it just runs.

1. A GitHub account
2. An [Anthropic API key](https://console.anthropic.com)
3. A [Google AI Studio API key](https://aistudio.google.com/apikey) for Gemini
4. An Instagram **business or creator account** connected to a Facebook page (the Meta API requires both, even if you never use Facebook)
5. A [Meta developer account](https://developers.facebook.com), an app, and a long-lived page access token
6. A free [Cloudinary account](https://cloudinary.com)
7. About 60 minutes for first-time setup

If the Meta token step looks daunting, [SETUP.md](SETUP.md) walks through every click. You can also paste it into Claude or ChatGPT and ask it to walk you through, step by step.

## How it works

The pipeline is four steps. There are no fallbacks, no alternative paths.

1. **Claude** writes the day's two posts (hook, caption, image brief, hashtags)
2. **Gemini** generates the slide-2 illustration for each post
3. **PIL** renders the slide-1 hook card with your brand colours and font
4. **Cloudinary** hosts the images, **Instagram Graph API** posts the carousel

The whole thing runs on GitHub Actions. Three runs a day: plan in the morning, two publish slots later. If anything breaks, she emails you.

## Set up

See [SETUP.md](SETUP.md). The Meta token step is the only fiddly bit.

## Running it locally

```sh
cp .env.example .env
# fill in every required key in .env

pip install -r requirements.txt

# Plan only, without posting (great for first runs):
JESS_MODE=plan JESS_PLAN_ONLY=true python jess.py

# Plan and prepare images:
JESS_MODE=plan python jess.py

# Post slot 1 (after a successful plan run):
JESS_MODE=publish_slot_1 python jess.py
```

## Customising

- **Brand colours.** Set `BRAND_BG_COLOR`, `BRAND_TEXT_COLOR`, `BRAND_ACCENT_COLOR` to any hex codes. Hook cards use them.
- **Display font.** Override `FONT_REGULAR_URL` and `FONT_ITALIC_URL` with any variable-weight TTF on a public URL. Defaults to Playfair Display.
- **Wordmark and handle.** Set `BUSINESS_NAME` and `INSTAGRAM_HANDLE`. They appear at the top and bottom of every hook card.
- **Voice and approach.** Edit `config/system-prompt.md`.
- **Image style.** Edit `config/image-prompt-library.md`. This decides how every illustration looks: watercolour, photo-real, line illustration, whatever.
- **Schedule.** Defaults are 08:30 / 12:00 / 18:00 UK. Change `JESS_PLAN_HOUR`, `JESS_SLOT1_HOUR`, `JESS_SLOT2_HOUR` and the cron lines in the workflow.
- **Plan-only mode.** Set `JESS_PLAN_ONLY=true` to see what Jess would post without going live. Useful for a few days before flipping to real posting.

## The bigger picture

Jess can run alongside two siblings if you want a fuller setup:

| Agent | Role | Cadence |
|-------|------|---------|
| **[Cleo](https://github.com/catrinmdonnelly/cleo-agent)** | Weekly growth strategy. Reads what's happening, decides the focus. | Mondays |
| **[Alex](https://github.com/catrinmdonnelly/alex-agent)** | SEO. Pulls Search Console, finds rising queries and ranking opportunities. | Wednesdays |
| **Jess** | Social content. Plans and posts daily Instagram carousels. | Daily |

Each one runs on its own. You don't need to run all three.

## Help

Issues and pull requests welcome. The Meta token step is where most people get stuck. Open an issue with which step is failing and the error message and I'll help.

## Licence

MIT. See [LICENSE](LICENSE).
