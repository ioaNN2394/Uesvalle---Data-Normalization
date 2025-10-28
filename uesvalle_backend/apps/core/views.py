"""
Vistas para la aplicación core (health checks, estado general del sistema)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db import connection


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
