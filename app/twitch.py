import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.auth import (
    exchange_authorization_code,
    save_tokens,
    validate_access_token,
)
from app.config import (
    TWITCH_CLIENT_ID,
    TWITCH_REDIRECT_URI,
)


SCOPES = [
    "user:read:chat",
    "chat:read",
]

HOST = "localhost"
PORT = 3000


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)

        code = query.get("code", [None])[0]
        state = query.get("state", [None])[0]
        error = query.get("error", [None])[0]

        print()
        print("=" * 60)

        if error:
            print("Twitch authorization failed.")
            print("The authorization provider returned an error.")
            print("=" * 60)

            self.send_response(400)
            self.end_headers()

            self.wfile.write(
                b"Twitch authorization failed. You can close this window."
            )

            return

        if not code:
            print("No authorization code received.")
            print("=" * 60)

            self.send_response(400)
            self.end_headers()

            self.wfile.write(
                b"No authorization code received."
            )

            return

        print("Twitch authorization successful!")
        print()
        print("Authorization code received.")
        print("=" * 60)

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(
            b"""
            <html>
                <head>
                    <title>COD Live Code Monitor</title>
                </head>
                <body>
                    <h1>Twitch authorization successful.</h1>
                    <p>You can close this browser window.</p>
                </body>
            </html>
            """
        )

        self.server.authorization_code = code
        self.server.received_state = state

    def log_message(self, format, *args):
        return


def build_authorization_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": TWITCH_CLIENT_ID,
        "redirect_uri": TWITCH_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
    }

    return (
        "https://id.twitch.tv/oauth2/authorize?"
        + urllib.parse.urlencode(params)
    )


def main():
    state = secrets.token_urlsafe(32)

    server = HTTPServer(
        (HOST, PORT),
        OAuthCallbackHandler,
    )

    server.authorization_code = None
    server.received_state = None

    authorization_url = build_authorization_url(state)

    print()
    print("=" * 60)
    print("COD Live Code Monitor - Twitch Authentication")
    print("=" * 60)
    print()
    print("Starting local OAuth callback server...")
    print(f"Listening on http://{HOST}:{PORT}")
    print()
    print("Opening Twitch authorization page...")
    print()

    webbrowser.open(authorization_url)

    while server.authorization_code is None:
        server.handle_request()

    if server.received_state != state:
        print()
        print("ERROR: OAuth state mismatch.")
        print("The authorization response was rejected.")
        print()

        server.server_close()
        return

    print()
    print("OAuth state verified.")
    print("Authorization code received successfully.")
    print()
    print("Exchanging authorization code for Twitch tokens...")

    try:
        tokens = exchange_authorization_code(
            server.authorization_code
        )
    except Exception:
        print()
        print("ERROR: Token exchange failed.")
        print("Exception details omitted for security.")

        server.server_close()
        return

    print("Token exchange successful.")

    save_tokens(tokens)

    print()
    print("Validating access token...")

    try:
        validation = validate_access_token(
            tokens["access_token"]
        )
    except Exception:
        print()
        print("ERROR: Token validation failed.")
        print("Exception details omitted for security.")

        server.server_close()
        return

    tokens["user_id"] = validation["user_id"]
    tokens["login"] = validation["login"]
    tokens["scopes"] = validation["scopes"]


    save_tokens(tokens)

    print()
    print("=" * 60)
    print("TWITCH AUTHENTICATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Twitch username : {validation['login']}")
    print(f"Twitch user ID  : {validation['user_id']}")
    print(f"Scopes          : {validation['scopes']}")
    print(f"Expires in      : {validation['expires_in']} seconds")
    print()
    print("Access token validated successfully.")
    print("Refresh token has been stored locally.")
    print("=" * 60)

    server.server_close()


if __name__ == "__main__":
    main()