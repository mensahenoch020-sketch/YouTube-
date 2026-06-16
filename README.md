# YouTube-

Make YouTube videos with **Higgsfield** AI — entirely from your phone, using
[Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).
No computer needed. This repo sets itself up automatically every session.

---

## ✅ What you need / 🚫 What you DON'T

**You DON'T need:**
- ❌ An **API key** — Higgsfield doesn't use one. You just log in.
- ❌ To **install anything on your phone** — your phone is only the screen. The
  software runs in the cloud session.
- ❌ To **share your Higgsfield password** with Claude. Never type it in the chat
  or any file. Claude will never ask for it.

**You DO need:**
- ✅ A **Higgsfield account** with some **credits** (video generation uses credits).
- ✅ To tap a **login link once** on your phone.

---

## 📱 Step-by-step (all on your phone)

### Step 1 — Start a session
Open this repo in Claude Code on the web and start a session. Wait a moment —
the setup runs automatically and installs the Higgsfield tool for you.

### Step 2 — Log in (one time)
Tell Claude:

> Run `higgsfield auth login`

It prints a **link** (and maybe a short code). **Open that link in your phone's
browser**, sign in to your Higgsfield account, and approve. The session then
shows you're logged in. *(This is you logging in on Higgsfield's own website —
Claude never sees your password.)*

### Step 3 — Stay logged in (so you don't repeat Step 2 every time)
Tell Claude:

> Run `scripts/save-auth.sh`

It prints **one line** (a temporary access **token** — not your password). Copy it.
Then in your Claude Code **environment settings**, add a secret named:

```
HIGGSFIELD_CREDENTIALS_JSON
```

and paste that line as the value. Done — future sessions log you in automatically.
*(Never commit this value to the repo.)*

### Step 4 — Make a video 🎬
Just ask Claude in plain English. Examples:

> Make a vertical 9:16 video of a slow camera push through a neon Tokyo alley at
> night, cinematic, using Higgsfield.

> Animate this photo into a 5-second clip using Higgsfield. *(attach/point to an image)*

Claude uses the built-in `/higgsfield:generate` skill. Generation takes a few
minutes; when it's done you get a **link to your video** — tap to watch or
download on your phone.

Prefer a command? You can also run:

```bash
scripts/generate-video.sh "slow push through a neon Tokyo alley at night, cinematic"
```

### Step 5 — Handy extras
```bash
higgsfield account              # check your remaining credits
higgsfield model list --video   # see available video models
```
Default output is **vertical 9:16** (YouTube Shorts). For widescreen add
`--aspect-ratio 16:9` to the script, or just ask Claude for "16:9".

---

## 🔒 Security note
Claude **never needs and will never ask for your Higgsfield password**. You log in
yourself via the link in Step 2. The only thing stored is a temporary access token
(Step 3), which you save as a secret — never share your password with anyone.

---

## What's in this repo (for reference)

| Path | Purpose |
| --- | --- |
| `.claude/hooks/session-start.sh` | Runs each session: installs the Higgsfield CLI + restores your login. |
| `.claude/settings.json` | Registers the SessionStart hook. |
| `.claude/skills/`, `.agents/skills/` | The official Higgsfield skills (`/higgsfield:generate`, etc.). |
| `scripts/generate-video.sh` | One-command video generation (defaults to vertical 9:16). |
| `scripts/save-auth.sh` | Prints your login token to save as a secret (Step 3). |
| `output/` | A place to keep notes/links to generated results. |

## Troubleshooting
- **"Not authenticated"** — redo Step 2 (`higgsfield auth login`). If it keeps
  asking every session, make sure the `HIGGSFIELD_CREDENTIALS_JSON` secret from
  Step 3 is set.
- **Install/network errors** — the environment's
  [network policy](https://code.claude.com/docs/en/claude-code-on-the-web) must
  allow the npm registry and `higgsfield.ai`. Adjust it in environment settings.
- **No video / out of credits** — check `higgsfield account` and top up credits
  in your Higgsfield account.

### Discovering models and parameters
```bash
higgsfield model list --video                     # available video models
higgsfield model get <model>                      # accepted params for a model
higgsfield generate cost <model> --prompt "..."   # estimate credits first
```
Defaults can be changed with env vars: `HIGGSFIELD_VIDEO_MODEL`, `HIGGSFIELD_ASPECT`.
