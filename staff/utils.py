from datetime import datetime, timedelta, timezone
import logging
import random

from django.core.exceptions import ValidationError

from app_ccf.models import VoucherCode


LOGGER = logging.getLogger(__name__)


def import_voucher_codes(filename, batch):
    LOGGER.info('Uploading codes...')
    num_valid_codes = 0
    num_invalid_codes = 0
    with open(filename, 'r') as f:
        voucher_codes_to_write = []
        for line in f:
            voucher_code_str = line.strip()
            voucher_code = VoucherCode(
                code=voucher_code_str,
                added_amount=0,
                batch=batch,
                is_active=True,
            )
            try:
                pass
                # voucher_code.full_clean()  # Validate code format
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


def generate_voucher_codes(num_codes, code_length, alphabet):
    """Returns a list of new unique codes not already in the database.

    Args:
        num_codes: The number of codes to generate.
        code_length: The number of characters in each code.
        alphabet: A string to choose characters from for each code.
    """
    # Highly unlikely to happen, but we pull up the existing code set to check
    # against in case we generate a duplicate
    code_set = set(VoucherCode.objects.filter().values_list('code', flat=True))
    new_codes = []
    while len(new_codes) < num_codes:
        new_code = ''.join([random.choice(alphabet)
                            for j in range(code_length)])
        if new_code not in code_set:
            new_codes.append(new_code)
            code_set.add(new_code)
    return new_codes


def invalidate_voucher_codes_with_campaign(affiliate, campaign):
    """Invalidates all codes under the given campaign name."""
    voucher_codes = VoucherCode.objects.filter(batch__affiliate=affiliate,
                                               batch__campaign=campaign)
    LOGGER.info('Found %d codes with affiliate \'%s\', '
                'and campaign \'%s\'. Invalidating...' %
                (len(voucher_codes), affiliate, campaign))
    voucher_codes.update(is_active=False)
    LOGGER.info('Done.')


def invalidate_voucher_codes_with_code_list(codes):
    """Invalidates the codes given in a list. Unknown codes are ignored."""
    voucher_codes = VoucherCode.objects.filter(code__in=codes)
    LOGGER.info('Found %d out of %d provided codes. Invalidating...' %
                (len(voucher_codes), len(codes)))
    voucher_codes.update(is_active=False)
    LOGGER.info('Done.')
