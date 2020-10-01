import datetime

from app_ccf.common import (
    auto_update_application_statuses,
    update_application_statuses
)
from app_ccf.config import CONFIG
from app_ccf.models import Application, VoucherCode, VoucherCodeBatch, PreapprovedAddress
from shared.test_utils import DEFAULT_CCF_APP_FIELDS

from parameterized import parameterized

from . import base_test


class AutoUpdateAppStatusTests(base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.ADDRESS_FIELDS = {
            'addr1': '45 BROADWAY',
            'city': 'NY',
            'state': 'New York',
            'zip_code': '10006',
            'usps_verified': True,
        }
        self.OTHER_REQUIRED_FIELDS = DEFAULT_CCF_APP_FIELDS.copy()
        for address_field in self.ADDRESS_FIELDS:
            del self.OTHER_REQUIRED_FIELDS[address_field]
        del self.OTHER_REQUIRED_FIELDS['first_name']
        del self.OTHER_REQUIRED_FIELDS['last_name']
        del self.OTHER_REQUIRED_FIELDS['phone_number']

    def test_auto_update_application_statuses_fourDupAddresses_marksNewDupsForReview(
            self):
        # 4 apps with the same address, 1 already approved
        app1 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="A",
            last_name="A",
            addr2="APT A1",
            phone_number='+12222222222',
            status=Application.ApplicationStatus.APPROVED)
        app2 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="B",
            last_name="B",
            addr2="APT B2",
            phone_number='+13333333333',
            status=Application.ApplicationStatus.SUBMITTED)
        app3 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="C",
            last_name="C",
            addr2="APT C3",
            phone_number='+14444444444',
            status=Application.ApplicationStatus.SUBMITTED)
        app4 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="D",
            last_name="D",
            addr2="APT D4",
            phone_number='+15555555555',
            status=Application.ApplicationStatus.SUBMITTED)

        auto_update_application_statuses()

        # This one was already approved so it should stay the same
        app1.refresh_from_db()
        self.assertEqual(
            app1.status,
            Application.ApplicationStatus.APPROVED)

        app2.refresh_from_db()
        self.assertEqual(
            app2.status,
            Application.ApplicationStatus.NEEDS_REVIEW)

        app3.refresh_from_db()
        self.assertEqual(
            app3.status,
            Application.ApplicationStatus.NEEDS_REVIEW)
        self.assertEqual(app3.note, 'duplicate address')

        app4.refresh_from_db()
        self.assertEqual(
            app4.status,
            Application.ApplicationStatus.NEEDS_REVIEW)
        self.assertEqual(app4.note, 'duplicate address')

    def test_auto_update_application_statuses_fourDupAddressesPreapproved_marksNewDupsForReview(
            self):
        PreapprovedAddress.objects.create(
            addr1=self.ADDRESS_FIELDS["addr1"],
            city=self.ADDRESS_FIELDS["city"],
            state=self.ADDRESS_FIELDS["state"],
            zip_code=self.ADDRESS_FIELDS["zip_code"],
            note="Test Preapproved Address")

        # 4 apps with the same address, 1 already approved
        app1 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="A",
            last_name="A",
            addr2="APT A1",
            phone_number='+12222222222',
            status=Application.ApplicationStatus.APPROVED)
        app2 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="B",
            last_name="B",
            addr2="APT B2",
            phone_number='+13333333333',
            status=Application.ApplicationStatus.SUBMITTED)
        app3 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="C",
            last_name="C",
            addr2="APT C3",
            phone_number='+14444444444',
            status=Application.ApplicationStatus.SUBMITTED)
        app4 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="D",
            last_name="D",
            addr2="APT D4",
            phone_number='+15555555555',
            status=Application.ApplicationStatus.SUBMITTED)

        auto_update_application_statuses()

        app1.refresh_from_db()
        self.assertEqual(
            app1.status,
            Application.ApplicationStatus.APPROVED)

        app2.refresh_from_db()
        self.assertEqual(
            app2.status,
            Application.ApplicationStatus.APPROVED)

        app3.refresh_from_db()
        self.assertEqual(
            app3.status,
            Application.ApplicationStatus.APPROVED)

        app4.refresh_from_db()
        self.assertEqual(
            app4.status,
            Application.ApplicationStatus.APPROVED)

    def test_auto_update_application_statuses_threeDupAddresses_marksDupsApproved(
            self):
        # 3 apps with the same address
        app1 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="A",
            last_name="A",
            phone_number='+12222222222',
            status=Application.ApplicationStatus.SUBMITTED)
        app2 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="B",
            last_name="B",
            phone_number='+13333333333',
            status=Application.ApplicationStatus.SUBMITTED)
        app3 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            **self.ADDRESS_FIELDS,
            first_name="C",
            last_name="C",
            phone_number='+14444444444',
            status=Application.ApplicationStatus.SUBMITTED)

        auto_update_application_statuses()

        # This one was already approved so it should stay the same
        app1.refresh_from_db()
        self.assertEqual(
            app1.status,
            Application.ApplicationStatus.APPROVED)

        app2.refresh_from_db()
        self.assertEqual(
            app2.status,
            Application.ApplicationStatus.APPROVED)

        app3.refresh_from_db()
        self.assertEqual(
            app3.status,
            Application.ApplicationStatus.APPROVED)

    def test_auto_update_application_statuses_dupNamePhone_marksDupsForReview(
            self):
        self.trigger_text_messages_mock.reset_mock()
        app1 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            addr1='45 BROADWAY',
            city='NY',
            zip_code='10011',
            state='NY',
            first_name="FirstName",
            last_name="LastName",
            phone_number='+12222222222',
            status=Application.ApplicationStatus.SUBMITTED)
        app2 = Application.objects.create(
            **self.OTHER_REQUIRED_FIELDS,
            addr1='25 STATE ST',
            city='NY',
            zip_code='10011',
            state='CA',
            first_name="firstName",
            last_name="lastName",
            phone_number='+12222222222',
            status=Application.ApplicationStatus.SUBMITTED)

        auto_update_application_statuses()

        app1.refresh_from_db()
        self.assertEqual(
            app1.status,
            Application.ApplicationStatus.REJECTED)
        self.assertEqual(app1.note, 'duplicate first/last/phone')

        app2.refresh_from_db()
        self.assertEqual(
            app2.status,
            Application.ApplicationStatus.REJECTED)
        self.assertEqual(app2.note, 'duplicate first/last/phone')

        self.assertEqual(
            1,
            self.trigger_text_messages_mock.call_count)
        self.assertEqual(
            {'+12222222222'},
            self.trigger_text_messages_mock.call_args_list[0][0][0])


class UpdateAppStatusTests(base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        fields = DEFAULT_CCF_APP_FIELDS.copy()

        self.models = [
            Application.objects.create(
                **fields,
                status=Application.ApplicationStatus.APPROVED),
            Application.objects.create(
                **fields,
                status=Application.ApplicationStatus.NEEDS_REVIEW),
            Application.objects.create(
                **fields,
                status=Application.ApplicationStatus.NEEDS_REVIEW),
            Application.objects.create(
                **fields,
                status=Application.ApplicationStatus.REJECTED),
            Application.objects.create(
                **fields,
                status=Application.ApplicationStatus.SENT_FOR_PAYMENT),
        ]

    @parameterized.expand([
        (Application.ApplicationStatus.APPROVED, ),
        (Application.ApplicationStatus.NEEDS_REVIEW, ),
        (Application.ApplicationStatus.REJECTED, ),
        (Application.ApplicationStatus.SENT_FOR_PAYMENT, ),
    ])
    def test_update_application_statuses(self, status):
        id_of_applications_to_update = [
            self.models[2].application_id,
            self.models[3].application_id,
            self.models[4].application_id,
        ]

        # Act
        update_application_statuses(id_of_applications_to_update, status)

        for m in self.models:
            m.refresh_from_db()

        # Verify updated models
        self.assertEqual(status, self.models[2].status)
        self.assertEqual(status, self.models[3].status)
        self.assertEqual(status, self.models[4].status)
        # Verify untouched models
        self.assertEqual(Application.ApplicationStatus.APPROVED,
                         self.models[0].status)
        self.assertEqual(
            Application.ApplicationStatus.NEEDS_REVIEW, self.models[1].status)

    @parameterized.expand([
        (Application.Language.EN,),
        (Application.Language.EN,),
        (Application.Language.ES,),
    ])
    def test_update_application_withTextMessaging(
            self, language):
        self.trigger_text_messages_mock.reset_mock()

        self.models[0].language = language
        self.models[0].save()
        self.models[1].language = language
        self.models[1].phone_number = '+16666666666'
        self.models[1].save()

        update_application_statuses(
            (
                self.models[0].application_id,
                self.models[1].application_id),
            Application.ApplicationStatus.PAYMENT_CONFIRMED)

        self.assertEqual(
            1,
            self.trigger_text_messages_mock.call_count)
        self.assertEqual(
            {'+15555555555', '+16666666666'}, self.trigger_text_messages_mock.call_args[0][0])