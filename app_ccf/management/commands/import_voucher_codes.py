#!/usr/bin/env python
# import_voucher_codes.py
# See LICENSE for details.

"""
Run:  ./manage.py import_voucher_codes <filename>

Args:
    filename: A file with a list of codes to be imported, each on a new line.
        Codes must be between 1 and 20 characters and can only contain
        characters in [A-Z0-9].
"""
import logging
from datetime import datetime, timedelta, timezone

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from app_ccf.models import VoucherCode

# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):

    help = 'Adds a list of voucher codes to the database.'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str,
                            help=('A file with a list of codes to be imported, '
                                  'each on a new line. Codes must be between 1 '
                                  'and 20 characters and can contain '
                                  'characters in [A-Z0-9].'))
        parser.add_argument('--amount', type=int, default=400,
                            help=('The dollar amount to be paid.'))
        parser.add_argument('--affiliate', type=str, required=True,
                            help='The associated affiliate.')
        parser.add_argument('--campaign', type=str, required=True,
                            help='The associated campaign.')
        expiration_group = parser.add_mutually_exclusive_group()
        expiration_group.add_argument('--exp-on-date', type=str,
                                      help=('The expiration date, format '
                                            'MM-DD-YYYY. Set either this field '
                                            'or --exp-days-from-now, but not '
                                            'both.'))
        expiration_group.add_argument('--exp-days-from-now', type=int,
                                      help=('The number of days from now to '
                                            'set the expiration date. Set '
                                            'either this field or '
                                            '--exp-on-date, but not both. If '
                                            'neither is set, this defaults to '
                                            '60 days.'))

    def handle(self, *args, **kwargs):
        filename = kwargs['filename']

        amount = kwargs['amount']
        affiliate = kwargs['affiliate']
        campaign = kwargs['campaign']
        if kwargs['exp_on_date']:
            expiration_date = datetime.strptime(
                kwargs['exp_on_date'],
                '%m-%d-%Y'
            ).replace(tzinfo=timezone.utc)
        else:
            exp_days_from_now = kwargs['exp_days_from_now'] or 60  # default
            expiration_date = datetime.now(
                timezone.utc) + timedelta(days=exp_days_from_now)

        LOGGER.info('Uploading codes with amount [%d], '
                    'affiliate ["%s"], campaign ["%s"], expiration [%s]...' % (
                        amount, affiliate, campaign,
                        expiration_date)
                    )
        num_valid_codes = 0
        num_invalid_codes = 0
        with open(filename, 'r') as f:
            voucher_codes_to_write = []
            for line in f:
                voucher_code_str = line.strip()
                voucher_code = VoucherCode(
                    code=voucher_code_str,
                    amount=amount,
                    expiration_date=expiration_date,
                    affiliate=affiliate,
                    campaign=campaign,
                    is_active=True,
                )
                try:
                    voucher_code.full_clean()  # Validate code format
                except ValidationError as e:
                    LOGGER.error('Error importing code \'%s\': %s' % (
                        voucher_code_str, str(e)))
                    num_invalid_codes += 1
                else:
                    voucher_codes_to_write.append(voucher_code)
                    LOGGER.info('Imported code \'%s\'.' % voucher_code_str)
                    num_valid_codes += 1

        LOGGER.info('Writing %d codes to database (%d invalid)...' %
                    (num_valid_codes, num_invalid_codes))
        VoucherCode.objects.bulk_create(voucher_codes_to_write)

        LOGGER.info('Done.')
        LOGGER.debug('Current codes: %s' % VoucherCode.objects.filter())
