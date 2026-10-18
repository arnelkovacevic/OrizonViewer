"""Stampa APP_VERSION leggendo app/config.py (senza importare Qt). Usato da build_exe.bat."""
import os
import re
import sys

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "config.py")
match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', open(path, encoding="utf-8").read(), re.M)
if not match:
    sys.exit(1)
print(match.group(1))
