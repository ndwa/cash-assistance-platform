from django.urls import include, path

from . import views

app_name = 'staff'


application_patterns = [
    path('', views.ApplicationListView.as_view(), name='ccf-application-list'),
    path('<uuid:pk>/', views.ApplicationDetailView.as_view(),
         name='application-detail'),
    path('<uuid:pk>/update', views.ApplicationUpdateView.as_view(),
         name='application-update'),
]

payments_patterns = [
    path('', views.PaymentsView.as_view(), name='payments'),
    path('mark_as_paid/', views.MarkAsPaidView.as_view(),
         name='mark-as-paid'),
    path('auto_process_applications/',
         views.AutoProcessApplicationsView.as_view(), name='auto-process-applications'),
    path('<str:status>/', views.DownloadReportView.as_view(), name='download-report'),
]

voucher_patterns = [
    path('', views.VoucherCodeGenerateView.as_view(), name='voucher-gen'),
    path('csv/<str:batch_id>/',
         views.DownloadVoucherCodeBatchView.as_view(), name='download-voucher'),
    path('invalidate/<str:batch_id>/', views.VoucherCodeBatchInvalidateView.as_view(),
         name='voucher-batch-invalidate'),
    path('list/', views.VoucherCodeListView.as_view(), name='voucher-list'),
    path('list/create/<str:code>',
         views.VoucherCodeListCreateApplicationRedirectView.as_view(), name='create-app-redirect'),
    path('list/invalidate/', views.VoucherCodeListInvalidateView.as_view(),
         name='voucher-list-invalidate'),
]

address_patterns = [
    path('', views.PreapprovedAddressGenerateView.as_view(),
         name='address-whitelist'),
]

admin_auth_override_patterns = [
    path('password_change/', views.LoginRequiredAfterPasswordChange.as_view()),
]

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('accounts/', include(admin_auth_override_patterns)),
    path('address/', include(address_patterns)),
    path('applications/', include(application_patterns)),
    path('logout/', views.staff_logout_view, name='logout'),
    path('payments/', include(payments_patterns)),
    path('voucher/', include(voucher_patterns)),
]
