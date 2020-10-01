from .models import AdminAction
from app_ccf.models import Application
from app_ccf import base_test
from django.forms.models import model_to_dict
from shared.test_utils import DEFAULT_CCF_APP_FIELDS


class AdminActionTests(base_test.CcfBaseTest):

    def test_changed_fields(self):
        app = Application(**DEFAULT_CCF_APP_FIELDS.copy())
        app.first_name = 'InitialFirst'
        app.addr2 = 'APT 1'
        initial = model_to_dict(app)

        # Make some changes
        app.first_name = 'ChangedFirst'
        app.addr2 = 'APT 1000'
        final = model_to_dict(app)

        admin_action = AdminAction(
            user='testuser',
            application=app,
            action_type=AdminAction.AdminActionType.MANUAL_EDIT,
            initial_app_json=initial,
            final_app_json=final
        )

        expected_changed_fields = [
            ('first_name', 'InitialFirst', 'ChangedFirst'),
            ('addr2', 'APT 1', 'APT 1000'),
        ]
        self.assertEqual(admin_action.changed_fields, expected_changed_fields)
