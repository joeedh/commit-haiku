# commit-haiku

A [Claude Code](https://claude.com/claude-code) skill that turns a git commit into a short dramatic video — reads the entire diff, distills it into a 5-7-5 haiku, then calls Google's Veo (via the Gemini API) to generate a dramatized reading with cinematic visuals and audio.

## Example

For commit `c9c2570` ("WebGPU: wire scene lights into material pipelines"):

```
Dark meshes awake
first light crosses every wire
shadows learn to fall
```

→ 8-second MP4 of a dark industrial hall, overhead conduits filling with traveling amber light, sculptures lit one by one, a narrator reading the haiku.

[▶ examples/commit-haiku-c9c2570.mp4](examples/commit-haiku-c9c2570.mp4)

## Install

This skill is installed by copying its files into your user skills directory.

```powershell
$dest = "$env:USERPROFILE\.claude\skills\commit-haiku"
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item .\SKILL.md, .\generate_video.py $dest
```

```bash
mkdir -p ~/.claude/skills/commit-haiku
cp SKILL.md generate_video.py ~/.claude/skills/commit-haiku/
```

Restart Claude Code (or open a new session); the skill registers automatically from its frontmatter.

### Requirements

- Python 3.11+ (uses stdlib only — no `pip install` step).
- A Gemini API key with Veo access. Get one at https://aistudio.google.com/apikey.

### API key setup (one-time)

The helper resolves the key from this chain (first hit wins):

1. `--api-key <KEY>` CLI flag
2. `--api-key-file <PATH>` CLI flag
3. `$GEMINI_API_KEY` env var (**recommended** — matches the official `google-genai` SDK)
4. `$GOOGLE_API_KEY` env var
5. `~/.claude/skills/commit-haiku/.api-key` (user-level file colocated with the skill)
6. `./gemini.txt` in the cwd (legacy — kept for back-compat)

Pick one and you're done:

```powershell
# PowerShell — persisted user env var
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "<KEY>", "User")

# OR a user-level file (no shell restart needed)
"<KEY>" | Out-File -Encoding ascii -NoNewline `
  "$env:USERPROFILE\.claude\skills\commit-haiku\.api-key"
```

```bash
# bash — env var
echo 'export GEMINI_API_KEY=<KEY>' >> ~/.zshrc  # or ~/.bashrc

# OR a user-level file
mkdir -p ~/.claude/skills/commit-haiku
echo -n '<KEY>' > ~/.claude/skills/commit-haiku/.api-key
```

## Usage

From inside any git repo:

```
/commit-haiku
```

Or:

```
haiku my last commit
make a commit haiku for HEAD~3
/commit-haiku abc1234
```

Claude reads the diff, writes the haiku, shows it to you alongside the full Veo prompt, then kicks off the helper in the background. The MP4 lands at `./commit-haiku-<shortsha>.mp4` after ~1 minute (Veo 3 Fast) or 3–6 minutes (Veo 3).

For higher visual quality, say "make it higher quality" — the skill will switch to `veo-3.0-generate-001`.

## How it works

1. **Claude** (in-conversation) runs `git show --stat` + `git show` against the ref, reads the message and the patch, and writes the haiku. The haiku-writing is not an API call — it uses the model that's already running in your Claude Code session.
2. **Claude** composes a Veo prompt that pairs a single dramatic visual scene with the haiku as quoted dialogue (Veo 3 reads quoted text verbatim as spoken lines).
3. **`generate_video.py`** submits the prompt to the Gemini `predictLongRunning` endpoint, polls until the operation completes, and streams the resulting MP4 from the Files API to disk.

## Standalone use

`generate_video.py` works on its own if you just want to call Veo:

```powershell
python generate_video.py `
  --prompt 'A lighthouse beam sweeping across a dark sea at dawn. Narrator: "Lonely light, awake."' `
  --output .\out.mp4
```

```
usage: generate_video.py [-h] --prompt PROMPT [--model MODEL] [--output OUTPUT]
                         [--api-key API_KEY] [--api-key-file API_KEY_FILE]
                         [--poll-seconds POLL_SECONDS]
                         [--timeout-seconds TIMEOUT_SECONDS]
                         [--aspect-ratio ASPECT_RATIO]
```

Defaults: `--model veo-3.0-fast-generate-001`, `--output ./haiku.mp4`, `--aspect-ratio 16:9`, `--poll-seconds 10`, `--timeout-seconds 900`.

## Cost

Approximate Gemini API pricing for an 8-second clip:

| Model | Per-second | Per 8s clip |
|---|---|---|
| `veo-3.0-fast-generate-001` | low | a few cents |
| `veo-3.0-generate-001` | higher | a few dimes |

Check the [Gemini API pricing page](https://ai.google.dev/pricing) for current numbers.

## Files

- `SKILL.md` — the skill manifest Claude Code loads. Frontmatter declares the trigger phrases; the body is the prompt Claude follows when invoked.
- `generate_video.py` — the Veo client. Zero pip deps (stdlib `urllib` only).

## License

MIT
