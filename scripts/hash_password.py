#!/usr/bin/env python3
"""
Generate a bcrypt password hash for a config.yaml auth user.

Usage:
    python scripts/hash_password.py <password> [--rounds 12]

Paste the printed hash into config.yaml under auth.users[].password_hash.
"""
import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash a password for config.yaml auth users")
    parser.add_argument("password", help="Plaintext password to hash")
    parser.add_argument("--rounds", type=int, default=12, help="bcrypt cost factor (default: 12)")
    args = parser.parse_args()

    import bcrypt

    password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt(rounds=args.rounds)).decode()
    print(password_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
