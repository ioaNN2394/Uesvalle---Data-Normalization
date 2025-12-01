#!/usr/bin/env bash
# Script de build para Render
# Este script se ejecuta durante el proceso de build

set -o errexit  # Salir si hay errores

echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --no-input

echo "🗄️ Ejecutando migraciones..."
python manage.py migrate --no-input

echo "✅ Build completado!"
