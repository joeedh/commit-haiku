# Working on this repo

This is the **development repo** for the `commit-haiku` skill. The installed copy lives at `~/.claude/skills/commit-haiku/`. Editing files here does **not** affect the installed skill until they're copied over.

## Layout

- `SKILL.md` — the manifest Claude Code loads. Frontmatter `name` + `description` controls when the skill triggers; the body is the prompt the running agent follows. Treat it as a prompt, not docs.
- `generate_video.py` — the Veo client. Stdlib-only (`urllib`, `argparse`, `json`). **Do not add pip dependencies** — the skill is meant to work on any machine with Python 3.11+ installed.
- `README.md` — human-facing install/usage guide.
- `examples/` — sample MP4s checked in for the README to link. Named `commit-haiku-<shortsha>.mp4` matching the filename pattern the skill writes.

## Editing workflow

Changes only take effect after copying into the user skills dir:

```powershell
$dest = "$env:USERPROFILE\.claude\skills\commit-haiku"
Copy-Item .\SKILL.md, .\generate_video.py $dest -Force
```

After copying, restart Claude Code (or open a new session) so the SKILL.md frontmatter re-registers.

## SKILL.md ↔ generate_video.py contract

Keep these in sync when changing either side:

- **API key resolution chain.** The order in `generate_video.py:resolve_api_key` must match the chain documented in SKILL.md's "Inputs" / "API key setup" sections and in `README.md`. If you add a source, update all three.
- **Default model.** `--model` default in argparse must match what SKILL.md tells Claude to assume (currently `veo-3.0-fast-generate-001`).
- **Default output path.** `--output` default + the filename pattern SKILL.md tells Claude to use (`commit-haiku-<shortsha>.mp4`) must agree.
- **Error messages.** SKILL.md tells Claude to "relay the script's error verbatim". If you change the wording or structure of an error in `generate_video.py`, no SKILL.md change is needed — but don't make errors so terse that the user can't act on them.

## Verifying changes

The smoke test that proves the helper works without burning an API call:

```powershell
python .\generate_video.py --prompt "test" --timeout-seconds 1
```

Expect: `submitting...` → `operation: ...` → one `still generating` line → `error: timed out`. If you see a key-resolution error instead, the API key wasn't found at any of the six sources.

End-to-end test: install (via the copy command above), `cd` to any git repo, run `/commit-haiku`. The MP4 should land in ~1 minute.

## Style

- No comments that just restate the code. The `WHY` of a non-obvious choice belongs in a one-liner; the `WHAT` is already visible.
- `urllib`, not `requests`. Keeping zero deps is a feature, not an accident.
- Errors via `sys.exit("error: ...")`, not exceptions or logging. The script is invoked by Claude Code as a one-shot — exit codes + stderr is the whole interface.

## Out of scope

- No haiku generation here. Claude writes the haiku in-conversation from the diff; this script only renders. Don't add a Gemini text call to "improve" the haiku.
- No video editing, captioning, transcoding, or upload. The script writes one MP4 and exits.
