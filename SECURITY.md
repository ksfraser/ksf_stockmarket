# Security & Secrets Management

## Overview

All sensitive credentials (database passwords, API keys, etc.) are stored in an
**Ansible Vault** encrypted file. No passwords are stored in plaintext in any
source file, config file, or git repository.

## Vault Files

| File | Purpose | Git? |
|------|---------|------|
| `group_vars/vault.yml` | Encrypted secrets (AES256) | ❌ `.gitignore'd` |
| `~/.vault_pass` | Vault password (chmod 600) | ❌ `.gitignore'd` |
| `config.yaml` | Non-secret config + vault path pointer | ✅ committed |

## How It Works

1. `config.yaml` has a `vault:` section pointing to the vault file and password file
2. `python/config_loader.py` calls `ansible-vault view` at runtime to decrypt
3. Decrypted secrets are available as `config.db_password`, `config.secrets`, etc.
4. All Python scripts import `Config` and read credentials — zero hardcoded passwords

## Setup (New Machine / New Developer)

### 1. Install Ansible
```bash
pip install ansible
# or
dnf install ansible
```

### 2. Get the Vault Password
The vault password file is at `/home/ksf_stockmarket/.vault_pass` (chmod 600).
Copy it to the same path on the new machine, or set the `VAULT_PASSWORD_FILE` env var.

### 3. Verify It Works
```bash
cd /home/ksf_stockmarket/ksf_stockmarket
python3 -c "
from python.config_loader import Config
c = Config('config.yaml')
print('DB host:', c.data.db_host)
print('DB password:', c.db_password)
print('Secrets:', c.secrets)
"
```

## Adding / Editing Secrets

```bash
cd /home/ksf_stockmarket/ksf_stockmarket

# Edit the vault interactively (decrypts to temp file, re-encrypts on save)
ansible-vault edit --vault-password-file /home/ksf_stockmarket/.vault_pass group_vars/vault.yml

# View current contents
ansible-vault view --vault-password-file /home/ksf_stockmarket/.vault_pass group_vars/vault.yml

# Encrypt a new file (if replacing vault entirely)
ansible-vault encrypt --vault-password-file /home/ksf_stockmarket/.vault_pass secret.yml --output group_vars/vault.yml
```

### Adding a New Secret

```bash
# View current vault
ansible-vault view --vault-password-file ~/.vault_pass group_vars/vault.yml

# The vault contains YAML key-value pairs:
# db_password: Zaqwsx9sm1@

# Add a new key:
ansible-vault edit --vault-password-file ~/.vault_pass group_vars/vault.yml
```
Add your new key to the YAML dict:
```yaml
api_key_openai: sk-...
api_key_alpk: ...
```

Then in Python:
```python
from config_loader import Config
cfg = Config()
openai_key = cfg.secrets.get('api_key_openai')
```

## Current Secrets in Vault

| Key | Description |
|-----|-------------|
| `db_password` | MySQL password for `ksfraser_stockmarket`@`ksfraser.ca` |

## PHP Credentials The PHP web dashboard stores its own DB credentials separately in
`/var/www/stockmarket-app/config/database.php` (PDO). This file is outside the git
repo and should be manually secured:
```bash
chmod 600 /var/www/stockmarket-app/config/database.php
chown root:root /var/www/stockmarket-app/config/database.php
```

## Vault Password Rotation

1. Edit the vault: `ansible-vault edit --vault-password-file ~/.vault_pass group_vars/vault.yml`
2. Update the password value
3. If the *vault password file itself* needs rotation:
   ```bash
   # Generate new vault password
   openssl rand -base64 32 > ~/.vault_pass
   chmod 600 ~/.vault_pass

   # Re-encrypt vault with new password
   ansible-vault rekey --vault-password-file ~/.old_vault_pass \
     --new-vault-password-file ~/.vault_pass \
     group_vars/vault.yml
   ```

## Git Safety

The following are in `.gitignore` and will never be committed:
- `group_vars/vault.yml` — encrypted secrets
- `.vault_pass` — vault password file
- `config/database.php` — PHP DB credentials at the web root

**If you accidentally commit a secret:**
1. Rotate the credential immediately (it's compromised)
2. Purge from git history with `git filter-branch` or BFG Repo Cleaner
3. Never rely on "deleting in next commit" — it's still in the history
