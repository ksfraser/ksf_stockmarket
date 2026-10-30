#!/usr/bin/env python3
"""Inject the 27 missing bb underscore setters into the DTO, then re-verify."""
from pathlib import Path
p = Path('/home/ksf_stockmarket/ksf_stockmarket/migrate_indicators_json_to_columnar.py')
lines = p.read_text().split('\n')

# Find the line with "def set_apo_7(self, v): self.apo_7 = v"
insert_after = None
for i, line in enumerate(lines):
    if 'def set_apo_7(self, v): self.apo_7 = v' in line:
        insert_after = i
        break

if insert_after is None:
    print("ERROR: set_apo_7 not found")
    exit(1)

print(f"Inserting after line {insert_after + 1}: {lines[insert_after].strip()}")

bb_setters = [
    # bb_5_* (5-period Bollinger with 2.0/2.5 std)
    ("set_bb_5_2_0_lower", "self.bb_5_2_0_lower"),
    ("set_bb_5_2_0_mid", "self.bb_5_2_0_mid"),
    ("set_bb_5_2_0_upper", "self.bb_5_2_0_upper"),
    ("set_bb_5_2_5_lower", "self.bb_5_2_5_lower"),
    ("set_bb_5_2_5_mid", "self.bb_5_2_5_mid"),
    ("set_bb_5_2_5_upper", "self.bb_5_2_5_upper"),
    # bb_10_* (10-period Bollinger with 2.0/2.5 std)
    ("set_bb_10_2_0_lower", "self.bb_10_2_0_lower"),
    ("set_bb_10_2_0_mid", "self.bb_10_2_0_mid"),
    ("set_bb_10_2_0_upper", "self.bb_10_2_0_upper"),
    ("set_bb_10_2_5_lower", "self.bb_10_2_5_lower"),
    ("set_bb_10_2_5_mid", "self.bb_10_2_5_mid"),
    ("set_bb_10_2_5_upper", "self.bb_10_2_5_upper"),
    # bb_20_* (20-period Bollinger with 2.0/2.5 std)
    ("set_bb_20_2_0_lower", "self.bb_20_2_0_lower"),
    ("set_bb_20_2_0_mid", "self.bb_20_2_0_mid"),
    ("set_bb_20_2_0_upper", "self.bb_20_2_0_upper"),
    ("set_bb_20_2_5_lower", "self.bb_20_2_5_lower"),
    ("set_bb_20_2_5_mid", "self.bb_20_2_5_mid"),
    ("set_bb_20_2_5_upper", "self.bb_20_2_5_upper"),
    # bb_50_* (50-period Bollinger with 1.5/2.0/2.5 std)
    ("set_bb_50_1_5_lower", "self.bb_50_1_5_lower"),
    ("set_bb_50_1_5_mid", "self.bb_50_1_5_mid"),
    ("set_bb_50_1_5_upper", "self.bb_50_1_5_upper"),
    ("set_bb_50_2_0_lower", "self.bb_50_2_0_lower"),
    ("set_bb_50_2_0_mid", "self.bb_50_2_0_mid"),
    ("set_bb_50_2_0_upper", "self.bb_50_2_0_upper"),
    ("set_bb_50_2_5_lower", "self.bb_50_2_5_lower"),
    ("set_bb_50_2_5_mid", "self.bb_50_2_5_mid"),
    ("set_bb_50_2_5_upper", "self.bb_50_2_5_upper"),
]

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if i == insert_after:
        new_lines.append("    @_setter")
        for setter_name, attr_name in bb_setters:
            new_lines.append(f"    def {setter_name}(self, v): {attr_name} = v")

p.write_text('\n'.join(new_lines))
print(f"Injected {len(bb_setters)} bb setters.")

# Verify
import importlib.util
spec = importlib.util.spec_from_file_location('mig', str(p))
mod = importlib.util.module_from_spec(spec)
import os
os.environ['DB_PASS'] = 'Zaqwsx9sm1@'
spec.loader.exec_module(mod)

bb_fields = [f for f in mod.IndicatorDTO.__fields__ if f.startswith('set_bb_')]
print(f"bb_ setters in __fields__: {len(bb_fields)}")
print(f"total __fields__: {len(mod.IndicatorDTO.__fields__)}")

# Quick DTO test
from decimal import Decimal
os.environ.pop('DB_PASS', None)  # won't be needed for DTO test
dto = mod.IndicatorDTO()
dto.set_symbol('AAPL')
dto.set_price_date('2026-09-09')
dto.from_json({
    'ad': 1.5,
    'rsi_14': 50.0,
    'bb_10_2.0_lower': 100.0,   # dotted -> underscore via _KEY_MAP
    'bb_5_2_5_lower': 200.0,    # already underscore
    'macd_12_26_9_hist': 2.5,
})
print(f"bb_10_2_0_lower (was bb_10_2.0_lower): {dto.bb_10_2_0_lower}")
print(f"bb_5_2_5_lower: {dto.bb_5_2_5_lower}")
print(f"rsi_14: {dto.rsi_14}")
print(f"ad: {dto.ad}")
print(f"field_names count: {len(dto.field_names())}")
print(f"to_dict: {len(dto.to_dict())} keys")
print("DTO SMOKE TEST: OK")
