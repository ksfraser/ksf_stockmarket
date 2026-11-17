import sys
import os

REPO_ROOT = "/root/Documents/stockmarket/php/stockmarket-app"
for _c in (REPO_ROOT, os.path.join(REPO_ROOT, "python", "src"), os.path.join(REPO_ROOT, "python")):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from config_loader import Config
c = Config(os.path.join(REPO_ROOT, "config.yaml"))
print("db_password:", repr(c.data.db_password))
print("has secrets attr:", hasattr(c.data, "secrets"))
try:
    print("secrets:", c.data.secrets)
except Exception as e:
    print("secrets error:", e)
print("env DB_PASS set:", bool(os.environ.get("DB_PASS")))
