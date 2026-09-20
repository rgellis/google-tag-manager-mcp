#!/usr/bin/env python3
"""Mint a Tag Manager refresh token.

Runs the OAuth installed-app flow and prints a refresh token carrying only the
Tag Manager scopes, which is what this server needs to authenticate.

Usage:
    GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... uv run scripts/get_refresh_token.py

    # read-only token (recommended unless this server will edit containers)
    ... uv run scripts/get_refresh_token.py --read-only

Tag Manager splits write access six ways -- editing containers, editing
container versions, deleting containers, managing accounts, managing users and
publishing -- so a token covering the whole API has to request all of them. A
read-only token needs one scope and cannot change anything.

The OAuth client must have http://localhost as an authorised redirect URI and be
of type "Desktop app" (or "Web application" with localhost allowed). Scope the
token to this server alone rather than reusing a token minted for other Google
APIs: re-consenting a shared token to add the Tag Manager scopes rotates a
secret that everything else using it depends on.
"""

from __future__ import annotations

import argparse
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE_READONLY = "https://www.googleapis.com/auth/tagmanager.readonly"
SCOPES_FULL = [
    SCOPE_READONLY,
    "https://www.googleapis.com/auth/tagmanager.edit.containers",
    "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
    "https://www.googleapis.com/auth/tagmanager.delete.containers",
    "https://www.googleapis.com/auth/tagmanager.manage.accounts",
    "https://www.googleapis.com/auth/tagmanager.manage.users",
    "https://www.googleapis.com/auth/tagmanager.publish",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Request tagmanager.readonly only, instead of every write scope.",
    )
    args = parser.parse_args()

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must both be set.",
            file=sys.stderr,
        )
        return 1

    scopes = [SCOPE_READONLY] if args.read_only else list(SCOPES_FULL)

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=scopes,
    )

    # access_type=offline + prompt=consent is what actually returns a refresh
    # token; without prompt=consent Google omits it on repeat authorisations.
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )

    if not credentials.refresh_token:
        print(
            "No refresh token returned. Revoke this client's access at "
            "https://myaccount.google.com/permissions and try again.",
            file=sys.stderr,
        )
        return 1

    print()
    print(f"Scopes granted ({len(scopes)}):")
    for scope in scopes:
        print(f"  {scope}")
    print()
    print("Set this as GOOGLE_TAG_MANAGER_REFRESH_TOKEN:")
    print()
    print(f"  {credentials.refresh_token}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
