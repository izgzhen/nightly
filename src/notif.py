# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import yaml

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from msbase.utils import getenv

master_resource = yaml.safe_load(open(getenv("CONFIG_RESOURCES"), "r"))["master"]

def send_text(s: str):
    message = Mail(
        from_email=master_resource["notif_sender_email"],
        to_emails=master_resource["notif_receiver_email"],
        subject='Notification from Nightly Service',
        html_content=s)
    sg = SendGridAPIClient(master_resource["sendgrid_api_key"])
    response = sg.send(message)
    ok = response.status_code >= 200 and response.status_code < 300
    assert ok, response.body