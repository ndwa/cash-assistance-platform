#!/usr/bin/env python
# export_apps.py
# See LICENSE for details.

"""
Run:  ./manage.py export_apps
"""
import collections
import csv
import logging
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand

from app_ccf.models import Application

# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

TABLES = {
    'approved': {'status': Application.ApplicationStatus.PAYMENT_CONFIRMED
                 },
    'needs_review': {
        'status': Application.ApplicationStatus.REJECTED
    },
}


def write_table(name, metadata, timestamp):
    applications = Application.objects.filter(
        status=metadata['status']).order_by('-submitted_date')

    if len(applications) == 0:
        LOGGER.info('No applications with status "%s" to export.', name)
        return

    rows = []
    for application in applications:
        data = collections.OrderedDict([
            ('Date', application.submitted_date.strftime('%Y-%m-%d %H:%M:%S')),
            ('Code', application.vouchercode_str),
            ('Application ID', application.application_id),
            ('Language', application.language),
            ('First', application.first_name),
            ('Last', application.last_name),
            ('Phone', application.phone_number),
            ('Email', application.email),
            ('Address1', application.addr1),
            ('Address2', application.addr2),
            ('City', application.city),
            ('State', application.state),
            ('Zip', application.zip_code),
            ('USPS Verified', application.usps_standardized),
            ('USPS Standardized', application.usps_standardized),
            ('Status', application.status),
            ('Note', application.note),
        ])
        rows.append(data)

    filename = "ccf_{name}-{ts}.csv".format(name=name, ts=timestamp)
    fieldnames = rows[0].keys()
    LOGGER.info('Writing {r} rows to "{fname}"...'.format(
        r=len(rows), fname=filename))
    with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class Command(BaseCommand):
    help = 'Exports a set of recent applications to a CSV.'

    def handle(self, *args, **kwargs):
        LOGGER.info('Preparing CSVs...')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for status_name, status_metadata in TABLES.items():
            write_table(status_name, status_metadata, timestamp)

        LOGGER.info('Done.')
