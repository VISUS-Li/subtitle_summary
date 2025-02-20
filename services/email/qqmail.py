import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Dict, Optional


class QQMailService:
    """Service for interacting with QQ Mail via IMAP"""

    def __init__(self, email_address: str, password: str):
        """Initialize QQ Mail service

        Args:
            email_address: QQ email address
            password: App-specific password from QQ Mail settings
        """
        self.email = email_address
        self.password = password
        self.imap_server = "imap.qq.com"
        self.imap_port = 993
        self.connection = None

    def connect(self) -> bool:
        """Establish connection to QQ Mail IMAP server

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.connection.login(self.email, self.password)
            return True
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            return False

    def disconnect(self):
        """Close the IMAP connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass

    def get_mailbox_list(self) -> List[str]:
        """Get list of available mailboxes

        Returns:
            List of mailbox names
        """
        mailboxes = []
        if not self.connection:
            return mailboxes

        try:
            resp, data = self.connection.list()
            if resp == 'OK':
                for item in data:
                    decoded = item.decode()
                    # Extract mailbox name
                    mailbox = decoded.split('"/"')[-1].strip()
                    mailboxes.append(mailbox)
        except Exception as e:
            print(f"Error getting mailboxes: {str(e)}")

        return mailboxes

    def fetch_emails(self, mailbox: str = 'INBOX', limit: int = 10) -> List[Dict]:
        """Fetch emails from specified mailbox

        Args:
            mailbox: Name of mailbox to fetch from
            limit: Maximum number of emails to fetch

        Returns:
            List of email dictionaries containing subject, from, date and body
        """
        emails = []

        if not self.connection:
            return emails

        try:
            # Select mailbox
            self.connection.select(mailbox)

            # Search for all emails
            _, message_numbers = self.connection.search(None, 'ALL')

            # Get list of email IDs
            email_ids = message_numbers[0].split()

            # Process latest emails up to limit
            for email_id in email_ids[-limit:]:
                _, msg_data = self.connection.fetch(email_id, '(RFC822)')
                email_body = msg_data[0][1]

                # Parse email message
                message = email.message_from_bytes(email_body)

                # Extract header info
                subject = self._decode_header(message['subject'])
                from_addr = self._decode_header(message['from'])
                try:
                    date_str = message['date']
                    # Remove (UTC) if present
                    date_str = date_str.replace('(UTC)', '').strip()
                    # Try parsing with timezone
                    date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    try:
                        # Try parsing without timezone if first attempt fails
                        date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S")
                    except ValueError:
                        # If parsing fails, use current datetime as fallback
                        date = datetime.now()

                # Get email body
                body = self._get_email_body(message)

                emails.append({
                    'subject': subject,
                    'from': from_addr,
                    'date': date,
                    'body': body
                })

        except Exception as e:
            print(f"Error fetching emails: {str(e)}")

        return emails

    def _decode_header(self, header: Optional[str]) -> str:
        """Decode email header

        Args:
            header: Email header string to decode

        Returns:
            Decoded header string
        """
        if not header:
            return ""

        try:
            decoded_header = decode_header(header)
            parts = []
            for text, charset in decoded_header:
                if isinstance(text, bytes):
                    text = text.decode(charset or 'utf-8', errors='ignore')
                parts.append(str(text))
            return " ".join(parts)
        except:
            return header

    def _get_email_body(self, message: email.message.Message) -> str:
        """Extract email body from message

        Args:
            message: Email message object

        Returns:
            Email body as text
        """
        body = ""

        if message.is_multipart():
            # If message has multiple parts, get text from each part
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode()
                    except:
                        pass
        else:
            # If message is not multipart, get text directly
            try:
                body = message.get_payload(decode=True).decode()
            except:
                pass

        return body


def main():
    # Initialize service
    email_address = "1183989659@qq.com"
    password = "gcwwoaoscpuviijb"  # Get this from QQ Mail settings

    mail_service = QQMailService(email_address, password)

    # Connect to server
    if mail_service.connect():
        try:
            # Get available mailboxes
            mailboxes = mail_service.get_mailbox_list()
            print("Available mailboxes:", mailboxes)

            # Fetch latest 5 emails from inbox
            emails = mail_service.fetch_emails(mailbox='INBOX', limit=5)

            # Process emails
            for email in emails:
                print("\nSubject:", email['subject'])
                print("From:", email['from'])
                print("Date:", email['date'])
                print("Body preview:", email['body'][:100])

        finally:
            # Always disconnect when done
            mail_service.disconnect()


if __name__ == "__main__":
    main()