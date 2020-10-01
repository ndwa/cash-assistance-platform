from django.urls import path, re_path
from django.conf.urls.i18n import i18n_patterns

from . import views

urlpatterns = [
    path('language', views.LanguageView.as_view(), name='language'),
    re_path(
        r'^language/(?P<accesscode>([a-zA-Z]{3}-[a-zA-Z]{3}-[a-zA-Z]{3}))/$',
        views.LanguageView.as_view(),
        name='language'
    ),
    path('welcome', views.WelcomeView.as_view(next_name='requirements',
                                              previous_name='language', step_number=1), name='welcome'),
    path('requirements', views.RequirementsView.as_view(next_name='accesscode',
                                                        previous_name='welcome',
                                                        invalid_url='do-not-qualify',
                                                        step_number=2), name='requirements'),
    path('accesscode', views.VoucherCodeView.as_view(next_name='profile',
                                                     previous_name='requirements', step_number=3), name='accesscode'),
    path('profile', views.ProfileView.as_view(next_name='additional-info',
                                              previous_name='accesscode', step_number=4), name='profile'),
    path('additional-info', views.HouseholdView.as_view(next_name='mailing-address',
                                                        previous_name='profile', step_number=5), name='additional-info'),
    path('mailing-address', views.AddressView.as_view(next_name='contact-info',
                                                      previous_name='additional-info', step_number=6), name='mailing-address'),
    path('usps-modified-address', views.AddressVerifyView.as_view(next_name='contact-info',
                                                                  previous_name='mailing-address', step_number=6), name='usps-modified-address'),
    path('usps-missing-apt', views.AddressMissingAptView.as_view(step_number=6),
         name='usps-missing-apt'),
    path('usps-cannot-verify', views.AddressUnverifiedView.as_view(step_number=6),
         name='usps-cannot-verify'),
    path('contact-info', views.ContactView.as_view(next_name='alia-disclosure',
                                                   previous_name='mailing-address', step_number=7), name='contact-info'),
    path('alia-disclosure', views.DisclosureView.as_view(next_name='terms-and-conditions',
                                                         previous_name='contact-info', step_number=8), name='alia-disclosure'),
    path('terms-and-conditions', views.SignatureView.as_view(next_name='review',
                                                             previous_name='alia-disclosure', step_number=9), name='terms-and-conditions'),
    path('review', views.ReviewView.as_view(next_name='success',
                                            previous_name='terms-and-conditions', step_number=10), name='review'),
    path('success', views.ConfirmationView.as_view(next_name='language',
                                                   previous_name='review'), name='success'),
    path('do-not-qualify', views.NoQualifyView.as_view(), name='do-not-qualify'),
    path('no-code', views.NoVoucherCodeView.as_view(), name='no-code'),
]
