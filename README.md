# Jess

A daily Instagram agent for small businesses, who removes the decision of what to post and the work of posting it, so the channel actually gets used instead of guilt-tripped about.

Most small businesses know they should be posting more, but every single post is a daily decision and the friction wins, especially when the owner is busy making the thing or running the business rather than writing captions, so they end up posting twice a month and feeling bad about it. Jess removes the decision: every morning at 08:30 she plans the day's two posts and generates the images, by midday and evening the carousels are live on Instagram, and you don't see any of her work unless something breaks. You wake up to "we posted today, here's what went out."

> **Status:** Free to use. Take the code, point it at your business. MIT licensed.

## What Jess actually does for a business

Picture a small ceramic plant pot brand turning over £40,000 a month, with two people running it and no marketing team, because the founder is in the workshop making pots rather than writing Instagram captions. She tried hiring a freelancer last year for £400 a month who posted twice a week with content that felt off-brand, cancelled after three months, and since then has managed maybe three posts a month when she remembers. With Jess running, a typical day looks like this:

> **08:30** Jess reads the brand voice file ("we sell handmade ceramic plant pots, our wedge is irregular hand-shaped pieces big chains can't sell, audience is plant people aged 30 to 50") and the image style ("watercolour illustrations, lived-in not flat-lay, soft palette, human presence welcome"), then picks today's two moments. Today they're the day someone realises the plant they've been killing actually wants neglect, and the moment a pot you bought a year ago becomes the one with a chip you secretly love most. She writes a hook line for each, generates the watercolour scenes through Gemini, renders the hook cards in your brand colours and font, uploads everything to Cloudinary, and saves state for the publish phase later.
>
> **12:00** She posts the first carousel: hook card on slide one, watercolour scene on slide two, caption with the teaser, and five hashtags from your bank.
>
> **18:00** She posts the second carousel.

The value isn't the brilliance of any single post, since none of them are going to go viral on their own. The value is **consistent presence on a channel where you'd otherwise have managed two posts a month**: two carousels a day, seven hundred a year, all while you're doing everything else.

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

Success isn't a viral post or two. It's twelve months of consistent daily posting that nobody had to burn out keeping up with, a library of seven hundred posts that compound on each other, follower numbers that have crept up because the algorithm rewards consistency more than it rewards perfection, the occasional post that breaks out because the hook genuinely landed, and the simple relief of not feeling guilty about Instagram any more.

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
