from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from two_factor.views.mixins import OTPRequiredMixin


class StaffRequiredMixin(OTPRequiredMixin, LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_active:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

class SuperUserRequiredMixin(StaffRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser or not request.user.is_active:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
