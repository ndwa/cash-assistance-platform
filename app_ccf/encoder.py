from datetime import datetime
from json import JSONEncoder
from uuid import UUID

class ApplicationEncoder(JSONEncoder):
    """Used to resolve the serialization issue for objects with certain fields.

    Note that deserialization is working fine without this encoder class.
    """

    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        if isinstance(obj, datetime):
            # datetime.datetime needs to be manually serialized
            return str(obj)
        return JSONEncoder.default(self, obj)