#!/usr/bin/env python
# update_app_statuses.py
# See LICENSE for details.

"""
Run:

Update the status of a list of application IDs from a file. For example:
 ./manage.py update_app_statuses --status=SENT_FOR_PAYMENT --filename=some_file


"""
from django.core.management.base import BaseCommand

from app_ccf.models import Application
from app_ccf.common import update_application_statuses


class Command(BaseCommand):

    help = 'Assigns approval statuses to new applications.'

    def add_arguments(self, parser):
        parser.add_argument('--filename', type=str, required=True,
                            help=('A file with a list of IDs of applications '
                                  'to update the status for, each on a new '
                                  'line.'))
        parser.add_argument('--status', type=str, required=True,
                            help=('The new status to assign to the given '
                                  'applications'))

    def handle(self, *args, **kwargs):
        filename = kwargs['filename']
        status = getattr(Application.ApplicationStatus,
                         kwargs['status'].upper())

        with open(filename, 'r') as f:
            application_ids = [line.strip() for line in f]

        update_application_statuses(application_ids, status)
