from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from admision.models import PeriodoAdmision, SolicitudAdmision
from admision.forms_publico import RegistroAspiranteForm


def _valid_curp():
    # Formato: 4 letras + 6 dígitos + H/M + 5 letras + [0-9A-Z] + dígito
    return "ABCD010203HABCDEX2"


def build_valid_payload(periodo):
    """Construye un payload válido dinámicamente a partir del formulario."""
    form = RegistroAspiranteForm(periodo=periodo)
    data = {}

    from django import forms

    for name, field in form.fields.items():
        # Reglas específicas por nombre
        if name == "curp":
            data[name] = _valid_curp()
            continue
        if name == "promedio_general":
            data[name] = "9.5"
            continue
        if "email" in name:
            data[name] = "aspirante.test@example.com"
            continue
        if "fecha" in name:
            data[name] = "2000-01-01"
            continue
        if "año" in name or "anio" in name:
            data[name] = 2020
            continue
        if "telefono" in name:
            data[name] = "5512345678"
            continue
        if "codigo_postal" in name:
            data[name] = "12345"
            continue

        # Por tipo de campo
        if isinstance(field, forms.BooleanField):
            data[name] = True
        elif isinstance(field, (forms.ChoiceField, forms.TypedChoiceField)):
            # Elegir la primera opción válida no vacía
            choices = list(getattr(field, "choices", []))
            choice_val = None
            for val, _label in choices:
                if val not in (None, ""):
                    choice_val = val
                    break
            # Si no hay opciones válidas y el campo no es requerido, dejar vacío
            data[name] = choice_val if choice_val is not None else ("" if not field.required else None)
        elif isinstance(field, forms.MultipleChoiceField):
            choices = list(getattr(field, "choices", []))
            vals = [val for val, _label in choices if val not in (None, "")]
            data[name] = vals[:1] if vals else ([] if not field.required else None)
        elif isinstance(field, (forms.IntegerField,)):
            data[name] = 1
        elif isinstance(field, (forms.FloatField,)):
            data[name] = 9.5
        elif isinstance(field, (forms.DecimalField,)):
            data[name] = "9.5"
        elif isinstance(field, (forms.DateField,)):
            data[name] = "2000-01-01"
        else:
            # CharField y otros
            data[name] = "TEST"

    # Asegurar aceptación de términos si existe
    if "acepta_terminos" in form.fields:
        data["acepta_terminos"] = True

    return data


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistroPublicoTests(TestCase):
    def setUp(self):
        now = timezone.now()
        periodo_tmp = PeriodoAdmision(nombre="Admisión Test", año=now.year)
        base = periodo_tmp.get_formulario_base_default()
        self.periodo = PeriodoAdmision.objects.create(
            nombre="Admisión Test",
            año=now.year,
            fecha_inicio=now - timedelta(days=1),
            fecha_fin=now + timedelta(days=30),
            activo=True,
            descripcion="Periodo de prueba",
            formulario_base=base,
        )
        self.client = Client()

    def test_registro_crea_solicitud_enviada(self):
        url = reverse("admision:admision_publico:registro_aspirante")
        payload = build_valid_payload(self.periodo)
        response = self.client.post(url, data=payload, follow=True)

        # Debe existir una solicitud creada
        self.assertEqual(SolicitudAdmision.objects.count(), 1)
        solicitud = SolicitudAdmision.objects.first()
        self.assertEqual(solicitud.estado, "enviada")
        self.assertEqual(solicitud.curp, payload["curp"])
        self.assertEqual(solicitud.email, payload["email"])

        # Debe redirigir a la página de éxito
        self.assertEqual(response.status_code, 200)
        self.assertIn("Registro Exitoso", response.content.decode())