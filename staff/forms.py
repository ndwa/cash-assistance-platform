from django.forms import ModelForm, TextInput, Select

from localflavor.us.forms import USStateField
from localflavor.us.us_states import US_STATES

from app_ccf.models import VoucherCodeBatch, PreapprovedAddress


class VoucherCodeGenerateForm(ModelForm):

    class Meta:
        model = VoucherCodeBatch
        fields = ['num_codes', 'affiliate', 'campaign',
                  'channel', 'base_amount', 'expiration_date']
        widgets = {
            'num_codes': TextInput(attrs={'class': 'form-control',
                                          'type': 'number', 'size': 80}),
            'affiliate': TextInput(attrs={'class': 'form-control'}),
            'campaign': TextInput(attrs={'class': 'form-control'}),
            'channel': TextInput(attrs={'class': 'form-control'}),
            'base_amount': TextInput(attrs={'class': 'form-control',
                                            'type': 'number', 'size': 80}),
            'expiration_date': TextInput(attrs={'type': 'date',
                                                'placeholder': 'yyyy-mm-dd'}),
        }


class PreapprovedAddressGenerateForm(ModelForm):
    state = USStateField(widget=Select(
        attrs={'class': 'form-control'}, choices=US_STATES))

    class Meta:
        model = PreapprovedAddress
        fields = ['addr1', 'city', 'state', 'zip_code', 'note']
        widgets = {
            'addr1': TextInput(attrs={'class': 'form-control'}),
            'city': TextInput(attrs={'class': 'form-control'}),
            'zip_code': TextInput(attrs={'class': 'form-control'}),
            'note': TextInput(attrs={'class': 'form-control'}),
        }