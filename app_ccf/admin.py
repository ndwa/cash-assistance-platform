from django.contrib import admin

from app_ccf import models as ccf_models

# Register your models here.
admin.site.register(ccf_models.Application)
admin.site.register(ccf_models.VoucherCode)
admin.site.register(ccf_models.VoucherCodeBatch)
admin.site.register(ccf_models.VoucherCodeAttempt)
admin.site.register(ccf_models.StatusUpdate)
