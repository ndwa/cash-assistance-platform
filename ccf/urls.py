"""ccf URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import (
    path,
    re_path,
    include
)
from django.views.generic import RedirectView

from two_factor.admin import AdminSiteOTPRequired
from two_factor.urls import urlpatterns as tf_urls

from app_ccf.views import LanguageView
import app_ccf

handler400 = app_ccf.views.UnknownErrorView.get_rendered_view(status_code=400)
handler403 = app_ccf.views.UnknownErrorView.get_rendered_view(status_code=403)
handler404 = app_ccf.views.UnknownErrorView.get_rendered_view(status_code=404)
handler500 = app_ccf.views.ServerErrorView.get_rendered_view(status_code=500)

admin.site.__class__ = AdminSiteOTPRequired

ccfpatterns = [
    re_path(
        r'^(?P<accesscode>([a-zA-Z]{3}-[a-zA-Z]{3}-[a-zA-Z]{3}))/$',
        LanguageView.as_view(),
        name='language'
    ),
    path('', LanguageView.as_view(), name='language'),
    path('language', LanguageView.as_view(), name='language'),
]

ccfpatterns += i18n_patterns(
    path('', include('app_ccf.urls')),
)

staffpatterns = [
    path('', include('staff.urls')),
    path('ssa/', admin.site.urls),
    path('accounts/', include('admin_honeypot.urls')),
    path('mfa/', include(tf_urls)),
]

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('session_security/', include('session_security.urls')),
]
# Based on app type variable, set urlpatterns
if settings.APP_TYPE == 'CCF':
    urlpatterns += ccfpatterns
elif settings.APP_TYPE == 'STAFF':
    urlpatterns += staffpatterns
else:  # Local/demo have access to staff urls directly from '/staff/'
    urlpatterns += ccfpatterns
    urlpatterns += [
        path('staff/', include(staffpatterns))
    ]

# https://docs.djangoproject.com/en/dev/ref/contrib/admin/#adminsite-attributes
admin.site.site_header = 'CCF administration'
admin.site.site_title = 'CCF site admin'


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
