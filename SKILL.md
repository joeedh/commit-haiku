---
name: commit-haiku
description: Turn a git commit into a short dramatic video — read the full diff, write a 5-7-5 haiku capturing the change, then call Google's Veo (via the Gemini API; see SKILL.md for key setup) to generate a dramatized reading with visuals and audio. Use when the user says "haiku my commit", "make a commit haiku", "/commit-haiku", or similar.
---

# Commit Haiku

Distill a git commit into a haiku, then render it as a short cinematic video with a dramatic spoken reading via Google's Veo model (Gemini API).

## Trigger

Phrases like: "haiku my last commit", "make a commit haiku", "/commit-haiku", "/commit-haiku HEAD~2", "haiku commit abc1234".

## Inputs

- Optional commit ref (SHA, branch, `HEAD~N`, tag). Default: `HEAD`.
- Optional model: if the user asks for "higher quality", pass `--model veo-3.0-generate-001`. Otherwise the helper defaults to `veo-3.0-fast-generate-001`.
- API key: resolved by the helper in this order — `--api-key` flag, `--api-key-file` flag, `$GEMINI_API_KEY`, `$GOOGLE_API_KEY`, `~/.claude/skills/commit-haiku/.api-key`, then legacy `./gemini.txt`. If none are set, the helper exits with a clear setup message — relay it verbatim.

## API key setup (one-time)

If the helper reports a missing key, pick one of these and re-run:

```powershell
# Recommended: persisted user env var
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "<KEY>", "User")

# OR a user-level file (no shell restart needed)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\commit-haiku" | Out-Null
"<KEY>" | Out-File -Encoding ascii -NoNewline "$env:USERPROFILE\.claude\skills\commit-haiku\.api-key"
```

`./gemini.txt` in the project root still works for back-compat but is deprecated — it has to be re-created in every repo and is easy to accidentally commit.

## Steps

### 1. Resolve the commit

Run `git rev-parse --verify <ref>` (default `HEAD`). If it fails, ask the user for a valid ref and stop.

Also capture the short SHA via `git rev-parse --short <ref>` — used in the output filename.

### 2. Gather diff context

Run these in parallel:
- `git show --stat --no-color <ref>` — message + file summary.
- `git show --no-color <ref>` — full patch.

If the full diff is larger than ~50 KB, take only the first 50 KB and note the truncation in your haiku-writing reasoning. Weight the commit message and `--stat` summary more heavily in that case.

### 3. Write the haiku

Compose a 5-7-5 haiku that captures the *essence* of the change. Rules:

- **One concrete image.** Not abstract jargon like "refactor utilities". Find the thing being moved, fixed, born, or killed and put it on the page.
- **Why over what** when the commit message reveals motivation. A bug fix has a victim and a culprit — name them.
- **Counted syllables: 5 / 7 / 5.** Count them.
- **No code identifiers** in the haiku itself unless they're truly central — a haiku that says "WebGPU" is fine; one that says "renderPassDescriptor" is not.

Show the haiku to the user before kicking off the video. Format:

```
Line one of five
Line two with seven beats here
Final five beats
```

### 4. Compose the Veo prompt

Build a single prompt string under ~500 words with these elements:

- **Scene**: one dramatic visual — subject, setting, lighting, camera. Mood matches the haiku. Example openers: "A weathered lighthouse keeper at dawn...", "Slow dolly across a neon-lit server room at 3am...", "Lone figure in a snowfield, backlit...".
- **Style**: "cinematic, 24fps, shallow depth of field" unless the haiku suggests otherwise (e.g. a haiku about chaos could be "handheld, kinetic").
- **Audio / dialogue**: include the haiku as **spoken dialogue, in quotes**. Veo 3 reads quoted text verbatim. Example:
  > A weathered narrator with a gravelly voice speaks slowly, with reverence: "Line one of five. Line two with seven beats here. Final five beats."
- **Audio ambience** (optional): one line about background sound matching the scene ("low wind, distant gulls" / "soft hum of cooling fans").

Print the full prompt to the user before calling the helper.

### 5. Run the helper

Call the helper script in the background — generation takes 1–6 minutes.

```powershell
python C:\Users\joeed\.claude\skills\commit-haiku\generate_video.py `
  --prompt "<the composed prompt>" `
  --output ".\commit-haiku-<shortsha>.mp4"
```

- Add `--model veo-3.0-generate-001` only if the user asked for higher quality.
- Use Bash with `run_in_background: true` (or PowerShell `-AsJob`) so you can keep talking while it renders. The script prints poll progress lines like `[t=30s] still generating...` to stdout.
- The script resolves the API key from `$GEMINI_API_KEY` / `$GOOGLE_API_KEY` / `~/.claude/skills/commit-haiku/.api-key` / legacy `./gemini.txt`. If none are set, it exits with a clear setup message — relay it verbatim.

### 6. Report

When the script finishes, show the user:

1. The final MP4 path (absolute).
2. The haiku, again.
3. The full Veo prompt that was used — so they can tweak and re-run.

If the script exited non-zero, surface its stderr verbatim. Common cases:
- **Safety / policy block** from Veo → tell the user what tripped (the error text usually says), suggest a rephrased prompt.
- **API key missing** → relay the script's error verbatim; it lists every location checked and the two fix commands.
- **API key invalid** (HTTP 400/403) → tell the user the resolved source rejected the key, and to update whichever one is highest-precedence (env var > user-level file > legacy `./gemini.txt`).
- **Timeout** → re-run; Veo occasionally takes longer than the 15-minute default.

## What NOT to do

- Don't invoke Veo without showing the haiku and prompt first — the user might want to iterate on text before spending the API call.
- Don't hardcode the API key into the prompt or any file. The helper reads `./gemini.txt` at run time.
- Don't try to summarize the diff for the user — they wrote it. Just produce the haiku.
- Don't pad the haiku with filler syllables to hit 5-7-5. Rewrite the line.
