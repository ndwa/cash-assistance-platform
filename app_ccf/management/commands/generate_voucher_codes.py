j#!/usr/bin/env python
# generate_voucher_codes.py
# See LICENSE for details.

"""
Run:  ./manage.py generate_voucher_codes <filename> <num_codes> [--length <length>]
"""
import logging

from django.core.management.base import BaseCommand

from app_ccf.common import generate_voucher_codes

# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):

    help = 'Generates new codes into a file.'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str,
                            help=('File to write new codes to'))
        parser.add_argument('num_codes', type=int,
                            help=('The number of new codes to generate.'))
        parser.add_argument('--length', type=int, default=9,
                            help=('The length of each code.'))

    def handle(self, *args, **kwargs):
        codes = generate_voucher_codes(
            num_codes=kwargs['num_codes'],
            code_length=kwargs['length'],
            alphabet='abcdefghijkmnopqrstuvwxyz')  # a-z minus l
        with open(kwargs['filename'], 'w') as f:
            for code in codes:
                f.write('%s\n' % code)