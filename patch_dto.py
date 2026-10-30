#!/usr/bin/env python3
"""Quick patch: fix __init__, to_dict, field_names, and from_json setter call."""
from pathlib import Path
p = Path('/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py')
src = p.read_text()

# 1. Fix __init__: set attribute (strip 'set_'), not the method itself
old_init = """    def __init__(self):
        for _f in self.__fields__:
            attr = _f[4:] if _f.startswith('set_') else _f  # set_foo -> foo
            setattr(self, attr, None)
"""
new_init = """    def __init__(self):
        for _f in self.__fields__:
            attr = _f[4:] if _f.startswith('set_') else _f
            setattr(self, attr, None)
"""
assert old_init in src, "init block not found"
src = src.replace(old_init, new_init, 1)

# 2. Fix field_names: return attribute names (strip 'set_')
old_fn = """    def field_names(self) -> List[str]:
        \"\"\"Return all DTO field names (excluding structural).\"\"\"
        return [f for f in self.__fields__ if f not in {'set_symbol', 'set_price_date'}]
"""
new_fn = """    def field_names(self) -> List[str]:
        \"\"\"Return all DTO field attribute names (excluding structural).\"\"\"
        result = []
        for f in self.__fields__:
            if f in ('set_symbol', 'set_price_date'):
                continue
            attr = f[4:] if f.startswith('set_') else f
            result.append(attr)
        return result
"""
assert old_fn in src, "field_names block not found"
src = src.replace(old_fn, new_fn, 1)

# 3. Fix to_dict: iterate attr names, get attribute values
old_td = """    def to_dict(self) -> Dict[str, Optional[float]]:
        \"\"\"Return dict mapping canonical field names → values (only non-None).\"\"\"
        d = {}
        for field in self.__fields__:
            val = getattr(self, field, None)
            if val is not None:
                d[field] = val
        return d
"""
new_td = """    def to_dict(self) -> Dict[str, Optional[float]]:
        \"\"\"Return dict mapping canonical field attribute names -> values (only non-None).\"\"\"
        d = {}
        for setter_name in self.__fields__:
            attr = setter_name[4:] if setter_name.startswith('set_') else setter_name
            val = getattr(self, attr, None)
            if val is not None:
                d[attr] = val
        return d
"""
assert old_td in src, "to_dict block not found"
src = src.replace(old_td, new_td, 1)

# 4. Fix from_json: call setter(value) not setter(self, value)
old_setter_call = "            setter(value)\n            seen.add(key)"
new_setter_call = "            setter(value)\n            seen.add(key)"
# Already correct? Check what's there now
if "setter(self, value)" in src:
    src = src.replace("setter(self, value)", "setter(value)")
    print("Fixed setter(self, value) -> setter(value)")

p.write_text(src)
print("Patched __init__, field_names, to_dict, from_json setter call")
