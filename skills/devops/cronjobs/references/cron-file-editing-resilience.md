# Cron job file-editing resilience patterns

Session context: when editing cron job scripts and configs across multiple turns, env resets and context compression can interrupt large edits. This reference captures lessons from the 2026-09-16 FHS/KSFP/ASPD conversion and the data_importer.py rewrite.

## Two editing patterns, two resilience profiles

### Pattern A: `write_file` for complete replacement

**Best for:** files under ~200 lines, or when you have the complete corrected content ready.

**Risk:** on files 500+ lines, a single `write_file` can be truncated by turn timeout + env reset, leaving the file in a partially-written state. The next turn sees a broken file.

**Resilience strategy:** for large files, prefer Pattern B.

### Pattern B: targeted `patch` operations

**Best for:** files 200+ lines with scattered fixes, or when only specific sections need changing.

**How:** use `patch` with `old_string`/`new_string` targeting specific function bodies or line ranges. One patch per logical fix.

**Why more resilient:**
- Each patch is small enough to complete in one turn
- A failed patch (no match) is immediately visible — re-read the file and re-assess
- Partial state from a prior turn's failed patch is still valid — the old content is still there
- You can `grep` for specific patterns to verify each fix landed before moving to the next

**Pitfall — context bleed:** a patch that replaces a multi-line block can leave variable references from the old block in the new code. Example: replacing a `try/finally` block where the `finally` clause references a variable (`close_after`) that was defined inside the replaced `try` block. After patching, re-read the surrounding context to check for orphaned references.

## Verification pattern for multi-fix edits

After each patch on a large file:

```bash
# Syntax check
python3 -m py_compile python/script.py && echo "OK" || echo "BROKEN"

# Count remaining occurrences of each legacy pattern
grep -c "PATTERN" python/script.py

# Count new patterns present
grep -c "NEW_PATTERN" python/script.py
```

Do this between patches, not after all patches are applied. If patch #3 fails to match, you don't want to discover it after also applying patches #4 and #5 on top of a partially-edited file.

## Write vs patch decision

| File size | Number of fixes | Recommended approach |
|-----------|----------------|---------------------|
| < 200 lines | Any | `write_file` with complete corrected content |
| 200-500 lines | 1-2 focused fixes | `patch` on specific sections |
| 200-500 lines | 3+ scattered fixes | `patch` each fix separately, verify between |
| 500+ lines | Any | `patch` each fix separately, verify between |

## Cron job script edits specifically

Cron job scripts (`script:` field in job config) are often shell wrappers under 50 lines — `write_file` is usually fine for these. The prompts for agent-mode cron jobs are long (2000+ chars) but are edited via `cronjob action=update` with the full prompt text, not file edits.

The `data_importer.py` case (819 lines, 6 distinct fix categories) is the canonical example of when to use Pattern B.
