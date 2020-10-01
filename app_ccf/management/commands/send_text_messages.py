#!/usr/bin/env python
# send_text_messages.py
# See LICENSE for details.

"""
Run:

./manage.py send_text_messages --filename=foo.csv

The input csv file should contain a "phone" and a "language" fields. All other
fields will be ignored. For example:

phone,language
11231231234,es
12342342345,en
13453453456,es

"""
import csv

from django.core.management.base import BaseCommand
from app_ccf.twilio import twilio_client

from app_ccf import utils

from app_ccf.models import Application


# Fill out the messages before you run this command.
en_message = ''
es_message = ''


class Command(BaseCommand):

    help = 'Send text messages to a list of phone numbers.'

    def add_arguments(self, parser):
        parser.add_argument('--filename', type=str, required=True,
                            help=('Name of a CSV file that contains at least '
                                  'a "phone" field and a "language" field.'))

    def handle(self, *args, **kwargs):
        if not en_message or not es_message:
            print('Please fill out the English and Spanish messages in this '
                  'file before you run the command.')
            return

        filename = kwargs['filename']

        with open(filename, newline='') as csvfile:
            csv_reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            if not {'phone', 'language'}.issubset(csv_reader.fieldnames):
                print('The CSV file should contain a "phone" field and a '
                      '"language" field')
                return

            for row in csv_reader:
                if row['language'] == 'en':
                    message = en_message
                elif row['language'] == 'es':
                    message = es_message
                else:
                    raise ValueError
                twilio_client.trigger_text_messages(
                    [row['phone']], message)
                print('Triggered an {} message for {}'.format(row['language'],
                                                              row['phone']))
