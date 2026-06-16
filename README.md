# YouTube-

A phone-friendly setup for generating YouTube videos with **Higgsfield** AI,
driven entirely from [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web).

You don't need a computer. Everything runs in the cloud session; this repo makes
the Higgsfield tooling reinstall itself automatically on every session.

## What's in here

| Path | Purpose |
| --- | --- |
| `.claude/hooks/session-start.sh` | Runs at every session start: installs the Higgsfield CLI + Claude Code skills and restores your login. |
| `.claude/settings.json` | Registers the SessionStart hook. |
| `scripts/generate-video.sh` | One-command video generation (defaults to vertical 9:16 Shorts). |
| `scripts/save-auth.sh` | Prints your login so you can save it as a secret and stay logged in. |
| `output/` | Place to keep notes/links to generated results. |

## First-time setup (do this once)

1. **Start a session** from this repo. The session-start hook installs
   `@higgsfield/cli` and the `higgsfield-ai/skills` automatically. Wait for it to
   finish.

2. **Log in.** In the session, ask Claude to run, or run yourself:

   ```bash
   higgsfield auth login
   ```

   It prints a URL (device login). **Open that URL in your phone browser** and
   approve. No API key needed.

3. **Stay logged in across sessions.** The cloud container is wiped between
   sessions, so save your login as a secret:

   ```bash
   scripts/save-auth.sh
   ```

   Copy the single line it prints and, in your Claude Code on the web
   **environment settings**, add a secret named:

   ```
   HIGGSFIELD_CREDENTIALS_JSON
   ```

   Paste the line as its value. From then on, every new session logs you in
   automatically (the credential auto-refreshes). **Never commit this value.**

## Generating a video

The easiest way (great on a phone): just ask Claude in plain English, e.g.

> Generate a vertical video of a slow camera push through a neon Tokyo alley at
> night, cinematic, using Higgsfield.

Claude uses the installed `/higgsfield:generate` skill.

Or run the wrapper directly:

```bash
# Vertical 9:16 Short (default)
scripts/generate-video.sh "slow push through a neon Tokyo alley at night, cinematic"

# Pick a model / aspect ratio / extra params
scripts/generate-video.sh "drone shot over snowy mountains at sunrise" \
  --model kling3_0 --aspect-ratio 16:9 --duration 5
```

The script waits for the job and prints the result URL. Paste that URL into the
`output/` notes or download it on your phone.

### Discovering models and parameters

```bash
higgsfield model list --video        # available video models
higgsfield model get <model>         # accepted params for a model
higgsfield generate cost <model> --prompt "..."   # estimate credits first
```

Defaults can be changed with env vars: `HIGGSFIELD_VIDEO_MODEL`, `HIGGSFIELD_ASPECT`.

## Notes & troubleshooting

- **"Not authenticated"** — run `higgsfield auth login` again and re-open the URL
  on your phone. If it keeps happening across sessions, make sure the
  `HIGGSFIELD_CREDENTIALS_JSON` secret is set (step 3).
- **Install fails / network errors** — the environment's
  [network policy](https://code.claude.com/docs/en/claude-code-on-the-web) must
  allow the npm registry and `higgsfield.ai`. Adjust it in the environment
  settings.
- **Credits** — video generation uses Higgsfield credits tied to your account.
  Check `higgsfield account` and estimate with `higgsfield generate cost ...`.
- The hook only runs in the remote web environment (it no-ops locally).
