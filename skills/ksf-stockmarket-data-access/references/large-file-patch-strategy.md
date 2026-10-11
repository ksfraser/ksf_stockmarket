# Large-File Patch Strategy — Surviving Turn Timeouts and Env Resets

When patching a large script (500+ lines) that has multiple scattered fixes, **do not use one big `write_file` of the complete corrected file**. This session's `data_importer.py` (908 lines) hit exactly this problem: a single `write_file` got truncated by a turn timeout + environment reset, and the file reverted to its pre-fix state.

## Why one big write_file fails on large files

- **Turn timeout**: a `write_file` of 800+ lines can exceed the turn's time budget, especially when combined with prior tool calls in the same turn.
- **Env reset at turn boundary**: if the turn is interrupted after the write but before the next verification, the working tree resets to the last committed state. The partial write is lost.
- **Silent failure**: a truncated `write_file` may leave a syntactically valid but semantically broken file (e.g. half the new code, half the old). `py_compile` passes because the syntax is valid — the logic bugs are invisible until runtime.

## The targeted-patch approach

Instead, fix one issue at a time with `patch`, verifying between each:

1. **Count the scope first** — `grep -c` each problematic pattern so you know how many locations need fixing and can verify each is resolved.
2. **Patch in dependency order** — fix the function that everything else depends on first (e.g. `write_prices()`), then error handling, then credential patterns.
3. **Verify after each patch** — run `grep -c` again to confirm the fix landed. Don't batch 5 patches and discover #3 didn't match.
4. **Re-read the file when a patch fails to match** — the file may have changed from a prior turn's partial fix. The `patch` tool tells you when the `old_string` isn't found; that's a signal to re-read, not to guess a new string.
5. **Use `replace_all=true` for repeated patterns** — `is_connected()`, `MySQLError`, `DB_CONFIG` each appear in multiple locations. One `replace_all` patch per pattern.
6. **Watch for context bleed** — a patch that replaces a multi-line block can leave variables from the old block referenced in nearby code. After removing a large block, read the lines immediately before and after the patch boundary.

## When one big write_file IS fine

- Files under ~200 lines
- Files where the entire content is being replaced (not patched)
- When you can verify the complete file compiles and the key patterns are correct in the same turn

## Verification commands (reusable template)

After patching any large script, run a compaction-resistant verification:

```bash
cd /path/to/repo
python3 -m py_compile <file> && echo "COMPILES OK"

# Each of these should return the expected count:
grep -c "<bad_pattern_1>" <file>   # should be 0
grep -c "<bad_pattern_2>" <file>   # should be 0
grep -c "<good_pattern>" <file>    # should be >0
```

This is compaction-resistant because each `grep -c` returns a single integer — even if the conversation gets compacted, the verification numbers survive as tool output.

## Signals that targeted patches are the right call

- File is 500+ lines
- Fixes are scattered across multiple functions/sections
- You'd need to read the entire file to write a correct replacement
- A prior turn's write_file was truncated or failed to match
- The file is under active development (other changes may land between turns)
