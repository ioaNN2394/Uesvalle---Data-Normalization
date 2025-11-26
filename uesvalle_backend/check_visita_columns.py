import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from django.db import connection

def check_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'visita' AND table_schema = 'uesvalle';
        """)
        columns = cursor.fetchall()
        print("Columns in uesvalle.visita:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")

if __name__ == '__main__':
    check_columns()
