import collections
from datetime import datetime, timezone
import logging
import json
import random
from uuid import UUID

from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from app_ccf import models
from .encoder import ApplicationEncoder
from .fraud_checks import (
    AddressDedupCheck,
    NamePhoneDedupCheck,
)
from .config import CONFIG
from .models import Application, VoucherCode, VoucherCodeAttempt, VoucherCodeCheckStatus
from django.db import transaction
from . import notification, utils


# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class ApplicationSubmissionError(Exception):
    pass


class ApplicationSession():

    def __init__(self, model_dict=None, checks=None):
        if model_dict:
            self.model = Application(**model_dict)
        else:
            self.model = Application()
        self.checks = checks or {
            'qualified': False,
            'vouchercheck': False,
        }

    @staticmethod
    def to_dict(session):
        model_dict = model_to_dict(session.model)
        serialized_session = {
            'model': model_dict,
            'checks': session.checks,
        }
        return serialized_session

    @staticmethod
    def serialize(session):
        return json.dumps(ApplicationSession.to_dict(session),
                          cls=ApplicationEncoder)

    @staticmethod
    def load(serialized):
        if serialized is None:
            return ApplicationSession()
        loaded = json.loads(serialized)
        session = ApplicationSession(
            model_dict=loaded['model'],
            checks=loaded['checks'])
        return session

    def save(self):
        for c in self.checks:
            if not c:
                return
        self.model.save()


def is_voucher_code_valid(
        code,
        ip_address,
        action=VoucherCodeAttempt.Action.VOUCHER_CODE_CHECK):
    """Checks if a given voucher code is valid to redeem.

    For each call to this method, it also writes an entry to VoucherCodeAttempt table for record purpose.

    Args:
        code: A given voucher code.
        ip_address: The IP address of the requester.
        action: A VoucherCodeAttempt.Action.

    Returns:
        A bool of whether the code is valid to redeem.
    """
    status = VoucherCode.verify_code(code)
    attempt_info = dict(code=code, ip_address=ip_address,
                        action=action, status=status)
    LOGGER.debug('#VoucherCodeAttempt: %s', attempt_info)

    VoucherCodeAttempt(**attempt_info).save()
    return status == VoucherCodeCheckStatus.SUCCESS


@transaction.atomic
def submit_application(application, ip_address):
    """Submits a voucher redemption application.

    Returns:
        A 2-tuple of:
            - A bool of whether the submission goes through and
            - An error message (if any)

    """
    if not is_voucher_code_valid(
            application.vouchercode_str,
            ip_address,
            action=VoucherCodeAttempt.Action.APPLICATION_REVIEW):
        return False, str(_('voucher_input_incorrect_format'))

    code = VoucherCode.objects.get(code=application.vouchercode_str)
    code.application = application
    assign_voucher_code_amount(application, code)
    code.save()
    application.save()
    return True, None


def assign_voucher_code_amount(application, code):
    """Implement any code-specific special dollar amount assignments here."""
    # if <condition>:
    #     code.added_amount = <value>
    pass


def auto_update_application_statuses():
    """Run fraud checks on newly submitted applications.

    Updates all applications with status SUBMITTED to APPROVED, REJECTED or
    NEEDS_REVIEW.
    """
    new_applications = Application.objects.filter(
        status=Application.ApplicationStatus.SUBMITTED
    ).order_by('-submitted_date')
    LOGGER.info('Setting statuses for %d new applications...' %
                len(new_applications))

    apply_dedup_check(AddressDedupCheck(), new_applications)
    apply_dedup_check(NamePhoneDedupCheck(), new_applications)

    ###########################################################################
    #                  ADD ADDITIONAL FRAUD CHECKS HERE                       #
    ###########################################################################

    # Approve all applications that weren't flagged for review.
    for application in new_applications:
        if application.status not in (
            Application.ApplicationStatus.NEEDS_REVIEW,
            Application.ApplicationStatus.REJECTED,
        ):
            application.status = Application.ApplicationStatus.APPROVED
        application.save()
        LOGGER.info('Application %d: %s' % (application.application_id,
                                            application.status))

    notification.send_text([a for a in new_applications if a.status ==
                            Application.ApplicationStatus.REJECTED], notification.TextType.REJECTION)
    LOGGER.info('Set statuses for %d new applications.' %
                len(new_applications))


def apply_dedup_check(dedup_check, new_apps):
    """Applies the provided dedup_check to new_apps.

    Any duplicates found will have their status updated to the status
    specified in the provided dedup_check.

    Args:
      dedup_check: The DedupCheck to use for duplicate checking.
      new_apps: The apps on which to apply duplicate checking.
    """

    dup_counts = collections.defaultdict(int)
    all_apps = Application.objects.all()
    for app in all_apps:
        dup_counts[dedup_check.get_test_value(app)] += 1

    duplicate_apps = filter(lambda app: dup_counts[dedup_check.get_test_value(
        app)] > dedup_check.get_max_duplicates(), new_apps)
    for app in duplicate_apps:
        if dedup_check.is_preapproved(app):
            continue
        app.status = dedup_check.new_status
        if app.note:
            app.note += '; %s' % dedup_check.get_error_message()
        else:
            app.note = dedup_check.get_error_message()


def update_application_statuses(
        application_ids,
        status,
        send_text_messages=True):
    applications = Application.objects.filter(pk__in=application_ids)
    LOGGER.info('Setting status to {} for applications: {}...'.format(
                status, application_ids))

    Application.bulk_update_status(applications, status)

    if status == Application.ApplicationStatus.PAYMENT_CONFIRMED and send_text_messages:
        notification.send_text(
            applications, notification.TextType.PAYMENT_CONFIRMED)

    LOGGER.info('Done')
