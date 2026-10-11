# File Editing — Write-Validate-Swap Pattern

## When Patch Fails to Match

When `patch(action='replace')` fails because `old_string` doesn't match the file exactly
(whitespace differences, partial prior edits, line-number drift), the `patch` tool will return
a non-zero exit and the file is unchanged. Do NOT retry with smaller substrings — the risk of
matching the wrong location grows.

## The Write-Validate-Swap Pattern

For large single-function rewrites where patch matching is unreliable:

### Step 1: Read the full file
```python
# Read entire file to get exact current content
read_file(path, offset=1, limit=2000)
```

### Step 2: Write a complete corrected version to a temp file
```python
write_file(path="/tmp/data_importer_new.py", content=NEW_CONTENT)
```

### Step 3: Validate the temp file compiles/runs
```python
terminal("python3 -m py_compile /tmp/data_importer_new.py && echo OK")
# Or test import, run lint, etc.
```

### Step 4: Swap
```python
terminal("cp /path/to/original.py /path/to/original.py.bak")
terminal("cp /tmp/data_importer_new.py /path/to/original.py")
```

### Step 5: Verify
```python
terminal("python3 -m py_compile /path/to/original.py && echo OK")
# Run any existing tests
```

## Why This Works Better Than Patch

- `patch` uses fuzzy string matching — fragile when the file has been partially edited
- A complete rewrite eliminates ambiguity about what the final state should be
- Validation runs on the temp file before any damage to the original
- The backup preserves the original for diff/comparison

## When to Use

- Function rewrites spanning 50+ lines where `old_string` is hard to match precisely
- Files that have been patched multiple times and may have inconsistent state
- Any `patch` attempt that fails with "old_string not found" on the first try

## When NOT to Use

- Small targeted fixes (1-5 lines) where `patch` reliably matches
- Multi-file coordinated changes where patch's atomicity matters
- Files under active git version control where you want clean commits per change
