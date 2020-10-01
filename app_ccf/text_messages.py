
from django.utils import translation
from app_ccf.config import CONFIG
from django.conf import settings

_ = translation.ugettext_lazy


def get_submission_message(application):
    return str(_('submission-text')).format(
        CONFIG['fund_name'], application.get_full_address(), CONFIG['customer_service_phone_number'])

def get_payment_confirmed_message():
    return str(_('payment-confirmed-text')).format(
        CONFIG['customer_service_phone_number'])


def get_rejection_message():
    return str(_('rejection-text')).format(CONFIG['customer_service_phone_number'])
