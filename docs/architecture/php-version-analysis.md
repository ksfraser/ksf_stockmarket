# PHP Version Compatibility Analysis: FA + ksf_stockmarket

## Current Environment

| Component | Version | Notes |
|-----------|---------|-------|
| FA production image | `genebarker/frontaccounting:latest` | Based on FA 2.4.x |
| FA Dockerfile reference | `php:7.4-apache` | Original target |
| FA dev container | MariaDB 10.11 | Running on host |
| Local PHP (Fedora 36) | **8.1.18** | What we code on |
| KSF modules (Calendar, API, etc.) | Target `>=7.4` | Composer platform pinned to 7.4.33 |

## PHP 8.0 vs 8.1 — What FA Actually Uses

### FA Core Compatibility: GOOD for 8.0, MOSTLY GOOD for 8.1

Scanned the entire FA core (`fa_files/` reference copy):

**✅ No showstoppers found:**
- No `each()` (removed in 8.0)
- No `create_function()` (removed in 8.0)
- No `call_user_method*()` (removed in 8.0)
- No `mysql_*` functions (removed in 7.0) — FA uses `mysqli_*`
- No `set_magic_quotes_runtime()` (removed in 7.0)
- No `php_errormsg` (removed in 8.0)
- No `$php_errormsg` implicit variable

**⚠️ PHP 8.0 deprecations that FA triggers (E_DEPRECATED):**
1. **Passing null to non-nullable internal functions** — e.g., `strlen(null)`, `trim(null)`. FA does this in places where form fields may be null. On 8.0 these throw `E_DEPRECATED`; on 8.1 they throw `TypeError` in some cases.
2. **Implicit float-to-int conversion** — FA has some `int` params that receive floats.
3. **`$this` from static context** — minor, in some edge cases.

**⚠️ PHP 8.1 deprecations (additional):**
1. **Returning `$this` from void methods** — not in FA core
2. **Implicit incompatible float/int comparison** — minor
3. **`serialize()` with allowed_classes** — not in FA core
4. **`mysqli` error mode change** — FA already uses `mysqli_report()` properly

### KSF Module Compatibility: EXCELLENT

All KSF modules (Calendar, API, CRM, etc.) already:
- Use `declare(strict_types=1)` in some files
- Use typed parameters and return types
- Use `??` null coalescing
- Use namespaces and PSR-4 autoloading
- Target `>=7.4` in composer.json
- The Calendar module explicitly notes "PHP 7.4 compatible - no PHP 8+ syntax" in cal.php

## Recommendation: Code for PHP 7.4

### Why 7.4, not 8.0 or 8.1:

1. **FA's own Dockerfile targets 7.4** — the reference image is `php:7.4-apache`
2. **KSF modules pin to 7.4.33** in composer platform config
3. **The production FA pod may be running 7.4** — the `genebarker/frontaccounting:latest` image historically used 7.4
4. **Zero feature loss** — everything we need works in 7.4:
   - ✅ Typed properties (7.4+)
   - ✅ Arrow functions (7.4+)
   - ✅ Null coalescing `??` (7.0+)
   - ✅ Namespaces (5.3+)
   - ✅ PSR-4 autoloading
   - ✅ `declare(strict_types=1)`
   - ✅ Typed parameters and return types
   - ✅ Anonymous classes (7.0+)
   - ✅ `splat` operator (5.6+)

### What we'd lose going from 8.1 → 7.4:

| Feature | PHP 8.1 | PHP 7.4 | Impact |
|---------|---------|---------|--------|
| `readonly` properties | ✅ | ❌ | Low — can use `@var` docblocks |
| Enums | ✅ | ❌ | Low — can use class constants |
| Fibers | ✅ | ❌ | None — not needed |
| `never` return type | ✅ | ❌ | Low — use `void` |
| `final const` | ✅ | ❌ | None |
| `array_is_list()` | ✅ | ❌ | Low — easy to polyfill |
| Intersection types | ✅ | ❌ | None — not needed |
| First-class callable syntax | ✅ | ❌ | Low — use `[$obj, 'method']` |
| `new in initializers` | ✅ | ❌ | Low — assign in constructor |
| Explicit octal notation | ✅ | ❌ | None |

### What we'd lose going from 8.0 → 7.4:

| Feature | PHP 8.0 | PHP 7.4 | Impact |
|---------|---------|---------|--------|
| Named arguments | ✅ | ❌ | Low — use positional |
| Constructor property promotion | ✅ | ❌ | Medium — more boilerplate |
| Match expressions | ✅ | ❌ | Low — use switch |
| Nullsafe operator `?->` | ✅ | ❌ | Medium — use `if ($x)` checks |
| Union types | ✅ | ❌ | Low — use `@param` docblocks |
| `str_contains()` | ✅ | ❌ | Low — use `strpos() !== false` |
| `str_starts_with()` | ✅ | ❌ | Low — use `strpos() === 0` |
| `str_ends_with()` | ✅ | ❌ | Low — use `substr()` |
| `get_debug_type()` | ✅ | ❌ | Low — use `get_class()` |

## Impact Assessment

### HIGH impact (would need code changes):
- **Constructor property promotion** — saves significant boilerplate in DTOs/models. Without it, we write traditional constructors.
- **Nullsafe operator `?->`** — used frequently in FA hooks where `$app` or `$db` might be null. Without it, we need explicit null checks.

### MEDIUM impact:
- **Named arguments** — nice for readability with many-parameter functions, but not essential.
- **Match expressions** — cleaner than switch for simple value matching, but switch works fine.

### LOW impact:
- Everything else — easily worked around or not needed.

## Conclusion

**Code for PHP 7.4.** The feature loss is minimal (mainly constructor promotion and nullsafe operator), and it guarantees compatibility with:
1. The FA production container (likely 7.4)
2. All existing KSF modules (pinned to 7.4.33)
3. The FA core codebase (written for 7.4)

The two features we'll miss most:
- **Constructor promotion**: Instead of `public function __construct(public string $name, public int $id)`, we write traditional `$this->name = $name; $this->id = $id;`
- **Nullsafe operator**: Instead of `$user?->getName()`, we write `$user !== null ? $user->getName() : null`

Both are trivial workarounds. The compatibility guarantee is worth it.
