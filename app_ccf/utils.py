import logging
import unidecode

from django.conf import settings
import urllib.request
import xml.etree.ElementTree as ET
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

LOGGER = logging.getLogger(__name__)


def verify_usps_addr(entered_addr_1, entered_addr_2, entered_city, entered_state, entered_zip):
    requestXML = """<?xml version="1.0" encoding="UTF-8" ?>
    <AddressValidateRequest USERID="%s">
        <Address>
            <Address1>%s</Address1>
            <Address2>%s</Address2>
            <City>%s</City>
            <State>%s</State>
            <Zip5>%s</Zip5>
            <Zip4/>
        </Address>
    </AddressValidateRequest>""" % (settings.USPS_USER_ID, entered_addr_2,
                                    entered_addr_1, entered_city, entered_state,
                                    entered_zip)
    request_args = {
        'API': 'Verify',
        'XML': requestXML
    }

    url = "https://secure.shippingapis.com/ShippingAPI.0dll?" + \
        urllib.parse.urlencode(request_args)
    response = urllib.request.urlopen(url)
    if response.getcode() != 200:
        LOGGER.error('#UspsHttpRrror: ' + response.info())
        raise Exception('USPS HTTP error')

    contents = response.read()
    root = ET.fromstring(contents)
    for address in root.findall('Address'):
        # There should only be one <Address> tag, return the first one.
        error_description = ""
        if address.find("Error"):
            error_description = address.find("Error").findtext("Description",
                                                               default="")
        return (address.findtext("Address2", default=""),
                address.findtext("Address1", default=""),
                address.findtext("City", default=""),
                address.findtext("State", default=""),
                address.findtext("Zip5", default=""),
                address.findtext("ReturnText", default=""),
                error_description)
