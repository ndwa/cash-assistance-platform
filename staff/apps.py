from django.apps import AppConfig


class StaffAppConfig(AppConfig):
    name = 'staff'

    def ready(self):
        from . import signals
