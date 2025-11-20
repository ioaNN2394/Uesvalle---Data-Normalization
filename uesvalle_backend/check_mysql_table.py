import os
import sys
import django
import pandas as pd
from django.db import connections

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

def check_mysql_table():
    print("--- Verificando conexión a MySQL y tabla 'visitas_instituciones_educativos' ---")
    
    try:
        conn = connections['source_mysql']
        
        # Ensure connection
        if conn.connection is None:
            conn.connect()
        print("✅ Conexión a MySQL establecida.")
        
        table_name = 'visitas_instituciones_educativos'
        
        # Check if table exists
        with conn.cursor() as cursor:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            result = cursor.fetchone()
            
            if result:
                print(f"✅ Tabla '{table_name}' encontrada.")
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                count = cursor.fetchone()[0]
                print(f"📊 Registros en tabla: {count}")
                
                # Get columns
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = [col[0] for col in cursor.fetchall()]
                print(f"📋 Columnas: {', '.join(columns[:5])}...")
                
                # Try reading with pandas
                print("🔄 Intentando leer 5 registros con pandas...")
                df = pd.read_sql(f"SELECT * FROM `{table_name}` LIMIT 5", conn.connection)
                print(f"✅ Lectura exitosa. DataFrame shape: {df.shape}")
                print(df.head())
                
            else:
                print(f"❌ Tabla '{table_name}' NO encontrada.")
                
                # List available tables
                cursor.execute("SHOW TABLES")
                tables = [r[0] for r in cursor.fetchall()]
                print(f"ℹ️ Tablas disponibles: {', '.join(tables)}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_mysql_table()
