import logging
import json

from django.shortcuts import render, redirect, reverse
from django.conf import settings
from django.template import loader
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.edit import FormView
from django.forms.models import model_to_dict
from django.views.generic import TemplateView
from django.views.generic.base import TemplateResponseMixin, View
from django.utils.translation import get_language

from . import notification, utils
from .common import ApplicationSession, is_voucher_code_valid, submit_application, ApplicationSubmissionError
from .config import CONFIG
from .forms import (ReviewForm, DisclosureForm, WelcomeForm, HouseholdForm, HouseholdFormExpanded,
                    RequirementsForm, VoucherCheckForm, VoucherCodeForm, ProfileForm, ProfileFormNdwa,
                    AddressForm, AddressVerifyForm, SignatureForm, ContactForm)
from .models import VoucherCode

from shared.utils import clean_phone_number, visitor_ip_address


# Logging.
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class CcfView(TemplateResponseMixin):
    step_number = 0
    TOTAL_STEPS = 10
    status_code = 200

    def _load_application_session(self):
        try:
            self.application_session = ApplicationSession.load(
                self.request.session.get('application_session', None))
        except (json.JSONDecodeError, TypeError) as e:
            LOGGER.debug(
                'Got %s while loading %s. Resetting ApplicationSession...' % (
                    e, self.request.session.get('application_session', None)))
            self.application_session = ApplicationSession()

    def get_context_data(self, **kwargs):
        context = super(CcfView, self).get_context_data(**kwargs)
        self._load_application_session()
        context['lang_code'] = self.request.LANGUAGE_CODE
        context['application_model'] = self.application_session.model
        context['step_number'] = self.step_number
        context['status_code'] = self.status_code
        context['total_steps'] = self.TOTAL_STEPS
        context.update(CONFIG)
        return context

    def get_template_names(self):
        return self.template_name


class MultiStepFormView(FormView, CcfView):
    """
    Super class that facilitates the previous and next functions for a multi-step form.
    Each view in the multi-step form is inteded to sub-class this class. This class
    populates the next_name and previous_name variables to determine which url goes next.
    """
    next_name = ''
    previous_name = ''
    fund_name = ''

    ip_address = ''

    def get_initial(self):
        initial = super().get_initial()
        self.ip_address = visitor_ip_address(self.request)
        self.fund_name = CONFIG['fund_name']
        self._load_application_session()
        return initial

    def get_success_url(self):
        return reverse(self.next_name)

    def get_context_data(self, **kwargs):
        context = super(MultiStepFormView, self).get_context_data(**kwargs)
        context['previous_url'] = self.previous_name
        context['application_session'] = ApplicationSession.to_dict(
            self.application_session)
        return context


class ApplicationView(MultiStepFormView):
    """
    Contains a subclass to display fields of an Application model. The class is responsible
    for extracting the session-persisted Application fields and pre-populating them into the
    form before showing it.
    """

    def get_initial(self):
        initial = super().get_initial()
        initial = model_to_dict(self.application_session.model)
        return initial

    def form_save_to_session(self, form):
        for field in form.cleaned_data:
            setattr(self.application_session.model,
                    field, form.cleaned_data[field])
        self.request.session['application_session'] = ApplicationSession.serialize(
            self.application_session)

    def form_valid(self, form):
        self.form_save_to_session(form)
        return super().form_valid(form)


class CheckView(MultiStepFormView):
    """
    Contains a subclass to display fields that are not in the Application model (checks). These are checks that are
    required from the user such as eligibility and acknowledging the terms of service, but that are not stored in the
    model / database because their value is always true. The class is responsible  for extracting the session-persisted
    information and pre-populating them into the form before showing it.
    """

    def get_initial(self):
        initial = super().get_initial()
        initial = self.application_session.checks
        return initial

    def form_valid(self, form):
        for field in form.cleaned_data:
            self.application_session.checks[field] = form.cleaned_data[field]
        self.request.session['application_session'] = ApplicationSession.serialize(
            self.application_session)
        return super().form_valid(form)


class RedirectInvalid(CheckView):
    """
    Overwrites the form_invalid method to redirect to the invalid_url page name
    when there is an error.
    """
    invalid_url = ''

    def form_invalid(self, form):
        return redirect(self.invalid_url)


class LanguageView(TemplateView, CcfView):
    template_name = 'language.html'

    def get_context_data(self, **kwargs):
        # Execute all the context setup work that populates application_session.
        context = super().get_context_data(**kwargs)
        if 'accesscode' in self.kwargs:
            self.application_session.model.vouchercode_str = self.kwargs['accesscode']
            self.request.session['application_session'] = ApplicationSession.serialize(
                self.application_session)
        return context


class WelcomeView(ApplicationView):
    template_name = 'welcome.html'
    form_class = WelcomeForm

    def get_initial(self):
        initial = super().get_initial()
        # Set the chosen language and save it to the session.
        setattr(self.application_session.model,
                'language', get_language())
        self.request.session['application_session'] = ApplicationSession.serialize(
            self.application_session)
        return initial


class RequirementsView(RedirectInvalid):
    template_name = 'requirements.html'
    form_class = RequirementsForm


class VoucherCheckView(RedirectInvalid):
    template_name = 'vouchercheck.html'
    form_class = VoucherCheckForm


class VoucherCodeView(ApplicationView):

    def get_initial(self):
        initial = super().get_initial()
        initial['voucher_input'] = self.application_session.model.vouchercode_str
        return initial

    def form_valid(self, form):
        # Format code to be lowercase and save the formatted code
        voucher_code = form.cleaned_data['voucher_input'].replace(
            "-", "").replace(" ", "")
        cleaned_code = voucher_code.lower()
        setattr(self.application_session.model,
                'vouchercode_str', cleaned_code)

        if is_voucher_code_valid(cleaned_code, ip_address=self.ip_address):
            return super().form_valid(form)

        form.add_error(
            None, _("This access code is invalid. Please check the "
                    "code and try again. If you're having trouble, please contact us "
                    "at {customer_service_phone_number}.").format(
                        customer_service_phone_number=self.get_context_data()['customer_service_phone_number']))
        return super().form_invalid(form)

    template_name = 'vouchercode.html'
    form_class = VoucherCodeForm


class ProfileView(ApplicationView):
    template_name = 'profile.html'

    def get_form_class(self):
        return ProfileFormNdwa

    def get_form_kwargs(self):
        kwargs = super(ProfileView, self).get_form_kwargs()
        kwargs['fund_name'] = self.fund_name
        return kwargs

    def form_valid(self, form):
        setattr(self.application_session.model,
                'type_of_work', form.cleaned_data['type_of_work'])
        setattr(self.application_session.model,
                'first_name', form.cleaned_data['first_name'])
        setattr(self.application_session.model,
                'last_name', form.cleaned_data['last_name'])
        return super().form_valid(form)


class HouseholdView(ApplicationView):
    template_name = 'household.html'

    def get_form_class(self):
        return HouseholdFormExpanded

    def form_valid(self, form):
        setattr(self.application_session.model,
                'ethnicity', form.cleaned_data['ethnicity'])
        setattr(self.application_session.model,
                'gender', form.cleaned_data['gender'])
        return super().form_valid(form)


class AddressView(ApplicationView):
    template_name = 'address.html'
    form_class = AddressForm

    def form_valid(self, form):
        """
        When the form is validated, extract the address and verify it with USPS.
        If the verification succeeds, redirect to /usps-modified-address, if not
        redirect to /usps-cannot-verify.
        """
        self.form_save_to_session(form)
        addr1, addr2, city, state, zip_code, return_text, error_description = utils.verify_usps_addr(
            form.cleaned_data['addr1'],
            form.cleaned_data['addr2'],
            form.cleaned_data['city'],
            form.cleaned_data['state'],
            form.cleaned_data['zip_code'])
        if error_description:
            return redirect('usps-cannot-verify')
        setattr(self.application_session.model,
                'usps_verified', True)

        usps_standardized = (addr1 == form.cleaned_data['addr1'] and
                             addr2 == form.cleaned_data['addr2'] and
                             city == form.cleaned_data['city'] and
                             state == form.cleaned_data['state'] and
                             zip_code == form.cleaned_data['zip_code'])
        setattr(self.application_session.model,
                'usps_standardized', usps_standardized)

        self.form_save_to_session(form)
        if 'apartment' in return_text:
            return redirect('usps-missing-apt')
        if not usps_standardized:
            return redirect('usps-modified-address')
        return super().form_valid(form)


class AddressVerifyView(ApplicationView):
    template_name = 'address_verify.html'
    form_class = AddressVerifyForm

    def get_initial(self):
        initial = super().get_initial()
        (self.verified_addr_1,
         self.verified_addr_2,
         self.verified_city,
         self.verified_state,
         self.verified_zip_code,
         self.return_text,
         self.usps_error) = utils.verify_usps_addr(
            self.application_session.model.addr1,
            self.application_session.model.addr2,
            self.application_session.model.city,
            self.application_session.model.state,
            self.application_session.model.zip_code)
        return initial

    def get_context_data(self, **kwargs):
        context = super(ApplicationView, self).get_context_data(**kwargs)
        context['verified_addr_1'] = self.verified_addr_1
        context['verified_addr_2'] = self.verified_addr_2
        context['verified_city'] = self.verified_city
        context['verified_state'] = self.verified_state
        context['verified_zip_code'] = self.verified_zip_code
        return context

    def form_valid(self, form):
        if form.cleaned_data['usps_standardized']:
            setattr(self.application_session.model,
                    'addr1', self.verified_addr_1)
            setattr(self.application_session.model,
                    'addr2', self.verified_addr_2)
            setattr(self.application_session.model,
                    'city', self.verified_city)
            setattr(self.application_session.model,
                    'state', self.verified_state)
            setattr(self.application_session.model,
                    'zip_code', self.verified_zip_code)
        return super().form_valid(form)


class AddressMissingAptView(TemplateView, CcfView):
    template_name = 'address_missing_apt.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.application_session.model.usps_standardized:
            next_url = reverse('usps-modified-address')
        else:
            next_url = reverse('contact-info')
        context['next_url'] = next_url
        return context


class AddressUnverifiedView(TemplateView, CcfView):
    template_name = 'address_unverified.html'


class ContactView(ApplicationView):
    template_name = 'contact.html'
    form_class = ContactForm

    def form_valid(self, form):
        """
        Once the form has been validated, concatenate country code and phone
        digits to store the final phone number in the model.
        """
        cleaned_phone = clean_phone_number(form.cleaned_data['phone_digits'])
        setattr(self.application_session.model, 'phone_number', cleaned_phone)
        return super().form_valid(form)


class SignatureView(ApplicationView):
    template_name = 'signature.html'
    form_class = SignatureForm


class ReviewView(ApplicationView):
    template_name = 'review.html'
    form_class = ReviewForm

    def form_valid(self, form):
        try:
            (success, error) = submit_application(
                self.application_session.model,
                ip_address=self.ip_address)
        except Exception as e:
            form.add_error(None, _('other_application_submission_errors').format(
                CONFIG['customer_service_phone_number']))
            LOGGER.error('#ApplicationSubmission: %s', e)
            return super().form_invalid(form)
        else:
            if success:
                response = super().form_valid(form)
                notification.send_text(
                    self.application_session.model, notification.TextType.SUBMISSION)
                del self.request.session['application_session']
                return response
            else:
                # TODO(lirongliu): Surface an error message here
                # To invalidate a form, it needs to have an error.
                form.add_error(None, error)
                LOGGER.error('#ApplicationSubmission: %s', error)
                return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        phone_number = self.application_session.model.phone_number
        context['phone_number_display'] = "%s (%s) %s-%s" % (
            phone_number[:2], phone_number[2:5], phone_number[5:8],
            phone_number[8:])
        return context


class DisclosureView(CheckView):
    template_name = 'disclosure.html'
    form_class = DisclosureForm


class ConfirmationView(ApplicationView):
    template_name = 'confirmation.html'
    form_class = SignatureForm


class NoQualifyView(TemplateView, CcfView):
    template_name = "noqualify.html"


class NoVoucherCodeView(TemplateView, CcfView):
    template_name = "novouchercode.html"


class UnknownErrorView(TemplateView, CcfView):
    template_name = "unknownerror.html"

    @classmethod
    def get_rendered_view(cls, status_code):
        as_view_fn = cls.as_view(status_code=status_code)

        def view_fn(request, exception):
            response = as_view_fn(request)
            response.render()
            return response

        return view_fn


class ServerErrorView(TemplateView, CcfView):
    template_name = "unknownerror.html"

    @classmethod
    def get_rendered_view(cls, status_code):
        as_view_fn = cls.as_view(status_code=status_code)

        def view_fn(request):
            response = as_view_fn(request)
            response.render()
            return response

        return view_fn
