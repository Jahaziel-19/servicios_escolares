from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth import update_session_auth_hash, logout
from django.urls import reverse_lazy
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from .forms_auth import AlumnoLoginForm, AlumnoPasswordResetForm
from datos_academicos.forms_servicios import ServiciosPerfilForm
from .models import Alumno, Calificacion, PeriodoEscolar
from procedimientos.models import Tramite


def alumno_login_view(request):
    """
    Vista de login para alumnos.
    """
    if request.user.is_authenticated and hasattr(request.user, 'alumno'):
        return redirect('datos_academicos:alumno_dashboard')
    
    form = AlumnoLoginForm()
    
    if request.method == 'POST':
        form = AlumnoLoginForm(data=request.POST)
        if form.is_valid():
            # Limpiar posibles datos en sesión no serializables (p.ej., del importador)
            try:
                request.session.pop('datos_importacion', None)
            except Exception:
                # Si hay algún problema accediendo a la sesión, continuar sin bloquear el login
                pass
            user = form.get_user()
            login(request, user)

            messages.success(request, f'¡Bienvenido, {user.first_name}! {request.user}')
            
            
            # Redirigir a la página solicitada o al dashboard
            next_url = request.GET.get('next', 'datos_academicos:alumno_dashboard')
            return redirect(next_url)
    
    context = {
        'form': form,
        'title': 'Acceso para Alumnos'
    }
    return render(request, 'datos_academicos/auth/login.html', context)


def alumno_logout_view(request):
    """
    Vista de logout para alumnos.
    """
    if request.user.is_authenticated:
        messages.info(request, 'Has cerrado sesión correctamente.')
    logout(request)
    return redirect('datos_academicos:alumno_login')


@login_required
def alumno_dashboard_view(request):
    """
    Dashboard principal para alumnos autenticados.
    """
    # Verificar que el usuario pertenezca al grupo 'Alumno'
    if not request.user.groups.filter(name='Alumno').exists():
        messages.error(request, 'Acceso no autorizado. Solo alumnos pueden acceder a esta sección.')
        return redirect('datos_academicos:alumno_login')
    
    # Obtener el alumno asociado al usuario
    try:
        alumno = Alumno.objects.get(matricula=request.user.username)
    except Alumno.DoesNotExist:
        messages.error(request, 'No se encontró información del alumno.')
        return redirect('datos_academicos:alumno_login')
    
    # Obtener período escolar activo
    periodo_activo = PeriodoEscolar.objects.filter(activo=True).first()
    
    # Estadísticas del alumno
    total_calificaciones = Calificacion.objects.filter(alumno=alumno).count()
    promedio_general = alumno.calcular_promedio()
    creditos_aprobados = alumno.calcular_creditos_aprobados()
    creditos_totales = alumno.carrera.creditos_totales
    
    # Progreso académico
    progreso_creditos = (creditos_aprobados / creditos_totales * 100) if creditos_totales > 0 else 0
    
    # Calificaciones recientes (últimas 5)
    calificaciones_recientes = Calificacion.objects.filter(
        alumno=alumno
    ).select_related('materia', 'periodo_escolar').order_by('-id')[:5]
    
    # Trámites del alumno
    tramites_pendientes = Tramite.objects.filter(
        alumno=alumno,
        estado='Pendiente'
    ).count()
    
    tramites_recientes = Tramite.objects.filter(
        alumno=alumno
    ).order_by('-fecha_solicitud')[:3]
    
    # Información del semestre actual
    semestre_actual = alumno.semestre
    materias_semestre = alumno.carrera.materiacarrera_set.filter(
        semestre=semestre_actual
    ).count()
    
    # Datos para gráficos
    calificaciones_por_semestre = []
    for i in range(1, semestre_actual + 1):
        materias_semestre_i = Calificacion.objects.filter(
            alumno=alumno,
            materia__materiacarrera__semestre=i,
            materia__materiacarrera__carrera=alumno.carrera
        )
        if materias_semestre_i.exists():
            promedio_semestre = materias_semestre_i.aggregate(
                promedio=Avg('calificacion')
            )['promedio']
            calificaciones_por_semestre.append({
                'semestre': i,
                'promedio': round(float(promedio_semestre or 0), 2)
            })
    
    context = {
        'alumno': alumno,
        'periodo_activo': periodo_activo,
        'total_calificaciones': total_calificaciones,
        'promedio_general': round(promedio_general, 2),
        'creditos_aprobados': creditos_aprobados,
        'creditos_totales': creditos_totales,
        'progreso_creditos': round(progreso_creditos, 1),
        'calificaciones_recientes': calificaciones_recientes,
        'tramites_pendientes': tramites_pendientes,
        'tramites_recientes': tramites_recientes,
        'semestre_actual': semestre_actual,
        'materias_semestre': materias_semestre,
        'calificaciones_por_semestre': calificaciones_por_semestre,
        'title': 'Mi Dashboard'
    }
    
    return render(request, 'datos_academicos/auth/dashboard.html', context)


@login_required
def alumno_calificaciones_view(request):
    """
    Vista para mostrar todas las calificaciones del alumno.
    """
    # Verificar que el usuario pertenezca al grupo 'Alumno'
    if not request.user.groups.filter(name='Alumno').exists():
        messages.error(request, 'Acceso no autorizado. Solo alumnos pueden acceder a esta sección.')
        return redirect('datos_academicos:alumno_login')
    
    # Obtener el alumno asociado al usuario
    try:
        alumno = Alumno.objects.get(matricula=request.user.username)
    except Alumno.DoesNotExist:
        messages.error(request, 'No se encontró información del alumno.')
        return redirect('datos_academicos:alumno_login')
    
    # Obtener calificaciones agrupadas por semestre
    calificaciones = Calificacion.objects.filter(
        alumno=alumno
    ).select_related('materia', 'periodo_escolar').order_by(
        'materia__materiacarrera__semestre', 'materia__nombre'
    )
    
    # Agrupar por semestre
    calificaciones_por_semestre = {}
    for calificacion in calificaciones:
        semestre = calificacion.materia.materiacarrera_set.filter(
            carrera=alumno.carrera
        ).first()
        semestre_num = semestre.semestre if semestre else 0
        
        if semestre_num not in calificaciones_por_semestre:
            calificaciones_por_semestre[semestre_num] = []
        
        calificaciones_por_semestre[semestre_num].append(calificacion)
    
    # Calcular estadísticas
    promedio_general = alumno.calcular_promedio()
    total_materias = calificaciones.count()
    materias_aprobadas = calificaciones.filter(calificacion__gte=6.0).count()
    materias_reprobadas = calificaciones.filter(calificacion__lt=6.0).count()
    
    context = {
        'alumno': alumno,
        'calificaciones_por_semestre': dict(sorted(calificaciones_por_semestre.items())),
        'promedio_general': round(promedio_general, 2),
        'total_materias': total_materias,
        'materias_aprobadas': materias_aprobadas,
        'materias_reprobadas': materias_reprobadas,
        'title': 'Mis Calificaciones'
    }
    
    return render(request, 'datos_academicos/auth/calificaciones.html', context)


@login_required
def alumno_tramites_view(request):
    """
    Vista para mostrar los trámites del alumno.
    """
    # Verificar que el usuario pertenezca al grupo 'Alumno'
    if not request.user.groups.filter(name='Alumno').exists():
        messages.error(request, 'Acceso no autorizado. Solo alumnos pueden acceder a esta sección.')
        return redirect('datos_academicos:alumno_login')
    
    # Obtener el alumno asociado al usuario
    try:
        alumno = Alumno.objects.get(matricula=request.user.username)
    except Alumno.DoesNotExist:
        messages.error(request, 'No se encontró información del alumno.')
        return redirect('datos_academicos:alumno_login')
    
    
    # Obtener trámites del alumno
    tramites = Tramite.objects.filter(
        alumno=alumno
    ).order_by('-fecha_solicitud')
    
    # Estadísticas de trámites
    total_tramites = tramites.count()
    # Considerar estados equivalentes para pendientes y completados
    tramites_pendientes = tramites.filter(estado__in=['Pendiente', 'En proceso']).count()
    tramites_completados = tramites.filter(estado__in=['Completado', 'Procesado']).count()
    tramites_rechazados = tramites.filter(estado='Rechazado').count()
    
    context = {
        'alumno': alumno,
        'tramites': tramites,
        'total_tramites': total_tramites,
        'tramites_pendientes': tramites_pendientes,
        'tramites_completados': tramites_completados,
        'tramites_rechazados': tramites_rechazados,
        'title': 'Mis Trámites'
    }
    
    return render(request, 'datos_academicos/auth/tramites.html', context)



@login_required
def alumno_perfil_view(request):
    """
    Vista para mostrar y editar el perfil del alumno.
    """
    # Verificar que el usuario pertenezca al grupo 'Alumno'
    if not request.user.groups.filter(name='Alumno').exists():
        messages.error(request, 'Acceso no autorizado. Solo alumnos pueden acceder a esta sección.')
        return redirect('datos_academicos:alumno_login')
    
    # Obtener el alumno asociado al usuario
    try:
        alumno = Alumno.objects.get(matricula=request.user.username)
    except Alumno.DoesNotExist:
        messages.error(request, 'No se encontró información del alumno.')
        return redirect('datos_academicos:alumno_login')
    
    context = {
        'alumno': alumno,
        'title': 'Mi Perfil'
    }
    
    return render(request, 'datos_academicos/auth/perfil.html', context)


# ================== AUTENTICACIÓN DE SERVICIOS ESCOLARES ==================
def servicios_login_view(request):
    """
    Vista de login para usuarios de Servicios Escolares (personal/administrativos).
    Usa el sistema estándar de autenticación de Django con username y password.
    Requiere que el usuario tenga permisos (is_staff) o pertenezca al grupo 'ServiciosEscolares'.
    """
    # Si ya está autenticado y tiene perfil de servicios, redirigir al dashboard
    if request.user.is_authenticated and (
        request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name__in=['ServiciosEscolares', 'Servicios Escolares']).exists()
    ):
        next_url = request.GET.get('next') or 'datos_academicos:dashboard'
        return redirect(next_url)

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            # Validar permisos para Servicios Escolares
            if user.is_staff or user.is_superuser or user.groups.filter(name__in=['ServiciosEscolares', 'Servicios Escolares']).exists():
                login(request, user)
                messages.success(request, f"¡Bienvenido, {user.get_full_name() or user.username}!")
                next_url = request.POST.get('next') or request.GET.get('next') or 'datos_academicos:dashboard'
                return redirect(next_url)
            else:
                messages.error(request, 'Tu cuenta no tiene permisos de Servicios Escolares.')
        else:
            messages.error(request, 'Usuario o contraseña inválidos.')

    context = {
        'form': form,
        'title': 'Acceso Servicios Escolares'
    }
    return render(request, 'datos_academicos/auth/servicios_login.html', context)


# ================== PERFIL DE SERVICIOS ESCOLARES ==================
@login_required(login_url=reverse_lazy('datos_academicos:servicios_login'))
def servicios_perfil_view(request):
    """Perfil del usuario de Servicios Escolares: edición de datos y cambio de contraseña."""
    user = request.user
    # Guard de permisos de Servicios Escolares
    if not (user.is_staff or user.is_superuser or user.groups.filter(name__in=['ServiciosEscolares', 'Servicios Escolares']).exists()):
        messages.error(request, 'Acceso restringido: solo personal de Servicios Escolares.')
        return redirect('datos_academicos:servicios_login')

    perfil_form = ServiciosPerfilForm(instance=user)
    pwd_form = PasswordChangeForm(user)

    if request.method == 'POST':
        scope = request.POST.get('_scope')
        if scope == 'update_profile':
            perfil_form = ServiciosPerfilForm(request.POST, instance=user)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('datos_academicos:servicios_perfil')
            else:
                messages.error(request, 'Revisa los datos del perfil.')
        elif scope == 'change_password':
            pwd_form = PasswordChangeForm(user, request.POST)
            if pwd_form.is_valid():
                pwd_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('datos_academicos:servicios_perfil')
            else:
                messages.error(request, 'No fue posible actualizar la contraseña. Verifica los campos.')
        elif scope == 'reset_password_email':
            # Enviar enlace de restablecimiento de contraseña al correo del usuario
            if not user.email:
                messages.error(request, 'No se encontró un correo asociado a tu cuenta.')
            else:
                form = PasswordResetForm({'email': user.email})
                if form.is_valid():
                    form.save(
                        request=request,
                        use_https=request.is_secure(),
                        email_template_name='registration/password_reset_email.html',
                        subject_template_name='registration/password_reset_subject.txt'
                    )
                    messages.success(request, 'Hemos enviado un enlace de restablecimiento a tu correo.')
                else:
                    messages.error(request, 'No fue posible enviar el correo de restablecimiento.')

    context = {
        'title': 'Mi Perfil',
        'theme_name': 'servicios',
        'perfil_form': perfil_form,
        'pwd_form': pwd_form,
        # Variables del template admin_material adaptadas al usuario
        'username': user.get_full_name() or user.username,
        'nombre_completo': user.get_full_name() or '—',
        'email': user.email or '—',
        'telefono': getattr(user, 'phone', '—'),
        'ubicacion': getattr(user, 'location', '—'),
        'extension': getattr(user, 'extension', '—'),
        'mensajes_recientes': [],
        'procesos_destacados': [],
    }
    return render(request, 'datos_academicos/servicios/perfil.html', context)


@login_required
def servicios_logout_view(request):
    """Cierra sesión del personal de Servicios Escolares y redirige al login."""
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('datos_academicos:servicios_login')