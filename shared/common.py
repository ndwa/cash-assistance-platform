from django.db import models
from django.utils.translation import ugettext_lazy as _
from django import forms


class TypeOfWork(models.TextChoices):
    HOUSE_CLEANING = 'House cleaning', _('house_cleaning')
    NANNY = 'Nanny', _('nanny')
    HOME_CARE = 'Home care', _(
        'home_care')
    OTHER = 'Other', _('none_of_the_above')


YES_NO_CHOICES = ((None, ''), (True, _('Yes')), (False, _('No')))


def clean_type_of_work_data(form_data):
    if not form_data:
        raise forms.ValidationError(
            _("This field is required."))
    if form_data == TypeOfWork.OTHER:
        raise forms.ValidationError(
            _("At this time, the Coronavirus Care Fund is only open to "
              "applicants who work in house cleaning, childcare, care for "
              "elders, or care for people with disabilities."))
    return form_data


def check_required(form_data):
    if form_data == None or form_data == 'None' or form_data == '':
        raise forms.ValidationError(
            _("This field is required."))
    return form_data
