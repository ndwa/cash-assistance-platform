import datetime
import textwrap
import uuid

from app_ccf.models import Application, StatusUpdate
from app_ccf.models import VoucherCode, VoucherCodeBatch, VoucherCodeCheckStatus
from shared.test_utils import DEFAULT_CCF_APP_FIELDS

from . import base_test

from . import utils


class ApplicationTests(base_test.CcfBaseTest):

    def setUp(self):
        super().setUp()
        self.fields = DEFAULT_CCF_APP_FIELDS.copy()
        self.application = Application(
            **self.fields,
        )
        self.application.status = Application.ApplicationStatus.NEEDS_REVIEW
        self.application.save()

    def test_save_secondTime_doesNotUpdateSubmittedDate(self):
        old_time = self.application.submitted_date
        self.application.save()
        new_time = self.application.submitted_date
        self.assertEqual(new_time, old_time)

    def test_save_changedStatus_updatesStatusLastModified(self):
        old_time = self.application.status_last_modified
        # Different from original status
        self.application.status = Application.ApplicationStatus.APPROVED
        self.application.save()
        new_time = self.application.status_last_modified
        self.assertGreater(new_time, old_time)

    def test_save_unchangedStatus_doesNotUpdateStatusLastModified(self):
        old_time = self.application.status_last_modified
        # Same as original status
        self.application.status = Application.ApplicationStatus.NEEDS_REVIEW
        self.application.save()
        new_time = self.application.status_last_modified
        self.assertEqual(new_time, old_time)

    def test_bulk_update_status(self):
        StatusUpdate.objects.all().delete()
        apps = [
            Application(**self.fields) for _ in range(100)
        ]
        Application.objects.bulk_create(apps)
        self.assertEqual(0, len(StatusUpdate.objects.all()))

        Application.bulk_update_status(
            apps[:50], Application.ApplicationStatus.NEEDS_REVIEW)
        self.assertEqual(
            Application.ApplicationStatus.NEEDS_REVIEW, apps[49].status)
        self.assertEqual(
            Application.ApplicationStatus.SUBMITTED, apps[50].status)
        self.assertEqual(50, len(StatusUpdate.objects.all()))

        # Update all applications to NEEDS_REVIEW even for those whose status
        # is already NEEDS_REVIEW. Make sure only 50 new StatusUpdate objects
        # were added.
        Application.bulk_update_status(
            apps, Application.ApplicationStatus.NEEDS_REVIEW)
        self.assertEqual(
            Application.ApplicationStatus.NEEDS_REVIEW, apps[50].status)
        self.assertEqual(100, len(StatusUpdate.objects.all()))

    def test_get_full_address(self):
        self.application.addr1 = '111 E 11th St'
        self.application.addr2 = 'APT 1'
        self.application.city = 'New York'
        self.application.state = 'NY'
        self.application.zip_code = '11111'
        expected_full_address = textwrap.dedent("""\
            111 E 11th St
            APT 1
            New York, NY 11111""")
        self.assertEqual(expected_full_address,
                         self.application.get_full_address())

    def test_get_full_address_2ndAddressLineBeingEmpty(self):
        self.application.addr1 = '111 E 11th St'
        self.application.city = 'New York'
        self.application.state = 'NY'
        self.application.zip_code = '11111'
        expected_full_address = textwrap.dedent("""\
            111 E 11th St
            New York, NY 11111""")
        self.assertEqual(expected_full_address,
                         self.application.get_full_address())


class VoucherCodeTests(base_test.CcfBaseTest):

    VALID_CODE = "VALID1234"
    EXPIRED_CODE = "EXPIRED12"
    USED_CODE = "USED12345"
    INVALIDATED_CODE = "INVALID12"

    def setUp(self):
        super().setUp()
        today = datetime.datetime.now(datetime.timezone.utc)
        tomorrow = today + datetime.timedelta(days=1)
        yesterday = today - datetime.timedelta(days=1)

        batch_fields = {
            'num_codes': 1,
            'code_length': 9,
            'base_amount': 400,
            'created': yesterday,
        }

        VoucherCode.objects.create(
            code=self.VALID_CODE,
            added_amount=400,
            batch=VoucherCodeBatch.objects.create(
                **batch_fields,
                expiration_date=tomorrow))
        VoucherCode.objects.create(
            code=self.USED_CODE,
            added_amount=400,
            batch=VoucherCodeBatch.objects.create(
                **batch_fields,
                expiration_date=tomorrow),
            application=Application.objects.create(
               **DEFAULT_CCF_APP_FIELDS))
        VoucherCode.objects.create(
            code=self.EXPIRED_CODE,
            added_amount=400,
            batch=VoucherCodeBatch.objects.create(
                **batch_fields,
                expiration_date=yesterday))
        VoucherCode.objects.create(
            code=self.INVALIDATED_CODE,
            added_amount=400,
            batch=VoucherCodeBatch.objects.create(
                **batch_fields,
                expiration_date=tomorrow),
            is_active=False)

    def test_verify_code_validCode(self):
        self.assertEqual(
            VoucherCode.verify_code(self.VALID_CODE),
            VoucherCodeCheckStatus.SUCCESS)

    def test_verify_code_codeDoesNotExist(self):
        self.assertEqual(
            VoucherCode.verify_code("FAKECODE"),
            VoucherCodeCheckStatus.CODE_NOT_FOUND)

    def test_verify_code_codeAlreadyUsed(self):
        self.assertEqual(
            VoucherCode.verify_code(self.USED_CODE),
            VoucherCodeCheckStatus.CODE_ALREADY_USED)

    def test_verify_code_codeInvalidated(self):
        self.assertEqual(
            VoucherCode.verify_code(self.INVALIDATED_CODE),
            VoucherCodeCheckStatus.CODE_INVALIDATED)

    def test_verify_code_codeExpired(self):
        self.assertEqual(
            VoucherCode.verify_code(self.EXPIRED_CODE),
            VoucherCodeCheckStatus.CODE_EXPIRED)
