#!/usr/bin/env python
# invalidate_voucher_codes.py
# See LICENSE for details.

"""
Run:  ./manage.py invalidate_voucher_codes --filename <filename>
Run:  ./manage.py invalidate_voucher_codes \
        --affiliate <affiliate> \
        --campaign <campaign>
"""
import logging

from django.core.management.base import BaseCommand

from app_ccf.common import invalidate_voucher_codes_with_campaign, invalidate_voucher_codes_with_code_list

# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):

    help = ('Invalidates voucher codes using a provided list or an associated '
            'campaign.')

    def add_arguments(self, parser):
        parser.add_argument('-f', '--filename', type=str,
                            help=('File with a list of codes to '
                                  'invalidate.'))
        parser.add_argument('--affiliate', type=str,
                            help=('Name of affiliate to invalidate.'))
        parser.add_argument('--campaign', type=str,
                            help=('Name of campaign to invalidate.'))

    def handle(self, *args, **kwargs):
        if kwargs['filename']:
            if (kwargs['affiliate'] or kwargs['campaign']):
                LOGGER.error(
                    'Cannot provide both a filename and another flag.')
                return
            with open(kwargs['filename'], 'r') as f:
                codes = f.read().splitlines()
            invalidate_voucher_codes_with_code_list(codes)
        elif kwargs['campaign']:
            if not kwargs['affiliate']:
                LOGGER.error('Must provide affiliate.')
            invalidate_voucher_codes_with_campaign(
                affiliate=kwargs['affiliate'],
                campaign=kwargs['campaign'])
        else:
            LOGGER.error(
                'Must provide either list of codes or campaign to invalidate.')
