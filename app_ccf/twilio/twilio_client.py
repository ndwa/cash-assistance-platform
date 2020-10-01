
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
import os
import logging


LOGGER = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_SERVICE_SID = os.environ.get('TWILIO_SERVICE_SID')


def trigger_text_messages(recipients, body):
    to_binding = [
        '{{"binding_type":"sms","address":"{recipient}"}}'.format(
            recipient=recipient
        ) for recipient in recipients
    ]
    LOGGER.info('About to send {} to {}.'.format(body, to_binding))

    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_SERVICE_SID):
        LOGGER.info('Twilio is not configured. Aborting sending the text...')
        return

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        client.notify.services(TWILIO_SERVICE_SID).notifications.create(
            to_binding=to_binding,
            body=body)
    except TwilioRestException as e:
        LOGGER.error(e)
    else:
        LOGGER.info('Successfully sent the text messages.')
