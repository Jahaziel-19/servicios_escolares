from django.contrib.auth.models import Group


def theme(request):
    """Determina el tema visual según el rol del usuario."""
    theme = "publico"
    u = getattr(request, "user", None)

    if u and u.is_authenticated:
        if u.is_superuser:
            theme = "superadmin"
        elif u.groups.filter(name__in=["ServiciosEscolares", "Servicios Escolares"]).exists():
            theme = "servicios"
        elif u.groups.filter(name__in=["Alumnos", "Estudiantes"]).exists():
            theme = "alumno"
        elif u.groups.filter(name__in=["Aspirantes"]).exists():
            theme = "aspirante"

    return {"theme_name": theme}