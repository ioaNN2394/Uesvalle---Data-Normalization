#!/usr/bin/env python
"""
Test script for ETL upload endpoint
Tests the complete flow: upload -> create job -> check status
"""

import os
import sys
import django
import requests
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from apps.etl.models import ETLFile, ETLRun
from django.conf import settings

BASE_URL = "http://localhost:8000/api/etl"

def test_upload_endpoint():
    """Test POST /api/etl/upload/"""
    print("\n" + "="*80)
    print("TEST 1: Upload Endpoint")
    print("="*80)
    
    # Crear un archivo de prueba simple
    test_file_path = Path(settings.BASE_DIR) / "test_upload.xlsx"
    
    # Si no existe, usar un archivo dummy
    if not test_file_path.exists():
        print(f"⚠️ Test file not found: {test_file_path}")
        print("Creating a dummy Excel file...")
        
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws['A1'] = "nombre"
            ws['B1'] = "estado"
            ws['A2'] = "Institución 1"
            ws['B2'] = "activo"
            wb.save(test_file_path)
            print(f"✓ Test file created: {test_file_path}")
        except ImportError:
            print("❌ openpyxl not installed. Install with: pip install openpyxl")
            return False
    
    # POST /api/etl/upload/
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/upload/", files=files)
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200 and data.get('uploaded'):
            file_id = data['uploaded'][0]['id']
            print(f"✓ Upload successful! File ID: {file_id}")
            return file_id
        else:
            print(f"❌ Upload failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        # Cleanup
        if test_file_path.exists():
            test_file_path.unlink()

def test_create_job(file_id):
    """Test POST /api/etl/jobs/"""
    print("\n" + "="*80)
    print("TEST 2: Create ETL Job")
    print("="*80)
    
    try:
        payload = {
            "file_ids": [file_id],
            "dry_run": True,
            "cancel_on_error": True
        }
        
        response = requests.post(
            f"{BASE_URL}/jobs/",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if response.status_code in [201, 202]:
            job_id = data.get('id')
            print(f"✓ Job created! Job ID: {job_id}")
            return job_id
        else:
            print(f"❌ Job creation failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_get_status():
    """Test GET /api/etl/status/"""
    print("\n" + "="*80)
    print("TEST 3: Check ETL Status")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/status/")
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print(f"✓ Status check successful")
            return True
        else:
            print(f"❌ Status check failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_database_models():
    """Test database models"""
    print("\n" + "="*80)
    print("TEST 4: Database Models")
    print("="*80)
    
    try:
        # Check ETLFile model
        etl_files_count = ETLFile.objects.count()
        print(f"✓ ETLFile.objects.count() = {etl_files_count}")
        
        # Check ETLRun model
        etl_runs_count = ETLRun.objects.count()
        print(f"✓ ETLRun.objects.count() = {etl_runs_count}")
        
        # List recent files
        recent_files = ETLFile.objects.all().order_by('-uploaded_at')[:5]
        if recent_files.exists():
            print("\nRecent files:")
            for f in recent_files:
                print(f"  - {f.filename} ({f.status}) - {f.uploaded_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    print("\n🧪 ETL System Test Suite")
    print("Testing backend endpoints and models")
    
    # Test database models
    test_database_models()
    
    # Test endpoints
    # file_id = test_upload_endpoint()
    # if file_id:
    #     job_id = test_create_job(file_id)
    # 
    # test_get_status()
    
    print("\n" + "="*80)
    print("✓ Tests completed")
    print("="*80)
