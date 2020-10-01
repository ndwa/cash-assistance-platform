from rest_framework.views import APIView
import ast
import collections
import csv
import django_filters
import unidecode
import urllib.parse

from collections import OrderedDict
from datetime import datetime, timezone
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.core.files import File
from django.db import transaction
from django.db.models.functions import Lower
from django.forms.models import model_to_dict
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.forms import Textarea
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View
from django.forms.models import modelform_factory
from django.views.generic.edit import CreateView
from django.views.generic.base import ContextMixin
from django.urls import reverse, reverse_lazy
from django_filters import (
    FilterSet,
    CharFilter,
    ChoiceFilter,
    DateFromToRangeFilter,
)
from django_filters.views import FilterView
from django_filters.widgets import RangeWidget

from app_ccf import common
from app_ccf import text_messages
from app_ccf.config import CONFIG
from app_ccf.models import (
    Application,
    VoucherCode,
    VoucherCodeBatch,
    PreapprovedAddress
)
from app_ccf import notification, utils


from .forms import VoucherCodeGenerateForm, PreapprovedAddressGenerateForm
from .mixins import (
    StaffRequiredMixin,
    SuperUserRequiredMixin,
)
from .models import AdminAction
from .utils import (
    generate_voucher_codes,
    import_voucher_codes,
    invalidate_voucher_codes_with_campaign,
    invalidate_voucher_codes_with_code_list
)


logger = logging.getLogger(__name__)


def ccf_bad_request_view(request, exception=None):
    messages.error(request, 'Bad request.')
    return render(
        request,
        'staff/40x.html',
        status=400
    )


def ccf_permssion_denied_view(request, exception=None):
    messages.error(request, 'You are not allowed to view this page.')
    return render(
        request,
        'staff/40x.html',
        status=403
    )


def ccf_not_found_view(request, exception=None):
    messages.error(request, 'Page not found.')
    return render(
        request,
        'staff/40x.html',
        status=404
    )


def staff_logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully')
    return redirect('staff:index')


# # # # # # # # # # # # # # # # # # # # # # # #
# Staff-required CCF application related views
# # # # # # # # # # # # # # # # # # # # # # # #

# TODO(stanfield): Consider moving to new filters.py file.
class ApplicationFilter(FilterSet):

    class Meta:
        model = Application
        fields = {'status': ['exact'],
                  'first_name': ['unaccent__icontains'],
                  'last_name': ['unaccent__icontains'],
                  'phone_number': ['icontains'],
                  'vouchercode_str': ['icontains'],
                  'addr1': ['icontains'],
                  'addr2': ['icontains'],
                  'city': ['iexact'],
                  'state': ['iexact'],
                  }


class IndexView(StaffRequiredMixin, TemplateView):
    template_name = 'staff/index.html'


def index_view(request):
    # This view is a FAKE login page that a potential hacker may use.
    # TODO: Additional config needed for notifying admins of login attempts.
    # TODO: customization of login pages.
    return HttpResponseRedirect(reverse('admin_honeypot:login',))


class PaginatedFilterViewMixin(View):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get filter params if in URL querystring
        if self.request.GET:
            querystring = self.request.GET.copy()
            if self.request.GET.get('page'):
                del querystring['page']
            context['params_GET'] = querystring.urlencode()
        return context


class AutoProcessApplicationsView(StaffRequiredMixin, TemplateView):

    def post(self, request, *args, **kwargs):
        common.auto_update_application_statuses()
        return HttpResponseRedirect(reverse('staff:payments'))


class ApplicationListView(StaffRequiredMixin, PaginatedFilterViewMixin, ListView):
    model = Application
    template_name = "staff/applications/application_list.html"
    ordering = '-submitted_date'
    paginate_by = 40

    def get_queryset(self):
        queryset = ApplicationFilter(
            self.request.GET,
            queryset=self.model.objects.all().order_by(self.ordering)
        ).qs
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = ApplicationFilter(
            self.request.GET, queryset=self.get_queryset())
        return context


class ApplicationDetailView(StaffRequiredMixin, DetailView):
    model = Application
    template_name = "staff/applications/application_details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['code'] = self.object.vouchercode
        return context


class LoginRequiredAfterPasswordChange(PasswordChangeView):
    @property
    def success_url(self):
        messages.success(
            self.request,
            'You have successfully updated you password.'
        )
        return reverse('staff:index')


# # # # # # # # # # # # # # # # # # # # # # # #
# Superuser-required views
# # # # # # # # # # # # # # # # # # # # # # # #


class SuperUserAccessedView(SuperUserRequiredMixin, TemplateView):
    template_name = None


class ApplicationUpdateView(StaffRequiredMixin, UpdateView):
    model = Application
    template_name = "staff/applications/application_update.html"
    form_class = modelform_factory(
        Application,
        fields=['first_name', 'last_name', 'phone_number', 'email', 'addr1',
                'addr2', 'city', 'state', 'zip_code', 'status', 'note'],
        widgets={'note': Textarea(attrs={'cols': 30,
                                         'rows': 3,
                                         'style': 'vertical-align: top'})})

    def get_form(self, *args, **kwargs):
        form = super(ApplicationUpdateView, self).get_form(*args, **kwargs)
        form.fields['note'].required = True
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rejection_message'] = text_messages.get_rejection_message()
        return context

    def get_success_url(self):
        return reverse('staff:application-detail', kwargs={'pk': self.object.pk})

    @transaction.atomic
    def form_valid(self, form):
        if form.has_changed():
            initial = model_to_dict(self.get_object())
            final = model_to_dict(self.object)
            admin_action = AdminAction(
                user=self.request.user.username,
                application=self.object,
                action_type=AdminAction.AdminActionType.MANUAL_EDIT,
                initial_app_json=initial,
                final_app_json=final
            )
            admin_action.save()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if (self.object.status == Application.ApplicationStatus.REJECTED and self.request.POST.get('send_rejection_notice')):
            notification.send_text(
                self.object, notification.TextType.REJECTION)
        return response


class PaymentsView(SuperUserRequiredMixin, TemplateView):
    template_name = "staff/applications/payments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sent_for_payment = Application.objects.filter(
            status=Application.ApplicationStatus.SENT_FOR_PAYMENT)
        approved = Application.objects.filter(
            status=Application.ApplicationStatus.APPROVED)
        applications_to_process = []
        if len(sent_for_payment) > 0:
            context['status'] = Application.ApplicationStatus.SENT_FOR_PAYMENT
            applications_to_process = sent_for_payment
        elif len(approved) > 0:
            context['status'] = Application.ApplicationStatus.APPROVED
            applications_to_process = approved

        context['applications_to_process'] = applications_to_process
        context['application_ids'] = [
            app.application_id.hex for app in applications_to_process]
        context['num_submitted'] = len(Application.objects.filter(
            status=Application.ApplicationStatus.SUBMITTED
        ))
        return context


class MarkAsPaidView(SuperUserAccessedView):

    def post(self, request, *args, **kwargs):
        application_ids = ast.literal_eval(
            request.POST.get('application_ids'))
        send_text_messages = request.POST.get('send_text_messages')
        common.update_application_statuses(
            application_ids, Application.ApplicationStatus.PAYMENT_CONFIRMED,
            bool(send_text_messages))
        return HttpResponseRedirect(reverse('staff:payments'))


class DownloadReportView(SuperUserRequiredMixin, APIView):

    def post(self, request, *args, **kwargs):
        requested_status = self.kwargs.get('status')
        application_ids = ast.literal_eval(
            request.POST.get('application_ids'))
        filename = 'tmp.csv'
        self.write_payments_csv(filename, requested_status)
        # When a download is requested for APPROVED applications, we update
        # their status to SENT_FOR_PAYMENT. This is a bit of a hack while we
        # still need CSVs to be uploaded for payment manually.
        # See payments user journeys here:
        # https://docs.google.com/document/d/1SbAEaOq-sxkPz1MYm01odUG7ktQEsVS8QklHHtHEEAI/
        if requested_status == Application.ApplicationStatus.APPROVED:
            applications = Application.objects.filter(pk__in=application_ids)
            common.update_application_statuses(
                applications, Application.ApplicationStatus.SENT_FOR_PAYMENT)
        return FileResponse(open(filename, 'rb'))

    def write_payments_csv(self, filename, status):
        applications = Application.objects.filter(
            status=status).order_by('-submitted_date')
        # Need to pre-load voucher codes because calling
        # VoucherCode.objects.get(code=application.voucher_code) on every
        # application is extremely slow
        # TODO (wups): remove this once the VoucherCode/Application model
        # relationship is fixed
        voucher_code_amount_map = {
            voucher_code.code: voucher_code.amount
            for voucher_code in VoucherCode.objects.filter(
                code__in=applications.values_list('vouchercode_str', flat=True))}
        rows = []
        for application in applications:
            load_amount = voucher_code_amount_map[application.vouchercode_str]
            card_design_id = CONFIG['usio_card_design_id_%s' %
                                    application.language]
            data = OrderedDict([
                ('cardType', 'Incentive-Card'),
                ('cardCount', '1'),
                ('shippingDestination', 'consumer'),
                ('firstName', application.first_name),
                ('lastName', application.last_name),
                ('address', application.addr1),
                ('address2', application.addr2),
                ('city', application.city),
                ('state', application.state),
                ('zipCode', application.zip_code),
                ('phone', application.phone_number.replace('+', '')),
                ('email', ''),  # not sharing emails for privacy
                ('loadAmount', str(load_amount)),
                ('loadNow', 'y'),
                ('distributorId', ''),
                ('cardDesignId', card_design_id),
                ('giftMessage', ''),
                ('giftSenderFirstName', ''),
                ('giftSenderLastName', ''),
                ('giftVirtualDeliveryMethod', ''),
                ('expiresIn', ''),
                ('reportData1', ''),
                ('reportData2', ''),
                ('reportData3', ''),
                ('Source', ''),
                ('Shipping Method', '3'),  # 3 = US_Postal_Service
            ])
            for key, value in data.items():
                data[key] = unidecode.unidecode(value)
            rows.append(data)
        fieldnames = rows[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


class VoucherCodeGenerateView(SuperUserRequiredMixin, CreateView, ListView, ContextMixin):
    template_name = "staff/voucher.html"
    form_class = VoucherCodeGenerateForm

    queryset = VoucherCodeBatch.objects.order_by('-created')
    paginate_by = 10

    def get_initial(self):
        initial = super().get_initial()
        initial['base_amount'] = CONFIG['payment_amount']
        return initial

    def get_success_url(self):
        return '{}?{}'.format(
            reverse('staff:voucher-gen'),
            urllib.parse.urlencode({
                'success': True,
                'num_codes_generated': self.object.num_codes,
                'batch_id': self.object.id,
            })
        )

    def get_context_data(self, **kwargs):
        self.object_list = VoucherCodeBatch.objects.order_by('-created')
        context = super(VoucherCodeGenerateView,
                        self).get_context_data(**kwargs)

        # Add vars for success alert if codes were just generated
        if (self.request.GET.get('success')) == str(True):
            context['success'] = True
            context['num_codes_generated'] = self.request.GET.get(
                'num_codes_generated')
            context['batch_id'] = self.request.GET.get(
                'batch_id')

        return context

    def form_valid(self, form):
        model = form.instance
        model.code_length = 9
        model.alphabet = 'abcdefghijkmnopqrstuvwxyz'
        model.user = self.request.user.username

        # Need to save before creating codes so the batch can be attached
        model.save()

        # Create codes and write to a temp file
        codes = generate_voucher_codes(
            model.num_codes, model.code_length, model.alphabet)
        filename = 'tmp.csv'
        with open(filename, 'w') as f:
            for code in codes:
                f.write('%s\n' % code)

        # Add codes to the database
        import_voucher_codes(filename, model)

        return super().form_valid(form)


class DownloadVoucherCodeBatchView(SuperUserRequiredMixin, TemplateView):
    template_name = "staff/voucher.html"

    def get(self, request, *args, **kwargs):
        batch_id = self.kwargs.get('batch_id')
        batch = VoucherCodeBatch.objects.get(id=batch_id)
        filename_raw = "codes_batch{id}_{campaign}_{ts}".format(
            id=batch_id,
            campaign=batch.campaign,
            ts=batch.created.strftime('%Y-%m-%d'))
        filename = slugify(filename_raw) + '.csv'  # clean filename
        with open(filename, 'w') as file:
            codes = batch.vouchercode_set.values_list('code', flat=True)
            file.writelines('\n'.join(codes))

        # Need 'rb' and not 'r' or you will get a very strange error
        return FileResponse(open(filename, 'rb'), filename=filename)


class VoucherCodeBatchInvalidateView(SuperUserRequiredMixin, TemplateView):
    template_name = "staff/voucher.html"

    def get(self, request, *args, **kwargs):
        batch_id = self.kwargs.get('batch_id')
        batch = VoucherCodeBatch.objects.get(id=batch_id)
        voucher_codes = batch.vouchercode_set.values_list('code', flat=True)
        invalidate_voucher_codes_with_code_list(voucher_codes)
        return HttpResponseRedirect(reverse('staff:voucher-gen'))


def get_choices(field):
    # We have to process this whole thing within a QuerySet because trying to
    # extract any values eagerly will get us a [ProgrammingError: relation
    # "app_ccf_vouchercodebatch" does not exist"]. The (field, field) part is to
    # pull out choice tuples in the form of (value, label) (see other usage in
    # ApplicationFilter above).
    return VoucherCodeBatch.objects.values_list(
        field, field).distinct().order_by(Lower(field))


class VoucherCodeFilter(FilterSet):
    batch__channel = ChoiceFilter(
        choices=get_choices('channel'),
        label='Channel')
    batch__affiliate = ChoiceFilter(
        choices=get_choices('affiliate'),
        label='Affiliate')
    batch__campaign = ChoiceFilter(
        choices=get_choices('campaign'),
        label='Campaign')

    class Meta:
        model = VoucherCode
        fields = {
            'code': ['icontains'],
        }


class VoucherCodeListView(StaffRequiredMixin, PaginatedFilterViewMixin, FilterView):
    template_name = "staff/voucher_list.html"
    queryset = VoucherCode.objects.filter(
        is_active=True).order_by('-batch__created')
    filterset_class = VoucherCodeFilter
    paginate_by = 40

    def get_context_data(self, **kwargs):
        context = super(VoucherCodeListView, self).get_context_data(**kwargs)
        context['code_list'] = ' '.join(
            [voucher_code.code for voucher_code in kwargs['object_list']])

        # Set 'empty' to True if the page load is not from an explicit search,
        # which we use to decide whether or not to show the "invalidate" button
        context['empty'] = dict(self.request.GET) == {}

        # Add vars for success alert if codes were just generated
        if (self.request.GET.get('success')) == str(True):
            context['success'] = True
            context['num_codes_invalidated'] = self.request.GET.get(
                'num_codes_invalidated')
        return context


class VoucherCodeListCreateApplicationRedirectView(SuperUserRequiredMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        code = self.kwargs.get('code')
        if settings.APP_TYPE == 'STAFF':
            # Redirect to non-staff version of site
            url = 'https://{}/{}/'.format(
                self.request.get_host().replace('staff-', ''), code)
        else:  # demo or local
            url = reverse('language', kwargs={'accesscode': code})
        return HttpResponseRedirect(url)


class VoucherCodeListInvalidateView(SuperUserRequiredMixin, TemplateView):
    template_name = "staff/voucher_list.html"

    def post(self, request, *args, **kwargs):
        voucher_codes = request.POST.get('submit-invalidate').split()
        invalidate_voucher_codes_with_code_list(voucher_codes)
        return HttpResponseRedirect(
            '{}?{}'.format(
                reverse('staff:voucher-list'),
                urllib.parse.urlencode({
                    'success': True,
                    'num_codes_invalidated': len(voucher_codes),
                })
            ))


class PreapprovedAddressGenerateView(SuperUserRequiredMixin, CreateView, ListView, ContextMixin):
    template_name = "staff/preapproved_addresses.html"
    form_class = PreapprovedAddressGenerateForm
    queryset = PreapprovedAddress.objects.order_by('addr1')

    def get_success_url(self):
        return '{}?{}'.format(
            reverse('staff:address-whitelist'),
            urllib.parse.urlencode({
                'success': True,
                'note': self.object.note,
            })
        )

    def get_context_data(self, **kwargs):
        self.object_list = PreapprovedAddress.objects.order_by('addr1')
        context = super(PreapprovedAddressGenerateView,
                        self).get_context_data(**kwargs)

        # Add vars for success alert if codes were just generated
        if (self.request.GET.get('success')) == str(True):
            context['success'] = True
            context['note'] = self.request.GET.get('note')

        return context
