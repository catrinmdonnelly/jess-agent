# Jess setup

Plain English, end to end. About 60 minutes the first time. The Meta side (Instagram + Facebook + access token) is the only fiddly bit.

## Before you start

You'll need:
- A GitHub account ([sign up](https://github.com/join))
- An Anthropic account ([sign up](https://console.anthropic.com))
- A Google account (the same one you'll use for Gemini)
- An **Instagram business or creator account**. If yours is personal, [convert it](https://help.instagram.com/502981923235522). It's free.
- A Facebook page connected to your Instagram. Instagram requires this for API posting, even if you never use Facebook.
- A Cloudinary account ([sign up free](https://cloudinary.com/users/register/free))
- About 60 minutes the first time

You will *not* need to write any code.

---

## Step 1 — get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Sign up or sign in. Click your profile in the top right → **API Keys**.
3. **Create Key** → name `jess-agent` → copy the key. **You'll only see it once.**
4. **Plans & Billing** → add £10 to £20 of credit. Jess uses about £3 a month for planning.

---

## Step 2 — get a Gemini API key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Sign in with your Google account.
3. Click **Create API key** → choose a project (or let it create one). Copy the key.
4. Gemini's free tier covers most users (1500 requests/day on the experimental image model). Two carousels a day = ~60 requests/month.

---

## Step 3 — copy this repo into your GitHub

1. Click **Fork** on [the GitHub page](https://github.com/catrinmdonnelly/jess-agent), or **Use this template** for a clean repo with no commit history.

---

## Step 4 — set up Cloudinary for image hosting

Instagram's API needs your images to be at a public URL. Cloudinary handles that.

1. Go to [cloudinary.com](https://cloudinary.com) → sign up free.
2. After signup, you land on the dashboard. Note your **Cloud Name** (top of the dashboard, looks like `dxxxxxxxxx`).
3. Settings (top right gear icon) → **Upload** → scroll to **Upload presets** → **Add upload preset**.
4. Set the preset name to `jess-instagram`. Set **Signing mode** to **Unsigned**. Save.
5. You now have your `CLOUDINARY_CLOUD_NAME` and `CLOUDINARY_UPLOAD_PRESET`. Note both.

---

## Step 5 — convert Instagram to a Business or Creator account, link to Facebook

If you've already done this, skip to step 6.

1. In the Instagram app on your phone: **Profile → Menu (top right) → Settings and privacy → Account type and tools → Switch to professional account**. Choose **Business** or **Creator**, either works.
2. Connect to a **Facebook page**. If you don't have one, [create a free Facebook page](https://www.facebook.com/pages/create/) — it can be brand-new and empty.
3. Once connected, you should be able to find your Instagram from the Facebook page's settings. If you can't, the linking step didn't complete; try again.

---

## Step 6 — get your Meta long-lived page access token

This is the slowest step. It's a series of clicks across two Meta tools.

### 6a. Create a Meta developer app

1. Go to [developers.facebook.com](https://developers.facebook.com). Log in with the Facebook account that owns your page.
2. Click **My Apps** → **Create app**.
3. **Use case**: choose **Other**. Click **Next**.
4. **App type**: **Business**. Click **Next**.
5. App name: `jess-agent`. Contact email: yours. Business account: leave on default. Click **Create app**.
6. You're now in the app dashboard. From the left sidebar: **Add product** → find **Instagram Graph API** → click **Set up**.

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
6. Copy the token that appears. **This is short-lived — only valid for an hour. We'll convert it next.**

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
2. The response shows your Facebook pages. Find the one connected to your Instagram. Copy the `access_token` for that page. **This is your `META_PAGE_ACCESS_TOKEN`. It does not expire as long as the user token doesn't.**

### 6e. Get your Instagram account ID

1. In Graph API Explorer, paste this (with your page access token and page ID from 6d):
   ```
   https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=PAGE_ACCESS_TOKEN
   ```
2. The response includes `instagram_business_account.id`. **That's your `META_INSTAGRAM_ACCOUNT_ID`.**

You now have:
- `META_PAGE_ACCESS_TOKEN` (the page access token from 6d)
- `META_INSTAGRAM_ACCOUNT_ID` (the Instagram business account ID from 6e)

> **Token refresh:** The page access token will keep working as long as you use it. If you don't use it for 60 days, it expires and you'll need to redo 6b, 6c, 6d. In practice Jess uses it daily, so it stays alive.

---

## Step 7 — fill in your config files

In your forked repo:

1. Click into `config/`.
2. Edit `brand-voice.md`. Replace every placeholder. The more specific, the better.
3. Edit `hashtag-bank.md`. Replace the placeholders with your actual hashtag groups.
4. Edit `image-prompt-library.md`. This decides how Jess's daily illustrations look. Be specific about visual style, what to include, what to avoid, with worked examples.
5. `system-prompt.md` is optional. Leave it as is to use the default.

---

## Step 8 — add your secrets and variables to GitHub

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
| `INSTAGRAM_HANDLE` | Your Instagram handle including the `@`, e.g. `@yourbusiness`. Shown on hook cards. |
| `BRAND_BG_COLOR` | Hex colour for hook card background, e.g. `#1a2332`. Defaults to ink navy. |
| `BRAND_TEXT_COLOR` | Hex colour for hook text, e.g. `#f5efe6`. Defaults to warm off-white. |
| `BRAND_ACCENT_COLOR` | Hex colour for the wordmark, e.g. `#eba18a`. Defaults to soft coral. |

---

## Step 9 — turn on Actions

1. In your repo, click **Actions** in the top tabs.
2. Click **I understand my workflows, go ahead and enable them** if prompted.

---

## Step 10 — test before going live

You don't have to wait for the schedule, and you don't have to post a real Instagram on your first run.

1. **Actions** → **Jess daily Instagram** in the left sidebar.
2. Click **Run workflow** dropdown → leave **mode** blank for auto, or pick **plan** to test the planning step alone.
3. **For your first run, set `JESS_PLAN_ONLY=true` as a repo variable.** This makes the plan-mode run write a plan to `plans/` but not generate images or post anything. A safe dry run.
4. Run the workflow. Wait 1-2 minutes. Check `plans/YYYY-MM-DD.md` looks right.
5. When you're happy, **delete the `JESS_PLAN_ONLY` variable** and run the workflow again. This time it'll generate images and prepare them. Still no posting (publishing only happens at the slot hours).
6. Test posting: re-run with mode `publish_slot_1`. This actually posts to Instagram. Make sure you're ready.

If at any point the run goes red, click into it, expand the failed step, and read the error.

---

## Step 11 (optional) — failure email alerts

Same as the other agents. Add four secrets:
- `FAILURE_EMAIL_TO` — your inbox
- `FAILURE_EMAIL_FROM` — a Gmail you can send from
- `FAILURE_EMAIL_SMTP_HOST` — `smtp.gmail.com`
- `FAILURE_EMAIL_SMTP_PASS` — a [16-character app password](https://myaccount.google.com/apppasswords)

---

## Step 12 — let the schedule run

Once the schedule is on, Jess will:
- 08:30 plan and prepare images
- 12:00 post carousel 1
- 18:00 post carousel 2

You'll see the run results in **Actions** and the day's plan in `plans/`.

---

## Troubleshooting

**`Missing required environment variable: ANTHROPIC_API_KEY`** — Secret not set. Step 8.

**`(#10) The application does not have permission to perform this action`** — The Meta token doesn't have the right permissions, or it's the user token instead of the page token. Redo step 6.

**`Invalid OAuth access token`** — Token expired (60 days without use, or you regenerated something). Redo steps 6b-6d.

**`The user must be an administrator, editor, or moderator of the page`** — Wrong Facebook page. Make sure the Instagram is connected to the page whose access token you're using.

**Hook card looks wrong** — Check `BRAND_BG_COLOR` etc. are valid hex codes (with or without `#`). Default fallbacks should kick in if a value is missing.

**Image generation fails** — Gemini sometimes refuses prompts that mention violence, names of real people, or specific brands. Make `image-prompt-library.md` more abstract, or set `OPENAI_API_KEY` for a fallback (uses GPT-Image-1).

**Plan looks generic** — Almost always a config problem. Make `brand-voice.md` more specific. The more detail you give Jess, the sharper she gets.

**The schedule isn't firing** — GitHub Actions pauses cron in repos with no activity for 60 days. Run the workflow manually once, and the schedule resumes.

**Posts are double-posting** — Shouldn't happen, Jess checks `posted-log.json` before posting. If it does, check for two GitHub Actions runs firing at the same hour, or two repos pointing at the same Instagram.

**Caption character limit** — Instagram caption limit is 2,200 characters. Jess's defaults stay well under.

**Cron timing** — GitHub Actions cron isn't 100% precise. Posts can fire 5-15 minutes late at peak times. That's normal. If you need exact timing, run on Cloudflare Cron or Render instead.
