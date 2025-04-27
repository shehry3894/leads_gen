import base64
import httplib2shim
import os

from apiclient import discovery
from email.mime.text import MIMEText
from oauth2client.file import Storage
from typing import Dict

from utils.printing_and_logging import print_and_log

print('email_utils_#__os.getcwd(): ', os.getcwd())

curr_dir_path = os.path.dirname(os.path.abspath(__file__))
GMAIL_SECRET_PATH = os.path.join(curr_dir_path, '..', 'inputs', 'gmail-secret.json')
print(f'GMAIL_SECRET_PATH: {GMAIL_SECRET_PATH}')


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    store = Storage(GMAIL_SECRET_PATH)
    credentials = store.get()
    return credentials


http = get_credentials().authorize(httplib2shim.Http())
SERVICE = discovery.build('gmail', 'v1', http=http)


def send_email(from_email: str, to_email: str, subject: str, body: Dict) -> None:
    print_and_log(f'EMAIL_UTILS_#_send_email. to_email: {to_email}')

    msg = create_message(from_email, to_email, subject, body)
    message = (SERVICE.users().messages().send(userId='me', body=msg)
               .execute())

    print_and_log("Email {} has been sent successfully to {}.".format(message['id'], to_email))


def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': (base64.urlsafe_b64encode(message.as_bytes()).decode())}
