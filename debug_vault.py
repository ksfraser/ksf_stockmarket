#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'python')
import config_loader

# Patch _decrypt_vault to print pw_file
orig_decrypt = config_loader._decrypt_vault

def patched_decrypt(vault_path, password_file):
    print(f"_decrypt_vault called with password_file={password_file!r}")
    result = orig_decrypt(vault_path, password_file)
    return result

config_loader._decrypt_vault = patched_decrypt

# Also patch Config.__init__ to print before decryption
orig_init = config_loader.Config.__init__

def patched_init(self, path=None):
    # Read config first
    if path is None:
        path = 'config.yaml'
    with open(path) as f:
        data = config_loader.yaml.safe_load(f)
    vault = data.get('vault', {})
    print(f"CONFIG PATH: {path}")
    print(f"vault_cfg: {vault}")
    orig_init(self, path)

config_loader.Config.__init__ = patched_init

cfg = config_loader.Config('config.yaml')
