from app_ccf.twilio import twilio_client
from shared.utils import activate_language

from app_ccf import text_messages
from enum import Enum
from collections import Iterable
from app_ccf.config import CONFIG


class TextType(Enum):
    SUBMISSION = 1
    PAYMENT_CONFIRMED = 2
    REJECTION = 3


def send_text(applications, text_type):
    """Send text for one or multiple applications.

    Args:
        applications: Application object or an iterable of applications
    """
    if not isinstance(applications, Iterable):
        applications = (applications,)

    if text_type == TextType.SUBMISSION:
        if len(applications) > 1:
            raise ValueError(
                'We only support sending text one by one on application submission.')
        text = text_messages.get_submission_message(applications[0])
        twilio_client.trigger_text_messages(
            {applications[0].phone_number}, text)
        return

    for language in CONFIG['languages']:
        lang_applications = [a for a in applications if a.language == language]
        if not lang_applications:
            continue
        with activate_language(language):
            if text_type == TextType.PAYMENT_CONFIRMED:
                text = text_messages.get_payment_confirmed_message()
            elif text_type == TextType.REJECTION:
                text = text_messages.get_rejection_message()
            else:
                raise ValueError(
                    'text_type ({}) has to be a TextType Enum'.format(text_type))
            twilio_client.trigger_text_messages(
                {a.phone_number for a in lang_applications}, text)
