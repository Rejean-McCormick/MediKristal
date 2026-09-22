from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--permission", action="append", default=[])
    parser.add_argument("--case-grant", action="append", default=[], help="Case UUID accessible to this principal; repeatable.")
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()
    secret = os.environ["MEDIKRISTAL_AUTH_SECRET"].encode()
    payload = {
        "tenant_id": args.tenant, "principal_id": args.principal,
        "permissions": args.permission, "case_grants": args.case_grant,
        "exp": int(time.time()) + args.ttl,
    }
    pb = b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = b64(hmac.new(secret, pb.encode(), hashlib.sha256).digest())
    print(pb + "." + sig)


if __name__ == "__main__":
    main()
