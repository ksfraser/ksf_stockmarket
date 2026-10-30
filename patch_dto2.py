#!/usr/bin/env python3
"""Fix the DTO: __init__ sets attrs (strip set_), field_names and to_dict use attrs, from_json calls setter(value)."""
from pathlib import Path
p = Path('/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py')
src = p.read_text()

# Fix __init__: attr = _f[4:] if _f.startswith('set_') else _f
old = "            attr = _f[4:] if _f.startswith('set_') else _f  # set_foo -> foo"
new = "            attr = _f[4:] if _f.startswith('set_') else _f"
if old in src:
    src = src.replace(old, new, 1)
    print("Fixed __init__ comment")
else:
    print("No change to __init__ (already clean)")

# Fix field_names to return attr names
old_fn = "    def field_names(self) -> List[str]:\n        \"\"\"Return all DTO field names (excluding structural).\"\"\"\n        return [f for f in self.__fields__ if f not in {'set_symbol', 'set_price_date'}]"
new_fn = "    def field_names(self) -> List[str]:\n        \"\"\"Return all DTO field attribute names (excluding structural).\"\"\"\n        result = []\n        skip = {'set_symbol', 'set_price_date'}\n        for f in self.__fields__:\n            if f in skip:\n                continue\n            result.append(f[4:] if f.startswith('set_') else f)\n        return result"
if old_fn in src:
    src = src.replace(old_fn, new_fn, 1)
    print("Fixed field_names")
else:
    print("field_names already fixed?")

# Fix to_dict to use attr names
old_td = "    def to_dict(self) -> Dict[str, Optional[float]]:\n        \"\"\"Return dict mapping canonical field names → values (only non-None).\"\"\"\n        d = {}\n        for field in self.__fields__:\n            val = getattr(self, field, None)\n            if val is not None:\n                d[field] = val\n        return d"
new_td = "    def to_dict(self) -> Dict[str, Optional[float]]:\n        \"\"\"Return dict mapping canonical field attribute names -> values (only non-None).\"\"\"\n        d = {}\n        for setter_name in self.__fields__:\n            attr = setter_name[4:] if setter_name.startswith('set_') else setter_name\n            val = getattr(self, attr, None)\n            if val is not None:\n                d[attr] = val\n        return d"
if old_td in src:
    src = src.replace(old_td, new_td, 1)
    print("Fixed to_dict")
else:
    print("to_dict already fixed?")

# Fix from_json setter call
old_sc = "            setter(value)\n            seen.add(key)"
new_sc = "            setter(value)\n            seen.add(key)"
# Check if it's already correct
count = src.count("setter(self, value)")
if count > 0:
    src = src.replace("setter(self, value)", "setter(value)")
    print(f"Fixed {count} setter(self, value) -> setter(value)")
elif src.count("setter(value)") > 0:
    print("setter(value) already correct")
else:
    print("WARNING: could not find setter call pattern")

p.write_text(src)
print("Done")
