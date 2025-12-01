# Modelos base o compartidos
import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Colaborador(models.Model):
    """
    Modelo para usuarios colaboradores que tienen acceso a funciones administrativas.
    (ETL, Notificaciones, Reportes)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.CharField(max_length=100, unique=True, verbose_name="Usuario")
    password = models.CharField(max_length=255, verbose_name="Contraseña")
    nombre = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre completo")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        db_table = 'uesvalle"."colaborador'
        managed = True
    
    def __str__(self):
        return self.usuario
    
    def set_password(self, raw_password):
        """Encripta y guarda la contraseña."""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Verifica si la contraseña proporcionada coincide."""
        return check_password(raw_password, self.password)
