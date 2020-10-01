from app_ccf.models import Application
import datetime

DEFAULT_CCF_APP_FIELDS = {
    'vouchercode_str': 'abcabcabc',
    'first_name': 'Michael',
    'last_name': 'Jackson',
    'age_range': Application.AgeRange.RANGE_30_49,
    'household_size': 2,
    'phone_number': '+15555555555',
    'addr1': '123 Some St',
    'city': 'NY',
    'state': 'NY',
    'zip_code': '10011',
    'signature': 'MJ',
    'usps_verified': False,
    'submitted_date': datetime.datetime.now(),
}


DEFAULT_WORKER_VALUES = {
    'first_name': 'Jay',
    'last_name': 'Smith',
    'phone_number': '+12223334444',
}

DEFAULT_EMPLOYER_VALUES = {
    'first_name': 'Sammy',
    'last_name': 'Halawa',
    'phone_number': '+56667778888',
}

DEFAULT_ELIGIBILITY_APP_FIELDS = {
    'reminder_count': 1,
    'reference_first_name': 'Amilcar',
    'reference_last_name': 'Rodriguez',
    'reference_phone_number': '+15555555555',
    'domestic_work_type': 'Nanny',
    'domestic_work_length': '1',
    'domestic_work_source': 'Referrals',
    'currently_working': True,
    'interested_in_referrals': True,
    'zip_code': '11051',
}

DEFAULT_VERIFICATION_VALUES = {
    'zip_code': '55555',
    'type_of_domestic_work': 'Nanny',
    'length_worker': '2-5',
    'find_and_hire_worker': 'Referrals',
    'worker_currently_working': True,
    'worker_coming_back_to_work': True,
    'can_verify_work_experience': True,
}
