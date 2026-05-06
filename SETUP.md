# Jess setup

Plain English, end to end. About 60 minutes the first time. The Meta side (Instagram + Facebook + access token) is the only fiddly bit, and you only do it once.

## Before you start

You'll need:
- A GitHub account ([sign up](https://github.com/join))
- An Anthropic account ([sign up](https://console.anthropic.com))
- A Google account (the same one you'll use for Gemini)
- An **Instagram business or creator account**. If yours is personal, [convert it](https://help.instagram.com/502981923235522). Free, takes a minute.
- A Facebook page connected to your Instagram. Instagram requires this for API posting, even if you never use Facebook.
- A Cloudinary account ([sign up free](https://cloudinary.com/users/register/free))
- About 60 minutes the first time

You will *not* need to write any code.

---

## Step 1. Get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Sign up or sign in. Click your profile in the top right, then **API Keys**.
3. **Create Key**. Name it `jess-agent`. Copy the key. **You'll only see it once.**
4. **Plans & Billing**. Add £10 to £20 of credit. Jess uses about £3 a month for planning.

---

## Step 2. Get a Gemini API key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Sign in with your Google account.
3. Click **Create API key**. Choose a project, or let it create one. Copy the key.
4. Gemini's free tier covers most users (1500 requests/day on the experimental image model). Two carousels a day is roughly 60 requests a month.

---

## Step 3. Copy this repo into your GitHub

1. Click **Fork** on [the GitHub page](https://github.com/catrinmdonnelly/jess-agent), or **Use this template** for a clean repo with no commit history.

---

## Step 4. Set up Cloudinary for image hosting

Instagram's API needs your images to be at a public URL. Cloudinary handles that.

1. Go to [cloudinary.com](https://cloudinary.com). Sign up free.
2. After signup, you land on the dashboard. Note your **Cloud Name** (top of the dashboard, looks like `dxxxxxxxxx`).
3. Settings (top right gear icon) → **Upload** → scroll to **Upload presets** → **Add upload preset**.
4. Set the preset name to `jess-instagram`. Set **Signing mode** to **Unsigned**. Save.
5. You now have your `CLOUDINARY_CLOUD_NAME` and `CLOUDINARY_UPLOAD_PRESET`. Note both.

---

## Step 5. Convert Instagram to a Business or Creator account, link to Facebook

If you've already done this, skip to step 6.

1. In the Instagram app on your phone: **Profile → Menu (top right) → Settings and privacy → Account type and tools → Switch to professional account**. Choose **Business** or **Creator**, either works.
2. Connect to a **Facebook page**. If you don't have one, [create a free Facebook page](https://www.facebook.com/pages/create/). It can be brand-new and empty.
3. Once connected, you should be able to find your Instagram from the Facebook page's settings. If you can't, the linking step didn't complete. Try again.

---

## Step 6. Get your Meta long-lived page access token

This is the slowest step. It's a series of clicks across two Meta tools. If you get stuck, copy this whole step into Claude or ChatGPT and ask it to walk you through interactively.

### 6a. Create a Meta developer app

1. Go to [developers.facebook.com](https://developers.facebook.com). Log in with the Facebook account that owns your page.
2. Click **My Apps → Create app**.
3. **Use case**: choose **Other**. Click **Next**.
4. **App type**: **Business**. Click **Next**.
5. App name: `jess-agent`. Contact email: yours. Business account: leave on default. Click **Create app**.
6. You're now in the app dashboard. From the left sidebar: **Add product** → find **Instagram Graph API** → **Set up**.

### 6b. Get a short-lived user access token

1. From your app dashboard: **Tools** (top right) → **Graph API Explorer**.
2. **Application** dropdown (top right): pick `jess-agent`.
3. **User or Page** dropdown: select **User Token**.
4. Click **Add a permission**. Tick all of these:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`
5. Click **Generate Access Token**. A popup asks for permission. Allow.
6. Copy the token that appears. **This is short-lived, only valid for an hour. We'll convert it next.**

### 6c. Exchange for a long-lived user token

1. Still in Graph API Explorer, paste this into the URL field at the top (replace `YOUR_APP_ID`, `YOUR_APP_SECRET`, `SHORT_LIVED_TOKEN`):
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN
   ```
2. App ID and App Secret: in your app dashboard, **Settings → Basic**. App Secret needs you to click **Show** and confirm with your password.
3. Send the request. The response will have a long token. Copy it. **This one lasts ~60 days.**

### 6d. Get your page access token

1. In Graph API Explorer, paste this URL (with the long-lived **user** token from 6c):
   ```
   https://graph.facebook.com/v21.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN
   ```
2. The response shows your Facebook pages. Find the one connected to your Instagram. Copy the `access_token` for that page. **This is your `META_PAGE_ACCESS_TOKEN`. It does not expire as long as you keep using it.**

### 6e. Get your Instagram account ID

1. In Graph API Explorer, paste this (with your page access token and page ID from 6d):
   ```
   https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=PAGE_ACCESS_TOKEN
   ```
2. The response includes `instagram_business_account.id`. **That's your `META_INSTAGRAM_ACCOUNT_ID`.**

You now have:
- `META_PAGE_ACCESS_TOKEN` (the page access token from 6d)
- `META_INSTAGRAM_ACCOUNT_ID` (the Instagram business account ID from 6e)

> **Token refresh:** The page access token will keep working as long as you use it. If you don't use it for 60 days, it expires and you need to redo 6b, 6c, 6d. Jess uses it daily, so it stays alive.

---

## Step 7. Fill in your config files. *This is what makes Jess sound like you.*

The Meta and Cloudinary steps are the technical bits. This step is the bit that decides whether the daily posts feel on-brand or generic.

In your forked repo, click into `config/`:

### `brand-voice.md` (most important)

How your business sounds. What words you use. What you avoid. The audience.

Be specific. "Friendly, conversational" is too vague. "We use full sentences, never exclamation marks, we say 'have a look' instead of 'check out', our audience is plant people aged 30-50 who hate Etsy clutter" is useful.

### `hashtag-bank.md`

The hashtags Jess can pick from. Group them however you like (always-on, audience, topic, location). Avoid mega-tags (#love, #instagood). They don't reach buyers.

### `image-prompt-library.md`

This decides how the daily illustrations actually look. Watercolour? Photo-real? Hand-drawn line? Bright editorial? Be specific:

> "Watercolour illustrations. Lived-in, never flat-lay. Human presence welcome. Soft edges, muted palette."

Plus two or three example briefs that have worked, so Jess can calibrate.

### `system-prompt.md` (optional)

Leave blank to use Jess's default voice. Edit it if you want her to think differently.

---

## Step 8. Add your secrets and variables to GitHub

In your repo: **Settings → Secrets and variables → Actions**.

### Secrets

Click **New repository secret** for each:

| Name | Value |
|------|-------|
| `ANTHROPIC_API_KEY` | From step 1 |
| `GEMINI_API_KEY` | From step 2 |
| `CLOUDINARY_CLOUD_NAME` | From step 4 |
| `CLOUDINARY_UPLOAD_PRESET` | From step 4 (the preset name `jess-instagram`) |
| `META_INSTAGRAM_ACCOUNT_ID` | From step 6e |
| `META_PAGE_ACCESS_TOKEN` | From step 6d |

### Variables

Click the **Variables** tab. Then **New repository variable** for each:

| Name | Value |
|------|-------|
| `BUSINESS_NAME` | Your business name. Used as the wordmark on hook cards. |
| `INSTAGRAM_HANDLE` | Your Instagram handle including the `@`, e.g. `@yourbusiness`. |
| `BRAND_BG_COLOR` | Hex colour for hook card background, e.g. `#1a2332`. |
| `BRAND_TEXT_COLOR` | Hex colour for hook text, e.g. `#f5efe6`. |
| `BRAND_ACCENT_COLOR` | Hex colour for the wordmark, e.g. `#eba18a`. |

---

## Step 9. Turn on Actions

1. In your repo, click **Actions** in the top tabs.
2. Click **I understand my workflows, go ahead and enable them** if prompted.

---

## Step 10. Test before going live

You don't have to wait for the schedule. And you don't have to post a real Instagram on your first run.

1. **Settings → Secrets and variables → Actions → Variables tab**. Click **New repository variable**. Name: `JESS_PLAN_ONLY`. Value: `true`.
2. **Actions** → **Jess daily Instagram** → **Run workflow** → leave mode blank → **Run workflow**.
3. Wait one to two minutes. Refresh.
4. The run should turn green. Check `plans/YYYY-MM-DD.md` looks right.
5. When you're happy, **delete the `JESS_PLAN_ONLY` variable** and run the workflow again. This time Jess will generate images and prepare them, but still won't post (publishing only happens at the slot hours).
6. To test posting: re-run with mode `publish_slot_1` from the dropdown. **This actually posts to Instagram. Make sure you're ready.**

If at any point the run goes red, click into it, expand the failed step, and read the error.

---

## Step 11 (optional). Failure email alerts

Add four secrets:
- `FAILURE_EMAIL_TO`, your inbox
- `FAILURE_EMAIL_FROM`, a Gmail you can send from
- `FAILURE_EMAIL_SMTP_HOST`, `smtp.gmail.com`
- `FAILURE_EMAIL_SMTP_PASS`, a [16-character app password](https://myaccount.google.com/apppasswords)

---

## Step 12. Let the schedule run

Once the schedule is on, Jess will:
- 08:30 plan and prepare images
- 12:00 post carousel 1
- 18:00 post carousel 2

You'll see the run results in **Actions** and the day's plan in `plans/`.

---

## Troubleshooting

**`Missing required environment variable: ANTHROPIC_API_KEY`**

Secret not set. Go back to step 8.

**`(#10) The application does not have permission to perform this action`**

The Meta token doesn't have the right permissions, or it's the user token instead of the page token. Redo step 6.

**`Invalid OAuth access token`**

Token expired (60 days without use, or you regenerated something). Redo steps 6b to 6d.

**`The user must be an administrator, editor, or moderator of the page`**

Wrong Facebook page. Make sure the Instagram is connected to the page whose access token you're using.

**Hook card looks wrong**

Check `BRAND_BG_COLOR` etc. are valid hex codes (with or without `#`). Default fallbacks should kick in if a value is missing.

**Image generation fails**

Gemini sometimes refuses prompts that mention violence, names of real people, or specific brands. Make `image-prompt-library.md` more abstract. The hook card will still post on its own if the scene fails (you'll get the hook card on both slides instead of a true carousel).

**Plan looks generic**

Almost always a config problem. Make `brand-voice.md` more specific. The more detail you give Jess, the sharper she gets.

**The schedule isn't firing**

GitHub Actions pauses cron in repos with no activity for 60 days. Run the workflow manually once and the schedule resumes.

**Posts double-post**

Shouldn't happen. Jess checks `posted-log.json` before posting. If it does, check for two GitHub Actions runs firing at the same hour, or two repos pointing at the same Instagram.

**Cron timing**

GitHub Actions cron isn't 100% precise. Posts can fire 5-15 minutes late at peak times. That's normal.
