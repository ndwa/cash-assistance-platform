from app_ccf.models import PreapprovedAddress, Application


class BaseDedupCheck:
    """
    Base class for checking Applications for duplicates.

    Subclasses should override get_test_value to return a value
    to be compared across applications for duplicates. They may
    optionally provide max_duplicates if the number of allowed
    duplicates is greater than 1.

    Args:
        error_message (str): The note to append to the application when the
            dedup check fails.
        max_duplicates (int): The number of applications that are allowed to
            share a common test value before the dedup check fails.
        new_status (Application.Status): The status to update the application
            to if the dedup check fails.

    """

    def __init__(self, error_message, max_duplicates=1,
                 new_status=Application.ApplicationStatus.NEEDS_REVIEW):
        self.max_duplicates = max_duplicates
        self.error_message = error_message
        self.new_status = new_status

    def get_max_duplicates(self):
        """Returns the max number of apps that may share the value tested."""
        return self.max_duplicates

    def get_error_message(self):
        """Returns the error message to use when duplicates are detected."""
        return self.error_message

    def is_preapproved(self, application):
        """Returns whether this application is exempted from this check."""
        return False

    def get_test_value(self, application):
        """Returns the standardized value to be tested for duplicates."""
        pass


class AddressDedupCheck(BaseDedupCheck):
    """Flags duplicate addresses across more than 5 apps for review."""

    def __init__(self):
        super().__init__(error_message='duplicate address', max_duplicates=3)

    def is_preapproved(self, application):
        return PreapprovedAddress.objects.filter(
            addr1=application.addr1, zip_code=application.zip_code).exists()

    def get_test_value(self, application):
        return '\n'.join([application.addr1,
                          application.city,
                          application.state,
                          application.zip_code])


class NamePhoneDedupCheck(BaseDedupCheck):
    """Rejects apps with the same first name, last name, and phone number."""

    def __init__(self):
        super().__init__(error_message='duplicate first/last/phone',
                         new_status=Application.ApplicationStatus.REJECTED)

    def get_test_value(self, application):
        return application.first_name.lower() + application.last_name.lower() + \
            application.phone_number
