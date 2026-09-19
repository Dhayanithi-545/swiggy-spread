"""
auth.py - logs you into your own Swiggy account and gets a real access token.

Run once:

    python auth.py

What happens:
  1. Registers this app with Swiggy (Dynamic Client Registration - no
     approval needed, this is instant and automatic).
  2. Opens your browser to Swiggy's login page (phone number + OTP).
  3. Catches the redirect on localhost, exchanges the code for a token.
  4. Saves the token to .swiggy_token.json next to this file.

Every other file (mcp_client.py, live_tools.py, run_live.py) reads that
token file - you only need to run this again when it expires (5 days)
or when you delete the token file.

Nothing here is guessed. Every endpoint, parameter and response shape
comes straight from https://mcp.swiggy.com/builders/docs/start/authenticate/
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

BASE = "https://mcp.swiggy.com"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".swiggy_token.json")

# Change this if you want fewer/more servers. Matches Swiggy's v1 scopes.
SCOPE = "mcp:tools mcp:resources mcp:prompts"


@dataclass
class TokenSet:
    access_token: str
    expires_in: int
    scope: str

    def save(self) -> None:
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": self.access_token,
                       "expires_in": self.expires_in,
                       "scope": self.scope}, f)
        os.chmod(TOKEN_FILE, 0o600)  # your token, nobody else's business


def load_token() -> str | None:
    """Returns a cached access token, or None if you need to run auth.py."""
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f).get("access_token")


# ---------------------------------------------------------------- PKCE


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


# ---------------------------------------------------------------- callback catcher


class _CallbackResult:
    code: str | None = None
    state: str | None = None
    error: str | None = None


def _wait_for_callback(expected_state: str) -> _CallbackResult:
    result = _CallbackResult()
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            result.code = qs.get("code", [None])[0]
            result.state = qs.get("state", [None])[0]
            result.error = qs.get("error", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if result.code and result.state == expected_state:
                self.wfile.write(b"<h2>Logged in. You can close this tab.</h2>")
            else:
                self.wfile.write(b"<h2>Login failed or state mismatch. Check your terminal.</h2>")
            done.set()

        def log_message(self, *args):  # silence default request logging
            pass

    server = HTTPServer(("localhost", REDIRECT_PORT), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    done.wait(timeout=180)
    server.server_close()
    return result


# ---------------------------------------------------------------- main flow


def register_client() -> str:
    """Step 1: Dynamic Client Registration. No approval needed - this
    just tells Swiggy 'a new app exists' and gets back a client_id."""
    resp = httpx.post(
        f"{BASE}/auth/register",
        json={
            "redirect_uris": [REDIRECT_URI],
            "client_name": "spread-dev",
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    client_id = resp.json()["client_id"]
    print(f"Registered as client_id={client_id}")
    return client_id


def authenticate() -> TokenSet:
    """Full flow: register -> browser login -> token exchange."""
    client_id = register_client()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    auth_url = f"{BASE}/auth/authorize?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "scope": SCOPE,
    })

    print("\nOpening your browser to log in with your Swiggy account (phone + OTP)...")
    print("If it doesn't open automatically, visit this URL:\n")
    print(auth_url, "\n")
    webbrowser.open(auth_url)

    result = _wait_for_callback(state)
    if result.error:
        raise RuntimeError(f"Swiggy returned an error: {result.error}")
    if not result.code:
        raise RuntimeError("Timed out waiting for login. Run auth.py again.")
    if result.state != state:
        raise RuntimeError("State mismatch - possible CSRF, aborting. Run auth.py again.")

    print("Got the login code, exchanging it for a token...")
    resp = httpx.post(
        f"{BASE}/auth/token",
        json={
            "grant_type": "authorization_code",
            "code": result.code,
            "code_verifier": verifier,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    tokens = TokenSet(
        access_token=data["access_token"],
        expires_in=data.get("expires_in", 432000),
        scope=data.get("scope", SCOPE),
    )
    tokens.save()
    print(f"\nSaved token to {TOKEN_FILE}")
    print("This is valid for 5 days. Run auth.py again after that.")
    return tokens


if __name__ == "__main__":
    authenticate()