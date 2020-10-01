from django.db import models
from django.contrib.sessions.backends.db import SessionStore
from parameterized import parameterized, parameterized_class
from app_ccf.models import VoucherCode, VoucherCodeBatch, Application
from .common import ApplicationSession
from shared.test_utils import DEFAULT_CCF_APP_FIELDS

from . import base_test

import datetime
import uuid

LANGUAGES = ({'language': 'en', }, {'language': 'es'},)


def create_old_application_model():
    class OldApplication(models.Model):
        old_field = models.CharField()
        household_size = models.IntegerField()
        application_id = models.UUIDField(
            primary_key=True, default=uuid.uuid4)
    fields = {
        'household_size': 3,
        'old_field': 'old data',
    }
    return OldApplication(**fields)


class BaseViewTestCaseMixin(object):

    def test_get(self):
        if not hasattr(self, 'language'):
            # For some reason this test case is also triggered without the
            # parameterized settings, probably due to some Python inheritance
            # magic.
            return

        full_path = '/' + self.language + self.path
        response = self.client.get(full_path)
        self.assertEqual(response.status_code, 200)

    def test_get_outdatedApplicationSession(self):
        if not hasattr(self, 'language'):
            # For some reason this test case is also triggered without the
            # parameterized settings, probably due to some Python inheritance
            # magic.
            return

        # Mimic the scenario of the session storing an old application model.
        application_session = ApplicationSession.load(None)
        application_session.model = create_old_application_model()
        session = SessionStore(session_key=self.client.session.session_key)
        session['application_session'] = ApplicationSession.serialize(
            application_session)
        session.save()

        full_path = '/' + self.language + self.path
        response = self.client.get(full_path)
        self.assertEqual(response.status_code, 200)


class LanguageViewTests(base_test.CcfBaseTest):

    def test_get(self):
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)


@parameterized_class(LANGUAGES)
class WelcomeViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/welcome'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path)
        self.assertRedirects(response, '/' + self.language + '/requirements')

    def test_post_outdatedApplicationSession(self):
        # Mimic the scenario of the session storing an old application model.
        application_session = ApplicationSession.load(None)
        application_session.model = create_old_application_model()
        session = SessionStore(session_key=self.client.session.session_key)
        session['application_session'] = ApplicationSession.serialize(
            application_session)
        session.save()

        full_path = '/' + self.language + self.path
        response = self.client.post(full_path)
        self.assertRedirects(response, '/' + self.language + '/requirements')
        # Check that the updated application model doesn't have the old field.
        session = SessionStore(session_key=self.client.session.session_key)
        self.assertFalse(hasattr(ApplicationSession.load(session['application_session']).model,
                                 'old_field'))


@parameterized_class(LANGUAGES)
class RequirementsViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/requirements'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path, {'qualified': True})
        self.assertRedirects(response, '/' + self.language + '/accesscode')

    def test_post_notQualified(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path, {'qualified': False})
        self.assertRedirects(response, '/' + self.language + '/do-not-qualify')


@parameterized_class(LANGUAGES)
class VoucherCodeViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/accesscode'

        today = datetime.datetime.now(datetime.timezone.utc)
        tomorrow = today + datetime.timedelta(days=1)
        VoucherCode.objects.create(
            code='aaabbbccc',
            added_amount=0,
            batch=VoucherCodeBatch.objects.create(
                num_codes=1,
                code_length=9,
                base_amount=400,
                created=today,
                expiration_date=tomorrow))

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {'voucher_input': 'aaa-bbb-ccc'})
        self.assertRedirects(
            response, '/' + self.language + '/profile')

    def test_post_incorrectVoucherCode(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {'voucher_input': 'xxx-yyy-zzz'})
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(response.status_code, 200)


@parameterized_class(LANGUAGES)
class DisclosureViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/alia-disclosure'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path)
        self.assertRedirects(
            response, '/' + self.language + '/terms-and-conditions')


@parameterized_class(LANGUAGES)
class ProfileViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/profile'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path, {
            'first_name': 'Tom',
            'last_name': 'Lee',
            'age_range': '18-29',
            'type_of_work': 'Nanny',
            'ethnicity': 'Asian',
        })
        self.assertRedirects(
            response, '/' + self.language + '/additional-info')

    def test_post_incorrect_first_name_field(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {
                'first_name': 'mail@mailbox.com',
                'last_name': 'Lee',
                'age_range': '18-29',
                'type_of_work': 'Nanny',
                'ethnicity': 'Asian',
            })
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(response.status_code, 200)

    def test_post_incorrect_first_name_field(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {
                'first_name': 'Tom',
                'last_name': 'mail@mailbox.com',
                'age_range': '18-29',
                'type_of_work': 'Nanny',
                'ethnicity': 'Asian',
            })
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(response.status_code, 200)


@parameterized_class(LANGUAGES)
class HouseholdViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/additional-info'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path, {
            'household_size': 2,
            'household_income': '<20k',
        })
        self.assertRedirects(
            response, '/' + self.language + '/mailing-address')


@parameterized_class(LANGUAGES)
class AddressViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/mailing-address'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path, {
            'addr1': '100 E 100th st',
            'addr2': 'APT 1A',
            'city': 'New York',
            'state': 'NY',
            'zip_code': '10000',
            'usps_standardized': True,
            'usps_verified': True,
        })
        self.assertRedirects(
            response, '/' + self.language + '/usps-cannot-verify')

    def test_post_incorrect_addr1_field(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {
                'addr1': 'mail@mailbox.com',
                'addr2': 'APT 1A',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10000',
                'usps_standardized': True,
                'usps_verified': True,
            })
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(response.status_code, 200)

    def test_post_incorrect_addr2_field(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {
                'addr1': '100 E 100th st',
                'addr2': 'mail@mailbox.com',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10000',
                'usps_standardized': True,
                'usps_verified': True,
            })
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(response.status_code, 200)


@parameterized_class(LANGUAGES)
class ContactViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/contact-info'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(
            full_path, {'phone_digits': '555-555-5555'})
        self.assertRedirects(response, '/' + self.language +
                             '/alia-disclosure')


@parameterized_class(LANGUAGES)
class SignatureViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/terms-and-conditions'

    def test_post(self):
        full_path = '/' + self.language + self.path
        response = self.client.post(full_path, {
            'tos': True,
            'signature': 'L L'
        })
        self.assertRedirects(response, '/' + self.language + '/review')


@parameterized_class(LANGUAGES)
class ReviewViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/review'

        # Create a valid voucher code
        today = datetime.datetime.now(datetime.timezone.utc)
        tomorrow = today + datetime.timedelta(days=1)
        self.voucher_code = VoucherCode.objects.create(
            code='aaabbbccc',
            added_amount=0,
            batch=VoucherCodeBatch.objects.create(
                num_codes=1,
                code_length=9,
                base_amount=400,
                created=today,
                expiration_date=tomorrow))

        # Create a valid application session
        fields = DEFAULT_CCF_APP_FIELDS.copy()
        fields.update({
            'vouchercode_str': 'aaabbbccc',
            'phone_number': '+15555555555',
        })

        application_session = ApplicationSession.load(None)
        application_session.model = Application(**fields)
        session = SessionStore(session_key=self.client.session.session_key)
        session['application_session'] = ApplicationSession.serialize(
            application_session)
        session.save()

    def test_post(self):
        self.trigger_text_messages_mock.reset_mock()
        full_path = '/' + self.language + self.path

        response = self.client.post(full_path)

        self.assertRedirects(response, '/' + self.language + '/success')
        self.assertEqual(1, self.trigger_text_messages_mock.call_count)
        self.assertEqual(
            {'+15555555555'}, self.trigger_text_messages_mock.call_args[0][0])

    def test_post_incorrectVoucherCode(self):
        self.trigger_text_messages_mock.reset_mock()
        # Invalidate the voucher code here
        self.voucher_code.is_active = False
        self.voucher_code.save()

        full_path = '/' + self.language + self.path
        response = self.client.post(full_path)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        if self.language == 'en':
            self.assertIn('Invalid code. Access codes must',
                          form.errors['__all__'][0])
        elif self.language == 'es':
            self.assertIn(
                'Código inválido. Los códigos de acceso', form.errors['__all__'][0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(Application.objects.all()))
        self.assertEqual(0, self.trigger_text_messages_mock.call_count)

    def test_post_missingRequiredFields(self):
        self.trigger_text_messages_mock.reset_mock()

        fields = DEFAULT_CCF_APP_FIELDS.copy()
        fields.update({
            'vouchercode_str': 'aaabbbccc',
        })
        # Remove household_size field from the application session
        del fields['household_size']
        # Remove required 'first_name' field
        del fields['first_name']

        application_session = ApplicationSession.load(None)
        application_session.model = Application(**fields)
        session = SessionStore(session_key=self.client.session.session_key)
        session['application_session'] = ApplicationSession.serialize(
            application_session)
        session.save()

        full_path = '/' + self.language + self.path
        response = self.client.post(full_path)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(Application.objects.all()))
        self.assertEqual(0, self.trigger_text_messages_mock.call_count)


@parameterized_class(LANGUAGES)
class ConfirmationViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/success'


@parameterized_class(LANGUAGES)
class NoQualifyViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/do-not-qualify'


@parameterized_class(LANGUAGES)
class NoVoucherCodeViewTests(BaseViewTestCaseMixin, base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.path = '/no-code'
