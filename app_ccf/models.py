from django.db import models
from django.conf import settings
# Any user-facing text should be preppended with _ to enable localization
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.core.validators import EmailValidator, MinValueValidator, RegexValidator
from django.contrib.postgres.fields import ArrayField
from django.db import transaction

from datetime import datetime, timezone
import uuid

from shared.utils import no_special_chars_validator, street_address_validator
from shared.common import TypeOfWork


def get_datetime_now_utc():
    return datetime.now(timezone.utc)


class VoucherCodeCheckStatus(models.IntegerChoices):
    SUCCESS = 0
    CODE_NOT_FOUND = 1
    CODE_ALREADY_USED = 2
    CODE_EXPIRED = 3
    CODE_INVALIDATED = 4


class Application(models.Model):
    class AgeRange(models.TextChoices):
        RANGE__17 = '17', _('17_or_younger')
        RANGE__18_29 = '18-29', _('18-29')
        RANGE_30_49 = '30-49', _('30-49')
        RANGE_50_69 = '50-69', _('50-69')
        RANGE_70_PLUS = '70+', _('70_or_older')

    class HouseHoldIncome(models.TextChoices):
        UNDER_20K = '<20k', _('under_20k'),
        BETWEEN_20K_40K = '20,000-39,999', _(
            'between_20k_39k'),
        BETWEEN_40K_60K = '40,000-59,999', _(
            'between_40k_59k'),
        BETWEEN_60K_80K = '60,000-79,999', _(
            'between_60k_79k'),
        ABOVE_80K = '80,000+', _('above_80k'),

    class Language(models.TextChoices):
        ES = 'es', _('Español'),
        EN = 'en', _('English'),

    class ApplicationStatus(models.TextChoices):
        SUBMITTED = 'submitted'
        APPROVED = 'approved'
        NEEDS_REVIEW = 'needs_review'
        REJECTED = 'rejected'
        SENT_FOR_PAYMENT = 'sent_for_payment'
        PAYMENT_CONFIRMED = 'payment_confirmed'
        REISSUE_REQUESTED = 'reissue_requested'
        REISSUE_CONFIRMED = 'reissue_confirmed'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_status = self.status

    @classmethod
    @transaction.atomic
    def bulk_update_status(cls, applications, new_status):
        """Bulk updates the status of a list of Applications."""
        datetime_now_utc = datetime.now(timezone.utc)
        status_updates = []

        for app in applications:
            if app.submitted_date is None:
                raise ValueError(
                    'Cannot update statuses for an unsubmitted application: %s',
                    app.application_id)

            # We need to duplicate the save() logic a little bit here because
            # bulk_update doesn't call save().
            if app._last_status != new_status:
                app.status = new_status
                app.status_last_modified = datetime_now_utc
                status_updates.append(
                    StatusUpdate(status=new_status, date=datetime_now_utc,
                                 application=app)
                )

        cls.objects.bulk_update(
            applications, ['status', 'status_last_modified'], batch_size=30)
        StatusUpdate.objects.bulk_create(status_updates, batch_size=30)

        for app in applications:
            app._last_status = new_status

    @transaction.atomic
    def save(self, *args, **kwargs):
        datetime_now_utc = datetime.now(timezone.utc)
        if self.submitted_date is None:
            self.submitted_date = datetime_now_utc
        if self._state.adding or self.status != self._last_status:
            self._last_status = self.status
            self.status_last_modified = datetime_now_utc
            StatusUpdate(status=self.status, date=datetime_now_utc,
                         application=self).save()
        self.full_clean()
        super().save(*args, **kwargs)

    def get_full_address(self):
        if self.addr2:
            addr_lines = '\n'.join([self.addr1, self.addr2])
        else:
            addr_lines = self.addr1
        city_line = '%s, %s %s' % (self.city, self.state, self.zip_code)
        return '\n'.join([addr_lines, city_line])

    type_of_work = models.CharField(
        max_length=15,
        choices=TypeOfWork.choices,
        default=TypeOfWork.HOUSE_CLEANING,
        blank=True,
    )
    vouchercode_str = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    payment_confirmed_reminder_sent = models.BooleanField(default=False)
    age_range = models.CharField(
        max_length=6,
        choices=AgeRange.choices,
        default=AgeRange.RANGE__17,
    )
    household_size = models.SmallIntegerField(
        validators=[MinValueValidator(1)],
        null=True,
        blank=True
    )
    household_income = models.CharField(
        max_length=20,
        choices=HouseHoldIncome.choices,
        default=HouseHoldIncome.UNDER_20K,
    )
    ethnicity = ArrayField(
        models.CharField(max_length=50, blank=True),
        size=8,
        default=list,
        blank=True,
    )
    gender = ArrayField(
        models.CharField(max_length=50, blank=True),
        size=8,
        default=list,
        blank=True,
    )
    language = models.CharField(
        max_length=15,
        choices=Language.choices,
        default=Language.EN,
    )
    # Regex matches a phone number of at least 8 digits
    # https://stackoverflow.com/questions/14894899/what-is-the-minimum-length-of-a-valid-international-phone-number
    phone_number = models.CharField(max_length=50, validators=[
                                    RegexValidator("^[+][0-9]{8,}$", _('phone_number_incorrect_format'))])
    email = models.EmailField(blank=True, validators=[EmailValidator()])
    addr1 = models.CharField(max_length=200, validators=[
                             street_address_validator()])
    addr2 = models.CharField(max_length=100, blank=True,
                             validators=[street_address_validator()])
    city = models.CharField(max_length=100, validators=[
                            no_special_chars_validator()])
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=5)
    # True if the user provided a verified USPS address.
    usps_verified = models.BooleanField(default=False)
    # True if the user selected a standardized version of the address.
    usps_standardized = models.BooleanField(default=False)
    signature = models.CharField(max_length=200)

    application_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    submitted_date = models.DateTimeField()
    status = models.CharField(
        max_length=40,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    status_last_modified = models.DateTimeField(null=True)
    note = models.CharField(max_length=200, blank=True)


class StatusUpdate(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=40,
        choices=Application.ApplicationStatus.choices,
        default=Application.ApplicationStatus.SUBMITTED,
    )
    date = models.DateTimeField(auto_now_add=True)


class VoucherCodeBatch(models.Model):
    """
    Captures a batch of generated codes created together with common properties.

    Stores common fields among codes that were previously stored on the codes
    themselves.

    Fields:
      created: The date the batch was created, automatically set upon creation.
      user: The username of the staff portal user who created the batch.
      num_codes: The number of codes in the batch.
      code_length: The length of each code in the batch.
      alphabet: The set of characters the codes are created from.
      base_amount: The base dollar amount set for the batch.
      expiration_date: The date the codes are set to expire.
      affiliate: A text label indicating the affiliate the batch is associated
        with.
      campaign: A text label indicating the campaign the batch is associated
        with.
      channel: A text label indicating the channel the batch is associated
        with.
    """
    created = models.DateTimeField()
    user = models.CharField(max_length=20)

    num_codes = models.IntegerField(validators=[MinValueValidator(1)])

    code_length = models.IntegerField(validators=[MinValueValidator(1)])
    alphabet = models.CharField(max_length=100)
    base_amount = models.DecimalField(max_digits=7, decimal_places=2)
    expiration_date = models.DateTimeField(
        validators=[MinValueValidator(limit_value=get_datetime_now_utc)])

    affiliate = models.CharField(max_length=50)
    campaign = models.CharField(max_length=50)
    channel = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        datetime_now_utc = datetime.now(timezone.utc)
        if self.created is None:
            self.created = datetime_now_utc
        super().save(*args, **kwargs)


class VoucherCode(models.Model):
    """
    Stores a voucher code with its associated metadata.

    A submitted text code [my_code] is valid (can be redeemed) iff there is
    a VoucherCode entry [voucher_code] where [voucher_code.code == my_code]
    and [voucher_code.is_active == True] and [datetime.now() < expiration_date]
    and [voucher_code.application is None].

    When a voucher code is redeemed, application_id should be set to the
    application_id of the application that redeemed it.

    Fields:
      code: The text code. Allows up to 20 alphanumeric characters to support
        old and possibly future codes, but currently we are only generating and
        accepting 9-character codes using lowercase alphabetic letters,
        excluding 'l' (lowercase 'L').
      batch: The VoucherCodeBatch the code belongs to. Stores other fields
        common to all codes within the batch.
      added_amount: The dollar amount adjustment for this specific code. Total
        amount for this code = code.batch.base_amount + code.added_amount.
      is_active: True iff the code has not been manually invalidated.
      application_id: The application_id of the application that redeemed the
        code, if applicable.
    """
    code = models.CharField(
        max_length=20,
        primary_key=True,
        validators=[RegexValidator('^[A-z0-9]+$',
                                   _('voucher_code_invalid_format'))],
    )
    batch = models.ForeignKey(
        VoucherCodeBatch, on_delete=models.CASCADE, null=True)
    added_amount = models.DecimalField(max_digits=7, decimal_places=2)
    is_active = models.BooleanField(default=True)
    application = models.OneToOneField(
        Application, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def affiliate(self):
        return self.batch.affiliate

    @property
    def campaign(self):
        return self.batch.campaign

    @property
    def channel(self):
        return self.batch.channel

    @property
    def expiration_date(self):
        return self.batch.expiration_date

    @property
    def amount(self):
        return self.batch.base_amount + self.added_amount

    @property
    def code_formatted(self):
        return '%s-%s-%s' % (self.code[:3], self.code[3:6], self.code[6:])

    @classmethod
    def verify_code(cls, code):
        """Verifies if the given code string is valid to redeem.

        Returns:
            A VoucherCodeCheckStatus enum.
        """
        try:
            matched_code = cls.objects.get(code=code)
        except VoucherCode.DoesNotExist:
            return VoucherCodeCheckStatus.CODE_NOT_FOUND

        if matched_code.application:
            return VoucherCodeCheckStatus.CODE_ALREADY_USED
        # TODO (wups): Remove this case once data migration is done.
        elif Application.objects.filter(vouchercode_str=code).exists():
            return VoucherCodeCheckStatus.CODE_ALREADY_USED
        elif datetime.now(timezone.utc) >= matched_code.expiration_date:
            return VoucherCodeCheckStatus.CODE_EXPIRED
        elif not matched_code.is_active:
            return VoucherCodeCheckStatus.CODE_INVALIDATED
        return VoucherCodeCheckStatus.SUCCESS


class VoucherCodeAttempt(models.Model):

    class Action(models.IntegerChoices):
        VOUCHER_CODE_CHECK = 0
        APPLICATION_REVIEW = 1

    ip_address = models.GenericIPAddressField()
    action = models.IntegerField(choices=Action.choices)
    time = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=20)
    status = models.IntegerField(choices=VoucherCodeCheckStatus.choices)


class PreapprovedAddress(models.Model):
    """
    An address that has been preapproved as an affiliate or staff center.

    An application will skip the duplicate address fraud check if its address
    matches a preapproved address. Only the addr1 and zip_code fields are compared,
    but the city and state fields are included for clarity in the staff portal.
    """
    addr1 = models.CharField(max_length=200)
    zip_code = models.CharField(max_length=5)

    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['addr1', 'zip_code'], name='unique address')
        ]
