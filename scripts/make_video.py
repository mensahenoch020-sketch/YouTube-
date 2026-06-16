#!/usr/bin/env python3
"""
Free faceless-YouTube video maker (story/narration).

Turns a text script into a finished MP4 with:
  - free neural voiceover (edge-tts, no API key, no cost)
  - auto burned-in captions (synced from the TTS word timings)
  - a background: free Pexels stock clips if PEXELS_API_KEY is set,
    otherwise a clean animated gradient (zero setup, still looks good)
  - everything stitched with ffmpeg

No GPU, no paid credits. Runs on CPU in the cloud session.

Examples:
  scripts/make_video.py --script stories/sample.txt --format shorts
  scripts/make_video.py --text "Once upon a time..." --format long \
      --keywords "forest,fog,morning" --out output/tale.mp4
"""
import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Target geometry per format.
FORMATS = {
    "shorts": (1080, 1920),   # vertical 9:16
    "long":   (1920, 1080),   # horizontal 16:9
}
DEFAULT_VOICE = "en-US-GuyNeural"


def ffmpeg_exe() -> str:
    """Prefer system ffmpeg; fall back to the pip imageio-ffmpeg static binary."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install it: pip install imageio-ffmpeg")


FFMPEG = ffmpeg_exe()


def log(msg: str) -> None:
    print(f"[make_video] {msg}", flush=True)


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kw)


def media_duration(path: str) -> float:
    """Read a media file's duration by parsing ffmpeg stderr (no ffprobe needed)."""
    out = run([FFMPEG, "-hide_banner", "-i", path],
              stderr=subprocess.PIPE, stdout=subprocess.DEVNULL).stderr.decode("utf-8", "ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        return 0.0
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s)


# ---------------------------------------------------------------------------
# Step A + B: voiceover + caption timings (edge-tts, free, no key)
# ---------------------------------------------------------------------------
def _system_ssl_context():
    """SSL context that trusts this environment's proxy CA (system bundle).

    edge-tts pins its context to certifi, which omits the proxy CA used here, so
    we build one from the system bundle (SSL_CERT_FILE) and patch it in.
    """
    import ssl
    ctx = ssl.create_default_context()  # honors SSL_CERT_FILE / default paths
    bundle = os.environ.get("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
    if Path(bundle).exists():
        try:
            ctx.load_verify_locations(cafile=bundle)
        except Exception:
            pass
    return ctx


async def _tts(text: str, voice: str, mp3_path: str):
    """Stream TTS audio to mp3. Returns (audio_bytes, word_timings).

    word_timings is a list of (start_s, end_s, word) when the service provides
    WordBoundary metadata; it may be empty (e.g. proxy drops metadata frames),
    in which case captions are timed evenly against the audio duration.
    """
    import edge_tts
    import edge_tts.communicate as _ec
    _ec._SSL_CTX = _system_ssl_context()  # trust the proxy CA
    comm = edge_tts.Communicate(text, voice)
    words, nbytes = [], 0
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"]); nbytes += len(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7           # 100ns ticks -> seconds
                end = start + chunk["duration"] / 1e7
                words.append((start, end, chunk["text"]))
    return nbytes, words


def even_word_timings(text: str, duration: float):
    """Distribute words evenly across `duration`, weighted by word length."""
    toks = re.findall(r"\S+", text)
    if not toks:
        return []
    weights = [len(t) + 1 for t in toks]
    total = sum(weights)
    timings, t = [], 0.0
    for tok, w in zip(toks, weights):
        dt = duration * w / total
        timings.append((t, t + dt, tok))
        t += dt
    return timings


def whisper_word_timings(mp3_path: str):
    """Transcribe the voiceover locally (faster-whisper, no key) for exact word
    timings so captions are locked to the voice. Returns [] if unavailable."""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return []
    model_size = os.environ.get("WHISPER_MODEL", "base")
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(mp3_path, word_timestamps=True,
                                       vad_filter=True, beam_size=1)
        words = []
        for seg in segments:
            for w in (seg.words or []):
                tok = w.word.strip()
                if tok:
                    words.append((float(w.start), float(w.end), tok))
        return words
    except Exception as e:
        log(f"Whisper timing failed ({e}); using fallback timing.")
        return []


def make_cues(words, max_words=3, max_gap=0.6):
    """Group word timings into short caption cues: list of (start, end, text)."""
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or (w[0] - cur[-1][1]) > max_gap):
            groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return [(g[0][0], g[-1][1], " ".join(c[2] for c in g).strip().upper()) for g in groups]


def srt_time(t: float) -> str:
    t = max(t, 0)
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60); t -= m * 60
    s = int(t); ms = int(round((t - s) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_time(t: float) -> str:
    t = max(t, 0)
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60); t -= m * 60
    s = int(t); cs = int(round((t - s) * 100))
    if cs == 100:
        s += 1; cs = 0
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_srt(cues, path):
    """Plain .srt sidecar for upload/editing."""
    with open(path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n\n")


def write_ass(cues, path, W, H, fmt):
    """Styled .ass for burning in: big bold centered captions sized to the video."""
    fontsize = 80 if fmt == "shorts" else 56
    margin_v = 360 if fmt == "shorts" else 90   # lift above the platform UI / safe area
    outline = 6 if fmt == "shorts" else 4
    side = 90 if fmt == "shorts" else 160       # L/R margins force wrapping, keep off edges
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline},2,2,{side},{side},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for start, end, text in cues:
            text = text.replace("{", "(").replace("}", ")").replace("\n", " ")
            f.write(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}\n")


# ---------------------------------------------------------------------------
# Step C: background visuals
#   Preference: Pexels stock VIDEO (only if PEXELS_API_KEY) -> keyless stock
#   IMAGES (Openverse/Wikimedia) animated with Ken Burns -> animated gradient.
# ---------------------------------------------------------------------------
STOPWORDS = set("""a an the and or but if then of to in on at for with from by as is are was were
be been being this that these those it its his her their your you we they he she i my our not no
so very just into over under out up down off about after before once last every still yet who
whom which what when where why how all any some more most much many one two three said say says""".split())


def keywords_from_text(text: str, n=3):
    """Pick a few salient *visual* search terms from the script (used when
    --keywords absent). Skips proper nouns (character/place names) so the images
    match the scene, not a person's name."""
    # words that ever appear lowercased are common nouns; ones only ever seen
    # capitalized are treated as proper nouns and skipped.
    lower_seen = set(re.findall(r"\b[a-z]{4,}\b", text))
    freq = {}
    for w in re.findall(r"[A-Za-z]{4,}", text):
        lw = w.lower()
        if lw in STOPWORDS or lw not in lower_seen:
            continue
        freq[lw] = freq.get(lw, 0) + 1
    ranked = sorted(freq, key=lambda w: (-freq[w], w))
    return ", ".join(ranked[:n]) if ranked else "cinematic atmospheric landscape"


def _download(url, dst, timeout=60):
    import requests
    try:
        with requests.get(url, stream=True, timeout=timeout,
                           headers={"User-Agent": "faceless-yt/1.0"}) as r:
            r.raise_for_status()
            with open(dst, "wb") as f:
                for blk in r.iter_content(1 << 16):
                    f.write(blk)
        return dst.stat().st_size > 2000
    except Exception:
        return False


def fetch_images(keywords, n, tmp: Path):
    """Download up to n freely-licensed images. NO API KEY (Openverse, Wikimedia)."""
    import requests
    query = (keywords or "cinematic landscape").split(",")[0].strip() or "cinematic"
    urls = []
    # Openverse (keyless)
    try:
        r = requests.get("https://api.openverse.org/v1/images/",
                         params={"q": query, "page_size": n * 3, "license_type": "commercial",
                                 "mature": "false"},
                         headers={"User-Agent": "faceless-yt/1.0"}, timeout=25)
        r.raise_for_status()
        urls += [x["url"] for x in r.json().get("results", []) if x.get("url")]
    except Exception as e:
        log(f"Openverse search failed ({e}).")
    # Wikimedia Commons (keyless) as a top-up / fallback
    if len(urls) < n:
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php",
                             params={"action": "query", "generator": "search",
                                     "gsrsearch": query, "gsrlimit": n * 2, "gsrnamespace": 6,
                                     "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1600,
                                     "format": "json"},
                             headers={"User-Agent": "faceless-yt/1.0 (youtube maker)"}, timeout=25)
            pages = r.json().get("query", {}).get("pages", {})
            for p in pages.values():
                ii = (p.get("imageinfo") or [{}])[0]
                u = ii.get("thumburl") or ii.get("url")
                if u:
                    urls.append(u)
        except Exception as e:
            log(f"Wikimedia search failed ({e}).")

    paths = []
    for i, u in enumerate(urls):
        if len(paths) >= n:
            break
        ext = ".jpg" if not u.lower().endswith(".png") else ".png"
        dst = tmp / f"img_{i}{ext}"
        if _download(u, dst):
            paths.append(dst)
    return paths


def ken_burns_background(images, fmt, dur, tmp: Path):
    """Build a slow pan/zoom slideshow from still images -> background video."""
    W, H = FORMATS[fmt]
    n = len(images)
    seg = max(2.5, dur / n)
    clips = []
    for i, img in enumerate(images):
        frames = int(round(seg * 30))
        # Drive the zoom by output-frame number `on` with d=1 (one output frame
        # per input frame) — this is fast. A larger `d` multiplies frames and is
        # extremely slow. ~+0.10x zoom across the clip.
        rate = 0.10 / max(frames, 1)
        if i % 2 == 0:   # zoom in
            zexpr = f"min(1.0+{rate:.6f}*on,1.30)"
        else:            # zoom out
            zexpr = f"max(1.30-{rate:.6f}*on,1.0)"
        # scale up first so the zoom stays crisp; crop to fill; then pan/zoom.
        vf = (f"scale={int(W*1.5)}:{int(H*1.5)}:force_original_aspect_ratio=increase,"
              f"crop={int(W*1.5)}:{int(H*1.5)},"
              f"zoompan=z='{zexpr}':d=1:fps=30:s={W}x{H}:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
              f"setsar=1,format=yuv420p")
        clip = tmp / f"kb_{i}.mp4"
        cmd = [FFMPEG, "-y", "-loop", "1", "-framerate", "30", "-t", f"{seg:.2f}",
               "-i", str(img), "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", str(clip)]
        if run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            clips.append(clip)
    if not clips:
        return None
    listfile = tmp / "kb.txt"
    reps = max(1, int(dur // (seg * len(clips)) + 1))
    with open(listfile, "w") as f:
        for _ in range(reps):
            for c in clips:
                f.write(f"file '{c}'\n")
    bg = str(tmp / "bg.mp4")
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
           "-t", f"{dur:.2f}", "-an", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", bg]
    if run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return bg
    return None


def fetch_pexels_clips(keywords: str, orientation: str, n: int, tmp: Path):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    import requests
    query = (keywords or "abstract background").split(",")[0].strip() or "abstract"
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={"query": query, "orientation": orientation, "per_page": n, "size": "medium"},
            timeout=30,
        )
        r.raise_for_status()
        vids = r.json().get("videos", [])
    except Exception as e:
        log(f"Pexels fetch failed ({e}); trying keyless images.")
        return []
    paths = []
    for i, v in enumerate(vids[:n]):
        files = sorted(v.get("video_files", []),
                       key=lambda f: (f.get("height") or 0), reverse=True)
        link = next((f["link"] for f in files if (f.get("height") or 0) >= 720), None) \
            or (files[0]["link"] if files else None)
        if not link:
            continue
        dst = tmp / f"clip_{i}.mp4"
        if _download(link, dst):
            paths.append(dst)
    return paths


def make_background(keywords, fmt, dur, tmp: Path) -> str:
    """Return path to a background video of length `dur` at the target geometry."""
    W, H = FORMATS[fmt]
    orientation = "portrait" if fmt == "shorts" else "landscape"
    fill = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"

    # 1) Pexels stock VIDEO (only if the user added a free key)
    clips = fetch_pexels_clips(keywords, orientation, 4, tmp)
    bg = str(tmp / "bg.mp4")
    if clips:
        listfile = tmp / "concat.txt"
        reps = max(1, int(dur // 2) + 1)
        with open(listfile, "w") as f:
            for _ in range(reps):
                for c in clips:
                    f.write(f"file '{c}'\n")
        log(f"Background: {len(clips)} Pexels video clip(s).")
        cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
               "-t", f"{dur:.2f}", "-an",
               "-vf", f"{fill},fps=30", "-c:v", "libx264", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", bg]
        if run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return bg

    # 2) Keyless stock IMAGES, animated with Ken Burns (DEFAULT, no API key)
    log(f"Fetching free images (no key) for: {keywords}")
    images = fetch_images(keywords, 5, tmp)
    if images:
        log(f"Background: Ken Burns slideshow from {len(images)} free image(s).")
        kb = ken_burns_background(images, fmt, dur, tmp)
        if kb:
            return kb
        log("Ken Burns build failed; falling back to gradient.")

    # 3) Animated gradient (last resort, always works offline)
    log("Background: animated gradient (no images available).")
    grad = (f"gradients=s={W}x{H}:c0=0x12263a:c1=0x05070d:c2=0x1b3a5b:"
            f"nb_colors=3:speed=0.012:duration={dur:.2f},format=yuv420p")
    cmd = [FFMPEG, "-y", "-f", "lavfi", "-i", grad, "-t", f"{dur:.2f}",
           "-vf", f"{fill},fps=30", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", bg]
    run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return bg


# ---------------------------------------------------------------------------
# Step D: assemble final video
# ---------------------------------------------------------------------------
def assemble(bg, voice_mp3, ass, fmt, music, out_path):
    W, H = FORMATS[fmt]
    ass_esc = ass.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    vf = f"subtitles=filename={ass_esc}"

    cmd = [FFMPEG, "-y", "-i", bg, "-i", voice_mp3]
    if music and Path(music).exists():
        cmd += ["-i", music]
        # voice full, music ducked low, mixed to voice length
        filt = (f"[0:v]{vf}[v];"
                f"[2:a]volume=0.10[mus];[1:a][mus]amix=inputs=2:duration=first:"
                f"dropout_transition=2[a]")
        maps = ["-map", "[v]", "-map", "[a]"]
    else:
        filt = f"[0:v]{vf}[v]"
        maps = ["-map", "[v]", "-map", "1:a"]
    cmd += ["-filter_complex", filt] + maps + [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path]
    log("Encoding final video ...")
    if run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE).returncode != 0:
        # Re-run surfacing stderr for diagnosis.
        err = run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE).stderr.decode("utf-8", "ignore")
        sys.exit("ffmpeg failed:\n" + "\n".join(err.splitlines()[-15:]))


def main():
    ap = argparse.ArgumentParser(description="Free faceless video maker")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--script", help="path to a .txt narration script")
    g.add_argument("--text", help="narration text directly")
    ap.add_argument("--format", choices=FORMATS, default="shorts")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="edge-tts voice")
    ap.add_argument("--keywords", default="", help="comma-separated b-roll search terms (Pexels)")
    ap.add_argument("--music", default="", help="optional background music mp3")
    ap.add_argument("--out", default="", help="output mp4 path")
    args = ap.parse_args()

    if args.script:
        text = Path(args.script).read_text(encoding="utf-8").strip()
        stem = Path(args.script).stem
    else:
        text = args.text.strip()
        stem = "video"
    if not text:
        sys.exit("Empty narration text.")

    out = args.out or str(REPO / "output" / f"{stem}-{args.format}.mp4")
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    W, H = FORMATS[args.format]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mp3 = str(tmp / "voice.mp3")
        ass = str(tmp / "captions.ass")

        log(f"Generating voiceover ({args.voice}) ...")
        nbytes, words = asyncio.run(_tts(text, args.voice, mp3))
        if nbytes == 0:
            sys.exit("TTS produced no audio (check voice name / network).")
        dur = media_duration(mp3) or (words[-1][1] + 0.5 if words else 1.0)

        # Caption timing, best to worst: Whisper (locked to the voice) ->
        # edge-tts boundaries -> even spacing.
        log("Aligning captions to the voice (Whisper) ...")
        wt = whisper_word_timings(mp3)
        if wt:
            words = wt
            log(f"Whisper aligned {len(words)} words.")
        elif words:
            log("Using edge-tts word boundaries.")
        else:
            log("No word timings available; spacing captions evenly.")
            words = even_word_timings(text, dur)
        cues = make_cues(words)
        log(f"Voiceover {dur:.1f}s; {len(cues)} caption cues.")

        write_ass(cues, ass, W, H, args.format)
        # keep an .srt sidecar next to the output for upload/editing
        srt_side = str(Path(out).with_suffix(".srt"))
        write_srt(cues, srt_side)

        keywords = args.keywords or keywords_from_text(text)
        bg = make_background(keywords, args.format, dur, tmp)
        assemble(bg, mp3, ass, args.format, args.music, out)

    size = Path(out).stat().st_size
    log(f"DONE -> {out} ({size/1e6:.1f} MB, {args.format}, {dur:.1f}s)")
    log(f"Captions sidecar -> {srt_side}")


if __name__ == "__main__":
    main()
