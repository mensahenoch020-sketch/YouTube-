# YouTube-

Make **faceless YouTube videos** (story/narration) entirely from your phone, using
[Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).
No computer, no GPU, and — for the free maker — **no API keys and no credits**.

There are two ways to make videos here:

| | **Free maker** (recommended) | **Higgsfield** (optional, premium) |
|---|---|---|
| Cost | **$0**, unlimited | Paid credits |
| API key | **None** | None (web login) |
| Best for | Narration/story Shorts & long-form | Short AI-generated cinematic clips |
| How | voiceover + real images + captions | true AI text-to-video |

---

# 🆓 Free faceless-video maker (no credits, no keys)

It turns a written story into a finished video with:
- **AI voiceover** — free neural voice (edge-tts), no key.
- **Real visuals** — freely-licensed images (Openverse/Wikimedia, **no key**), animated
  with a slow pan/zoom (Ken Burns) so it feels like video.
- **Captions locked to the voice** — the voiceover is transcribed on-device (Whisper)
  so words appear exactly when spoken.
- Everything stitched with ffmpeg. Output is ready to upload.

### Make a video
1. Put your story in a text file under `stories/` (or just tell Claude the story).
2. Ask Claude, or run:

```bash
# Vertical 9:16 Short (default)
scripts/make-short.sh stories/sample.txt

# Long-form 16:9
python3 scripts/make_video.py --script stories/sample.txt --format long

# Pick the image theme + a different voice
python3 scripts/make_video.py --script stories/sample.txt \
    --keywords "lighthouse,storm,ocean" --voice en-US-AriaNeural
```

The finished `.mp4` lands in `output/` (plus an `.srt` caption file you can upload to
YouTube). On a phone, just say *"make a short from stories/sample.txt"* and Claude runs it
and sends you the video.

### Options
- `--format shorts|long` — 9:16 (default) or 16:9.
- `--keywords "a,b,c"` — what the background images show. If omitted, they're picked from
  your story automatically.
- `--voice` — any [edge-tts voice](https://github.com/rany2/edge-tts) (e.g.
  `en-US-GuyNeural`, `en-US-AriaNeural`, `en-GB-RyanNeural`).
- `--music path.mp3` — optional background music (drop files in `assets/music/`), auto-ducked
  under the voice.

### Want real stock *video* clips? (still free, optional)
The maker uses keyless images by default. If you want moving stock footage, get a **free**
[Pexels API key](https://www.pexels.com/api/) (free signup, no card) and add it as an
environment secret named `PEXELS_API_KEY`. The maker will then prefer Pexels video clips.

---

# 🎬 Higgsfield (optional premium path)

For true AI-generated cinematic clips. Uses **no API key** (web login) but **costs credits**.

1. **Log in once:** ask Claude to run `higgsfield auth login`, open the printed link on your
   phone, sign in, approve. *(Claude never sees your password.)*
2. **Stay logged in:** run `scripts/save-auth.sh`, copy the line, and add it as an environment
   secret named `HIGGSFIELD_CREDENTIALS_JSON`. (It's a token, **not** your password — never
   commit it.)
3. **Generate:** *"Make a vertical 9:16 video of … using Higgsfield"*, or
   `scripts/generate-video.sh "your prompt"`. Check credits with `higgsfield account status`.

🔒 Claude will **never** ask for your Higgsfield password — you log in yourself via the link.

---

## What's in this repo

| Path | Purpose |
| --- | --- |
| `scripts/make_video.py` | The free maker: voiceover + images + captions → mp4. |
| `scripts/make-short.sh` | One-command vertical Short. |
| `stories/` | Put your narration scripts here (`stories/sample.txt` included). |
| `assets/music/` | Optional background music. |
| `output/` | Finished videos + caption files. |
| `.claude/hooks/session-start.sh` | Installs all deps every session (ephemeral container). |
| `scripts/generate-video.sh`, `scripts/save-auth.sh` | Higgsfield helpers (optional). |

## Troubleshooting
- **Setup/network errors** — the environment's
  [network policy](https://code.claude.com/docs/en/claude-code-on-the-web) must allow the npm
  + PyPI registries and the media sites; adjust it in environment settings.
- **Captions slightly off** — they're aligned with Whisper; set a bigger model with
  `WHISPER_MODEL=small` for more accuracy (slower).
- **Higgsfield "not authenticated" / out of credits** — re-run `higgsfield auth login`; check
  `higgsfield account status`.
