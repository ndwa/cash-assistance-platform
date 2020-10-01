
from django.test import TestCase
from app_ccf.twilio import twilio_client
import mock

import time


class CcfBaseTest(TestCase):

    def setUp(self):
        super().setUp()
        if not hasattr(twilio_client.trigger_text_messages, 'mock'):
            mock.patch.object(twilio_client,
                              'trigger_text_messages', autospec=True).start()
        self.trigger_text_messages_mock = twilio_client.trigger_text_messages

        if not hasattr(time.sleep, 'mock'):
            mock.patch.object(time, 'sleep', autospect=True).start()
