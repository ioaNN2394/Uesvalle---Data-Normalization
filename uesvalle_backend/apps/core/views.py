"""
Vistas para la aplicación core (health checks, estado general del sistema)
"""
import uuid
import hashlib
import secrets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password

# Almacenamiento simple de sesiones en memoria (para desarrollo)
# En producción, usar Redis o base de datos
_sessions = {}


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint - verifica el estado del sistema
    Retorna estado de conexión a la BD y otros indicadores
    """
    payload = {
        "timestamp": timezone.now(),
        "status": "healthy",
        "database": "connected",
        "models": "ok",
    }
    
    try:
        # Verificar conexión simple a la base de datos
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            if result[0] != 1:
                payload["database"] = "error"
                payload["status"] = "unhealthy"
    except Exception as e:
        payload["database"] = f"error: {str(e)}"
        payload["status"] = "unhealthy"
    
    status_code = 200 if payload["status"] == "healthy" else 503
    return Response(payload, status=status_code)


@api_view(["POST"])
@permission_classes([AllowAny])
def colaborador_login(request):
    """
    Endpoint para autenticar colaboradores.
    Verifica usuario y contraseña contra la tabla colaborador.
    """
    usuario = request.data.get('usuario', '').strip()
    password = request.data.get('password', '')
    
    if not usuario or not password:
        return Response(
            {'error': 'Usuario y contraseña son requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id, usuario, password, nombre, activo FROM "uesvalle"."colaborador" WHERE usuario = %s',
                [usuario]
            )
            row = cursor.fetchone()
            
            if not row:
                return Response(
                    {'error': 'Usuario o contraseña incorrectos'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            col_id, col_usuario, col_password, col_nombre, col_activo = row
            
            if not col_activo:
                return Response(
                    {'error': 'Usuario desactivado'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Verificar contraseña (soporta hash Django o texto plano para migración)
            password_valid = False
            if col_password.startswith('pbkdf2_') or col_password.startswith('bcrypt'):
                password_valid = check_password(password, col_password)
            else:
                # Contraseña en texto plano (migración inicial)
                password_valid = (password == col_password)
            
            if not password_valid:
                return Response(
                    {'error': 'Usuario o contraseña incorrectos'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Generar token de sesión
            session_token = secrets.token_urlsafe(32)
            _sessions[session_token] = {
                'id': str(col_id),
                'usuario': col_usuario,
                'nombre': col_nombre,
                'timestamp': timezone.now().isoformat()
            }
            
            return Response({
                'success': True,
                'token': session_token,
                'usuario': col_usuario,
                'nombre': col_nombre
            })
            
    except Exception as e:
        return Response(
            {'error': f'Error de autenticación: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def colaborador_logout(request):
    """
    Endpoint para cerrar sesión de colaborador.
    """
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if token in _sessions:
        del _sessions[token]
    
    return Response({'success': True, 'message': 'Sesión cerrada'})


@api_view(["GET"])
@permission_classes([AllowAny])
def colaborador_verify(request):
    """
    Endpoint para verificar si una sesión es válida.
    """
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token or token not in _sessions:
        return Response(
            {'authenticated': False},
            status=status.HTTP_200_OK
        )
    
    session = _sessions[token]
    return Response({
        'authenticated': True,
        'usuario': session['usuario'],
        'nombre': session['nombre']
    })
