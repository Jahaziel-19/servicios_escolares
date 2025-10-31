import json
from django.core.serializers.json import DjangoJSONEncoder


class DjangoJSONEncoderSerializer:
    """
    Serializador de sesiones basado en JSON que utiliza DjangoJSONEncoder
    para soportar tipos como datetime, date y Decimal.
    Debe exponer métodos estáticos dumps y loads.
    """

    @staticmethod
    def dumps(obj):
        # Devolver bytes para evitar errores en firmados/HMAC
        return json.dumps(obj, cls=DjangoJSONEncoder).encode('utf-8')

    @staticmethod
    def loads(data):
        # Aceptar bytes o str
        if isinstance(data, (bytes, bytearray)):
            data = data.decode('utf-8')
        return json.loads(data)