#!/usr/bin/env python3
"""
Download all attachments from emails sent by periodicals@ukragroconsult.org
Uses Google Gmail API to search and download attachments automatically.
"""

import os
import base64
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UkrAgroAttachmentDownloader:
    """Download all attachments from periodicals@ukragroconsult.org"""

    def __init__(self):
        self.service = None
        self.download_folder = Path(__file__).parent / "market_data" / "ukragro_downloads"
        self.download_folder.mkdir(parents=True, exist_ok=True)

        # Gmail API scopes
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]

        # Target sender
        self.sender_email = "periodicals@ukragroconsult.org"

        # Statistics
        self.stats = {
            'emails_found': 0,
            'files_downloaded': 0,
            'total_size': 0,
            'errors': []
        }

    def authenticate_gmail(self):
        """Authenticate with Gmail API using OAuth2"""
        creds = None
        token_file = Path(__file__).parent / 'gmail_token.json'

        # Check if we can use existing OAuth credentials from the MCP tool
        mcp_token_path = Path.home() / '.config' / 'gmail-mcp' / 'token.json'
        if mcp_token_path.exists():
            logger.info("Found existing Gmail MCP token, attempting to use it...")
            try:
                with open(mcp_token_path, 'r') as f:
                    token_data = json.load(f)

                # Create credentials from the existing token
                creds = Credentials(
                    token=token_data.get('access_token'),
                    refresh_token=token_data.get('refresh_token'),
                    id_token=token_data.get('id_token'),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=token_data.get('client_id'),
                    client_secret=token_data.get('client_secret'),
                    scopes=self.scopes
                )

                # Test the credentials
                if creds.expired:
                    creds.refresh(Request())

            except Exception as e:
                logger.warning(f"Failed to use existing MCP token: {e}")
                creds = None

        # Load existing credentials if available
        if not creds and token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), self.scopes)
                logger.info("Loaded existing credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load existing credentials: {e}")

        # If no valid credentials, start OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                logger.info("Starting new OAuth flow...")

                # Note: In production, you should use your own OAuth credentials
                # Download credentials.json from Google Cloud Console and place it here
                print("❌ OAuth credentials required. Please:")
                print("1. Go to Google Cloud Console")
                print("2. Create OAuth 2.0 credentials")
                print("3. Download as credentials.json")
                print("4. Place in this directory")
                return False

                flow = Flow.from_client_config(client_config, self.scopes)
                flow.redirect_uri = 'http://localhost:3000/oauth2callback'

                # Get authorization URL
                auth_url, _ = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true',
                    prompt='consent'
                )

                print(f"\n🔐 Please visit this URL to authorize access:")
                print(f"{auth_url}\n")

                # Get authorization code from user
                try:
                    auth_code = input('Enter the authorization code from the browser: ').strip()
                except EOFError:
                    print("\n❌ No authorization code provided. Please run the script interactively.")
                    return False

                # Exchange authorization code for credentials
                try:
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    logger.info("Successfully obtained new credentials")
                except Exception as e:
                    logger.error(f"Failed to fetch token: {e}")
                    return False

        # Save credentials for future use
        if creds:
            try:
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Saved credentials to {token_file}")
            except Exception as e:
                logger.warning(f"Failed to save credentials: {e}")

        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("✅ Successfully authenticated with Gmail API")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to build Gmail service: {e}")
            return False

    def search_emails_from_sender(self, days_back=365):
        """Search for emails from the specific sender"""
        if not self.service:
            logger.error("Gmail service not initialized")
            return []

        # Build search query
        since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
        query = f"from:{self.sender_email} has:attachment after:{since_date}"

        logger.info(f"🔍 Searching for emails from {self.sender_email} with attachments...")
        logger.info(f"📅 Date range: {since_date} to today")
        logger.info(f"🔎 Query: {query}")

        try:
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500  # Increase limit to get more results
            ).execute()

            messages = results.get('messages', [])
            self.stats['emails_found'] = len(messages)

            logger.info(f"📧 Found {len(messages)} emails from {self.sender_email}")

            return messages

        except HttpError as error:
            logger.error(f"❌ Gmail API error: {error}")
            self.stats['errors'].append(f"Search error: {error}")
            return []

    def get_message_details(self, message_id):
        """Get full message details including attachments"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return message
        except HttpError as error:
            logger.error(f"❌ Error getting message {message_id}: {error}")
            self.stats['errors'].append(f"Message fetch error: {error}")
            return None

    def download_attachments(self, message):
        """Download all attachments from a message"""
        if not message:
            return []

        downloaded_files = []
        headers = message['payload'].get('headers', [])

        # Get message info
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        date_header = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        message_date = self._parse_date(date_header)

        logger.info(f"📧 Processing: {subject[:50]}{'...' if len(subject) > 50 else ''}")

        # Recursive function to process message parts
        def process_parts(parts, path_prefix=""):
            nonlocal downloaded_files

            for part in parts:
                # Check if this part has an attachment
                if 'body' in part and 'attachmentId' in part['body']:
                    filename = part.get('filename', '')

                    if filename:  # Download any file with a filename
                        logger.info(f"📎 Found attachment: {filename}")

                        try:
                            # Get attachment data
                            attachment = self.service.users().messages().attachments().get(
                                userId='me',
                                messageId=message['id'],
                                id=part['body']['attachmentId']
                            ).execute()

                            # Decode attachment data
                            data = base64.urlsafe_b64decode(attachment['data'])

                            # Create safe filename with date prefix
                            if message_date:
                                date_prefix = message_date.strftime('%Y%m%d')
                            else:
                                date_prefix = datetime.now().strftime('%Y%m%d')

                            # Clean filename and add prefix
                            safe_filename = self._clean_filename(filename)
                            final_filename = f"{date_prefix}_{safe_filename}"

                            # Handle duplicates
                            counter = 1
                            original_final_filename = final_filename
                            while (self.download_folder / final_filename).exists():
                                name, ext = os.path.splitext(original_final_filename)
                                final_filename = f"{name}_{counter:02d}{ext}"
                                counter += 1

                            # Save file
                            file_path = self.download_folder / final_filename
                            with open(file_path, 'wb') as f:
                                f.write(data)

                            # Update statistics
                            self.stats['files_downloaded'] += 1
                            self.stats['total_size'] += len(data)

                            file_info = {
                                'filename': final_filename,
                                'original_filename': filename,
                                'path': str(file_path),
                                'subject': subject,
                                'date': date_header,
                                'size': len(data),
                                'message_id': message['id']
                            }
                            downloaded_files.append(file_info)

                            logger.info(f"✅ Downloaded: {final_filename} ({self._format_size(len(data))})")

                        except Exception as e:
                            error_msg = f"Error downloading {filename}: {e}"
                            logger.error(f"❌ {error_msg}")
                            self.stats['errors'].append(error_msg)

                # Process nested parts (for multipart messages)
                elif 'parts' in part:
                    process_parts(part['parts'], path_prefix)

        # Start processing from payload
        payload = message.get('payload', {})
        if 'parts' in payload:
            process_parts(payload['parts'])
        elif payload.get('filename'):  # Single attachment message
            process_parts([payload])

        return downloaded_files

    def _parse_date(self, date_str):
        """Parse email date string"""
        if not date_str:
            return None

        try:
            # Try to parse common email date formats
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return None

    def _clean_filename(self, filename):
        """Clean filename for safe storage"""
        # Replace problematic characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        cleaned = ""

        for char in filename:
            if char in safe_chars:
                cleaned += char
            elif char in " ":
                cleaned += "_"
            else:
                cleaned += "_"

        return cleaned[:100]  # Limit length

    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def run_download(self, days_back=365):
        """Main function to download all attachments"""
        logger.info(f"🚀 Starting download from {self.sender_email}")

        # Authenticate
        if not self.authenticate_gmail():
            logger.error("❌ Authentication failed")
            return False

        # Search for emails
        messages = self.search_emails_from_sender(days_back)
        if not messages:
            logger.info("ℹ️ No emails found from this sender")
            return True

        # Download attachments from each email
        logger.info(f"📥 Processing {len(messages)} emails...")

        for i, message in enumerate(messages, 1):
            logger.info(f"📧 Processing email {i}/{len(messages)} (ID: {message['id']})")

            # Get full message details
            full_message = self.get_message_details(message['id'])
            if not full_message:
                continue

            # Download attachments
            downloaded = self.download_attachments(full_message)

            # Small delay to avoid rate limiting
            if i % 10 == 0:
                import time
                time.sleep(1)

        # Print summary
        self._print_summary()
        return True

    def _print_summary(self):
        """Print download summary"""
        logger.info("=" * 60)
        logger.info("📊 DOWNLOAD SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📧 Emails processed: {self.stats['emails_found']}")
        logger.info(f"📎 Files downloaded: {self.stats['files_downloaded']}")
        logger.info(f"💾 Total size: {self._format_size(self.stats['total_size'])}")
        logger.info(f"📁 Download folder: {self.download_folder}")

        if self.stats['errors']:
            logger.info(f"⚠️ Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                logger.info(f"   - {error}")
            if len(self.stats['errors']) > 5:
                logger.info(f"   ... and {len(self.stats['errors']) - 5} more errors")

        logger.info("=" * 60)

        if self.stats['files_downloaded'] > 0:
            print(f"\n✅ SUCCESS! Downloaded {self.stats['files_downloaded']} files")
            print(f"📁 Check files in: {self.download_folder}")
            print(f"🔄 You can now upload these to the Market Intelligence tab")
        else:
            print(f"\nℹ️ No attachments found from {self.sender_email}")

def main():
    """Main entry point"""
    print("📧 UkrAgroConsult Attachment Downloader")
    print("=" * 50)
    print(f"Target sender: periodicals@ukragroconsult.org")
    print(f"Will download ALL attachments from this sender")
    print()

    # Default to 365 days (can be modified if needed)
    days = 365
    print(f"🔍 Searching last {days} days for emails with attachments...")
    print()

    # Create downloader and run
    downloader = UkrAgroAttachmentDownloader()
    success = downloader.run_download(days_back=days)

    if success:
        print(f"\n🎯 Next steps:")
        print(f"1. Check downloaded files in: {downloader.download_folder}")
        print(f"2. Start the DARALEX app: streamlit run app.py")
        print(f"3. Go to '📊 Market Intel' tab")
        print(f"4. Upload Excel files using the upload feature")
    else:
        print("\n❌ Download process failed. Check the logs for details.")

if __name__ == "__main__":
    main()