from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.conf import settings


def get_translation_in(language, s):
    with translation.override(language):
        return translation.gettext(s)


CONFIG = {
    'languages': ('en', 'es'),
    'site_classname': 'ccf-myalia-org',
    'fund_name': _('ccf_fund_name'),
    'fund_name_es': get_translation_in('es', 'ccf_fund_name'),
    'fund_name_en': get_translation_in('en', 'ccf_fund_name'),
    'faq_link_url': _('ccf_faq_link'),
    'faq_link_text': _('ccf_faq'),
    'example_city_zip_code': '10006',
    'city_name': '',
    'payment_amount': '400',
    'customer_service_phone_number': '+1 888 888 8888',
    'eligibility_requirement_list': [_('requirements_eighteen_or_older'),
                                     _('requirements_income_source'),
                                     _('requirements_experiencing_hardship'),
                                     _('requirements_live_in_us')],
    'usio_card_design_id_en': '111',
    'usio_card_design_id_es': '222',
}
