#!/usr/bin/env python
# import_addresses.py
# See LICENSE for details.

"""
Run:  ./manage.py import_addresses <filename>

Args:
    filename: A CSV of preapproved addresses.
"""

import csv
import logging

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from app_ccf.models import PreapprovedAddress
from app_ccf.utils import verify_usps_addr


# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):

    help = 'Adds a list of preapproved addresses to the database.'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str,
                            help='CSV of preapproved addresses.')

    def handle(self, *args, **kwargs):
        num_addresses_total = 0
        num_addresses_valid = 0
        with open(kwargs['filename'], newline='') as csvfile:
            csv_reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            for field in ['Addr1', 'City', 'State', 'Zip', 'Notes']:
                if field not in csv_reader.fieldnames:
                    LOGGER.error('CSV error: Missing column "%s"' % field)
                    return
            LOGGER.info('Processing addresses...')
            for row in csv_reader:
                num_addresses_total += 1
                (number, rest) = row['Addr1'].split(maxsplit=1)
                # Fix formatting in PO Box addresses
                if 'PO BOX' in rest.upper():
                    row['Addr1'] = 'PO BOX ' + number

                addr1, _, city, state, zip_code, _, error = verify_usps_addr(
                    row['Addr1'], '', row['City'], row['State'], row['Zip'])
                if error:
                    LOGGER.error('Address not found: ' +
                                 ','.join(row.values()))
                    continue

                address = PreapprovedAddress(
                    addr1=addr1,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    note=row['Notes'],
                )

                try:
                    address.full_clean()
                except ValidationError as e:
                    # Duplicate address, compare notes
                    old_note = PreapprovedAddress.objects.get(
                        addr1=address.addr1).note
                    new_note = address.note

                    if old_note == new_note:
                        LOGGER.info('Address "%s" already exists with identical '
                                    'note, skipping.' % address.addr1)
                    else:
                        LOGGER.error('Duplicate address: %s, %s, %s %s' % (
                            address.addr1, address.city, address.state,
                            address.zip_code))
                        LOGGER.error('- Note (old): ' + old_note)
                        LOGGER.error('- Note (new): ' + new_note)
                else:
                    address.save()
                    num_addresses_valid += 1

        LOGGER.info('Added %d valid addresses (%d invalid).' % (
            num_addresses_valid, num_addresses_total - num_addresses_valid))
        LOGGER.info('Done.')
