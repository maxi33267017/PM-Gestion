#!/usr/bin/env python3
"""
Script para probar el login con CSRF token
"""

import requests
import re
from bs4 import BeautifulSoup

def test_login():
    """Probar el login con un usuario existente"""
    
    # URL del login
    login_url = "http://localhost:8000/login/"
    
    # Crear sesión para mantener cookies
    session = requests.Session()
    
    print("🔍 Probando acceso al login...")
    
    # 1. Obtener la página de login para extraer el token CSRF
    try:
        response = session.get(login_url)
        response.raise_for_status()
        print("✅ Página de login accesible")
        
        # Extraer el token CSRF del HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if csrf_token:
            csrf_value = csrf_token.get('value')
            print(f"✅ Token CSRF encontrado: {csrf_value[:20]}...")
        else:
            print("❌ No se encontró el token CSRF en el HTML")
            return False
            
    except Exception as e:
        print(f"❌ Error accediendo al login: {e}")
        return False
    
    # 2. Intentar hacer login con credenciales de prueba
    print("\n🔐 Intentando login...")
    
    # Datos de login (usar un usuario que sabemos que existe)
    login_data = {
        'csrfmiddlewaretoken': csrf_value,
        'username': 'admin@patagoniamaquinarias.com',  # Usuario que cargamos
        'password': 'admin123'  # Contraseña por defecto
    }
    
    try:
        # Hacer POST al login
        response = session.post(login_url, data=login_data, allow_redirects=False)
        
        print(f"📊 Status code: {response.status_code}")
        print(f"📊 Headers de respuesta: {dict(response.headers)}")
        
        if response.status_code == 302:  # Redirect después del login exitoso
            print("✅ Login exitoso - Redirección detectada")
            print(f"📍 Redirigido a: {response.headers.get('Location', 'No especificado')}")
            return True
        elif response.status_code == 200:
            # Verificar si hay errores en la página
            soup = BeautifulSoup(response.text, 'html.parser')
            errors = soup.find_all(class_='alert-danger')
            if errors:
                print("❌ Login falló - Errores encontrados:")
                for error in errors:
                    print(f"   - {error.get_text().strip()}")
            else:
                print("⚠️  Login no redirigió pero no hay errores visibles")
        else:
            print(f"❌ Status code inesperado: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error durante el login: {e}")
        return False
    
    return False

if __name__ == '__main__':
    print("🚀 Test de Login con CSRF")
    print("=" * 40)
    
    success = test_login()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Test completado exitosamente")
    else:
        print("❌ Test falló") 