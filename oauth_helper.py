#!/usr/bin/env python3
"""
OAuth Helper for Gmail API Authentication
This script helps set up Gmail API authentication for downloading attachments.
"""

import webbrowser
import http.server
import socketserver
import urllib.parse
import json
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    """Handle OAuth callback"""

    def do_GET(self):
        if self.path.startswith('/oauth2callback'):
            # Parse the authorization code from the callback
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)

            if 'code' in params:
                self.server.auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                <h2>✅ Authorization successful!</h2>
                <p>You can close this tab and return to the terminal.</p>
                <script>setTimeout(() => window.close(), 3000);</script>
                </body>
                </html>
                ''')
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                <h2>❌ Authorization failed!</h2>
                <p>No authorization code received.</p>
                </body>
                </html>
                ''')
        else:
            super().do_GET()

    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass

def setup_gmail_auth():
    """Set up Gmail API authentication"""

    print("🔐 Gmail API Authentication Setup")
    print("=" * 40)

    # Note: You need to provide your own OAuth credentials
    print("❌ OAuth credentials required. Please:")
    print("1. Go to Google Cloud Console (console.cloud.google.com)")
    print("2. Create a new project or select existing")
    print("3. Enable Gmail API")
    print("4. Create OAuth 2.0 credentials")
    print("5. Download credentials.json")
    print("6. Place in this directory")
    print()
    print("💡 For testing, you can use the manual download method:")
    print("   python simple_gmail_download.py")
    return False

    scopes = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    # Create flow
    flow = Flow.from_client_config(client_config, scopes)
    flow.redirect_uri = 'http://localhost:3000/oauth2callback'

    # Start local server for callback
    port = 3000
    with socketserver.TCPServer(("", port), OAuthHandler) as httpd:
        httpd.auth_code = None

        # Generate auth URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        print(f"🌐 Opening browser for authorization...")
        print(f"📝 If browser doesn't open, visit: {auth_url}")
        print(f"🔄 Waiting for authorization...")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        httpd.handle_request()

        if httpd.auth_code:
            print("✅ Authorization code received!")

            # Exchange code for credentials
            try:
                flow.fetch_token(code=httpd.auth_code)
                creds = flow.credentials

                # Save credentials
                token_file = Path(__file__).parent / 'gmail_token.json'
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())

                print(f"💾 Credentials saved to: {token_file}")
                return True

            except Exception as e:
                print(f"❌ Error exchanging code for token: {e}")
                return False

        else:
            print("❌ No authorization code received")
            return False

def test_gmail_auth():
    """Test Gmail authentication"""

    token_file = Path(__file__).parent / 'gmail_token.json'

    if not token_file.exists():
        print("❌ No credentials found. Run setup first.")
        return False

    try:
        # Load credentials
        creds = Credentials.from_authorized_user_file(str(token_file))

        # Test with Gmail API
        from googleapiclient.discovery import build

        service = build('gmail', 'v1', credentials=creds)

        # Get profile info
        profile = service.users().getProfile(userId='me').execute()

        print("✅ Gmail API authentication successful!")
        print(f"📧 Email: {profile.get('emailAddress')}")
        print(f"📊 Total messages: {profile.get('messagesTotal')}")

        return True

    except Exception as e:
        print(f"❌ Gmail API test failed: {e}")
        return False

def main():
    """Main function"""

    print("🚀 Gmail API Setup for UkrAgroConsult Downloads")
    print("=" * 50)

    # Check if credentials already exist
    token_file = Path(__file__).parent / 'gmail_token.json'

    if token_file.exists():
        print("🔍 Found existing credentials, testing...")
        if test_gmail_auth():
            print("\n✅ Gmail API is ready!")
            print("🎯 You can now run: python download_from_ukragro_sender.py")
            return

        print("🔄 Existing credentials don't work, setting up new ones...")

    # Set up authentication
    if setup_gmail_auth():
        print("\n🎉 Gmail API authentication setup complete!")
        print("\n🎯 Next steps:")
        print("1. Run: python download_from_ukragro_sender.py")
        print("2. The script will automatically download all attachments")
        print("3. Process files in the Market Intelligence tab")
    else:
        print("\n❌ Authentication setup failed")
        print("💡 Try running the manual download approach instead:")
        print("   python simple_gmail_download.py")

if __name__ == "__main__":
    main()