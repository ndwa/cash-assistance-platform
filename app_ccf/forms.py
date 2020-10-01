import json
import re

from django import forms
from django.forms.models import model_to_dict
from django.core.validators import MaxLengthValidator
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from .models import Application
from shared.utils import no_special_chars_validator, validate_phone_number

from localflavor.us.forms import USStateField
from localflavor.us.us_states import US_STATES
from shared.common import TypeOfWork, clean_type_of_work_data


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = '__all__'


class RequirementsForm(forms.Form):
    qualified = forms.BooleanField(
        widget=forms.RadioSelect(
            choices=[
                (True, _('yes')), (False, _('no'))]))


class VoucherCheckForm(forms.Form):
    vouchercheck = forms.BooleanField(
        widget=forms.RadioSelect(
            choices=[
                (True, _('yes')), (False, _('no'))]))


def validate_access_code(value):
    # Verify that only allowed characters were input.
    p = re.compile('^[A-Za-z- ]+')
    if not p.match(value):
        raise forms.ValidationError(_("voucher_input_incorrect_format"))
    # Verify that the length of letters is correct
    if len(value.replace("-", "")
                .replace(" ", "")) != 9:
        raise forms.ValidationError(_("voucher_input_incorrect_format"))


class VoucherCodeForm(forms.Form):
    voucher_input = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control',
                   'maxlength': '11',  # max 9 chars + 2 dashes
                   'onkeypress': 'return isVoucherKey(event);',
                   'autocomplete': 'off'
                   }),
        validators=[validate_access_code],
    )


class ProfileForm(ApplicationForm):
    fund_name = ''

    def __init__(self, fund_name, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fund_name = fund_name

    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control',
                                      'maxlength': '20'}),
        validators=[MaxLengthValidator(23), no_special_chars_validator()],
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control',
                                      'maxlength': '20'}),
        validators=[MaxLengthValidator(23), no_special_chars_validator()],
    )

    class Meta:
        model = Application
        fields = ['age_range']
        widgets = {
            'age_range': forms.RadioSelect(),
        }

    def clean_age_range(self):
        data = self.cleaned_data['age_range']
        if data == Application.AgeRange.RANGE__17:
            raise forms.ValidationError(
                _("At this time, the {fund_name} is only open to "
                  "applicants that are 18 years or older.").format(
                      fund_name=self.fund_name))
        return data


class ProfileFormNdwa(ProfileForm):
    type_of_work = forms.ChoiceField(
        widget=forms.RadioSelect(), choices=TypeOfWork.choices)

    def clean_type_of_work(self):
        return clean_type_of_work_data(self.cleaned_data['type_of_work'])


class HouseholdForm(ApplicationForm):
    class Meta:
        model = Application
        fields = ['household_income']
        widgets = {
            'household_income': forms.RadioSelect(),
        }

    ETHNICITY_OPTIONS = (
        ('Latina', _('ethnicity_latina')),
        ('Black', _(
            'ethnicity_black')),
        ('Asian', _(
            'ethnicity_asian')),
        ('Indigenous', _(
            'ethnicity_indigenous')),
        ('White', _('ethnicity_white')),
        ('Other', _('ethnicity_other')),
    )
    ethnicity = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                          choices=ETHNICITY_OPTIONS,
                                          required=False)
    GENDER_OPTIONS = (
        ('Female', _('gender_female')),
        ('Male', _(
            'gender_male')),
        ('Transgender', _(
            'gender_transgender')),
        ('Nonbinary/third gender', _(
            'gender_nonbinary')),
        ('Other', _(
            'gender_other')),
    )
    gender = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                       choices=GENDER_OPTIONS,
                                       required=False)


class HouseholdFormExpanded(HouseholdForm):
    class Meta:
        model = Application
        fields = ['household_size', 'household_income']
        widgets = {
            'household_income': forms.RadioSelect(),
        }

    def clean_household_size(self):
        data = self.cleaned_data['household_size']
        if not data:
            raise forms.ValidationError(
                _("This field is required."))
        if data < 1:
            raise forms.ValidationError(
                _("Ensure this value is greater than or equal to 1."))
        return data


def get_states_in(language):
    """Returns US states in the provided language, forcing eager evaluation."""
    with translation.override(language):
        return list((abbr, str(name)) for abbr, name in US_STATES[:])


class AddressForm(ApplicationForm):
    class Meta:
        model = Application
        fields = ['addr1', 'addr2', 'city', 'state',
                  'zip_code']
        widgets = {
            'addr1': forms.TextInput(attrs={'class': 'form-control'}),
            'addr2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
        }
    # Hack to deal with issue that UsStateSelect does not contain
    # a default value (https://stackoverflow.com/questions/1830894).
    state_choices = get_states_in('en')
    state_choices.insert(0, ('', _('select_one')))
    state = USStateField(widget=forms.Select(
        attrs={'class': 'form-control'}, choices=state_choices))


class AddressVerifyForm(ApplicationForm):
    class Meta:
        model = Application
        fields = ['usps_standardized']

class ContactForm(ApplicationForm):
    phone_digits = forms.CharField(
        widget=forms.TextInput(attrs={
                               'type': 'tel', 'class': 'form-control',
                               'maxlength': '20',  # 10 numbers + dash, parenthesis, spaces
                               'onkeypress': 'return isNumberKey(event);'}),
        validators=[validate_phone_number],
    )

    class Meta:
        model = Application
        fields = ['email']
        widgets = {
            'email': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SignatureForm(ApplicationForm):
    tos = forms.BooleanField()

    class Meta:
        model = Application
        fields = ['signature']
        widgets = {
            'signature': forms.TextInput(attrs={'class': 'form-control'}),
        }


class DisclosureForm(forms.Form):
    pass


class WelcomeForm(forms.Form):
    pass


class ReviewForm(forms.Form):
    pass
