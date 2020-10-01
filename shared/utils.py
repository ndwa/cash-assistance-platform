# Shared Utils
from django import forms
import logging
import unidecode
from contextlib import contextmanager
from django.core.validators import RegexValidator
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

import re


def visitor_ip_address(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def clean_phone_number(phone_number):
    """Returns a cleaned version of a user-provided phone number."""
    if not phone_number.startswith('+1'):
        phone_number = '+1' + phone_number
    return phone_number.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")


def phone_number_validator():
    return RegexValidator("^[+][0-9]{8,}$", _('phone_number_incorrect_format'))


def no_special_chars_validator():
    return RegexValidator("^[^0-9_!¡?÷?¿/\\+=@#$%ˆ&*(){}|~<>;:[\]]+$",
                          _('no_special_characters_allowed'))


def street_address_validator():
    return RegexValidator(
        "^.[^?@]*$", _('street_address_incorrect_format'))


def zip_code_validator():
    return RegexValidator(
        "^\d{5}$", _('zip_code_incorrect_format'))


def to_user_facing_code(code):
    """Returns a user-facing code given a raw code (e.g., abcdefghij)."""
    return '{}-{}-{}'.format(code[:3], code[3:6], code[6:])


def validate_phone_number(value):
    # Verify that only allowed characters were input.
    p = re.compile('^[0-9-\(\) ]+')
    if not p.match(value):
        raise forms.ValidationError(_("needs_phone_number_format"))
    # Verify that the length of numbers
    if len(value.replace("-", "")
                .replace("(", "")
                .replace(")", "")
                .replace(" ", "")) != 10:
        raise forms.ValidationError(_("needs_phone_number_format"))


@contextmanager
def activate_language(language):
    """A context manager for temporarily activating a language in the env."""
    cur_language = translation.get_language()
    translation.activate(language)
    try:
        yield None
    finally:
        translation.activate(cur_language)
