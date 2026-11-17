# Non-ASCII Characters Block Git Commit in This Repo

## Problem

Git in `/home/ksf_stockmarket/ksf_stockmarket` is configured with `core.quotepath` or similar settings that reject non-ASCII characters in file content during `git add`/`git commit`. Any `.md` file (or `.py` file with non-ASCII string literals) containing characters outside the ASCII range will cause the commit to fail.

## Symptoms

```
$ git commit -m "..."
[filename]: needs UTF-8 transfer encoding
[filename]: ADR snippet above
[filename]: ADR snippet above
error: RPC failed; result=1, HTTP code=400
```

Or the commit appears to succeed but files are silently dropped from the commit. Or `git status` shows the file as modified again immediately after commit.

## Characters that trigger this

Common non-ASCII characters found in documentation written for this project:

| Character | Name | Common source |
|-----------|------|---------------|
| `→` | Right arrow | "primary → secondary → fallback" chain descriptions |
| `—` | Em dash | Sentence punctuation in requirements tables |
| `–` | En dash | Ranges (e.g. "1–3 paragraphs") |
| `≥` | Greater-than-or-equal | "guarantee ≥ 75%", "MER ≥ 2.5%" |
| `≤` | Less-than-or-equal | "rank ≤ 2", "MER ≤ 2.5%" |
| `§` | Section sign | Section references ("see §10.5") |
| `│` `├` `└` `┌` `┘` `─` `┬` `┤` | Box-drawing chars | ASCII diagram tables |
| `✓` `✗` | Check/cross marks | Acceptance criteria, status indicators |
| `×` | Multiplication sign | "per-symbol × per-exchange" |
| `·` | Middle dot | List separators, "UC-15a–e" ranges |
| `▼` `◄` | Down/left arrows | Diagram arrows in architecture docs |
| `↓` `↑` | Down/up arrows | Diagram flow arrows |

## Fix: Normalize before commit

Run this script before `git add` on any `.md` file that was written or edited:

```bash
python3 -c "
import sys
for f in sys.argv[1:]:
    text = open(f, encoding='utf-8').read()
    replacements = {
        '\u2192': '->',   # →
        '\u2014': '--',   # —
        '\u2013': '-',    # –
        '\u2265': '>=',   # ≥
        '\u2264': '<=',   # ≤
        '\u00a7': 'Sec.', # §
        '\u2193': 'v',    # ↓
        '\u2191': '^',    # ↑
        '\u25bc': 'v',    # ▼
        '\u25c4': '<',    # ◄
        '\u00d7': 'x',    # ×
        '\u00b7': '-',    # ·
        '\u2713': '[OK]', # ✓
        '\u2717': '[FAIL]', # ✗
    }
    for box in ['\u2502','\u251c','\u2524','\u2514','\u2518','\u2510','\u251c','\u252c','\u253c','\u2500','\u250c']:
        replacements[box] = '+'
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    open(f, 'w', encoding='utf-8').write(text)
    print(f'Normalized: {f}')
" docs/requirements/*.md docs/architecture/*.md docs/advisors/*.md
```

This replaces the known non-ASCII characters with ASCII equivalents. The script is idempotent — running it on already-normalized files is safe.

## Prevention

When writing markdown for this repo:
- Use `->` instead of `→`
- Use `--` instead of `—`
- Use `>=` instead of `≥`
- Use `<=` instead of `≤`
- Use `Sec.` instead of `§`
- Use `+` for box-drawing characters in diagrams (not `│`, `├`, etc.)
- Use `[OK]` / `[FAIL]` instead of `✓` / `✗`
- Use `v` / `^` instead of `▼` / `▲`

## Why this matters for the ksf_stockmarket repo

The repo's git configuration rejects non-ASCII in commits. This is different from most repos where UTF-8 is the default. Always normalize before committing documentation. If a commit fails silently (files not included), check `git status` — the file will still show as modified.

## Detection

If a commit fails mysteriously or files seem to disappear from the commit, check for non-ASCII:

```bash
grep -Pn '[^\x00-\x7F]' docs/requirements/*.md docs/architecture/*.md docs/advisors/*.md
```

This prints any line containing a non-ASCII character with its file, line number, and content.
