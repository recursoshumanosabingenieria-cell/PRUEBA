"""
Ejecutar Flask con HTTPS para permitir acceso a camara desde dispositivos moviles
"""
import os
import webbrowser
import threading
import time
import socket
import logging
from app import app, socketio

def obtener_ip_local():
    """Obtiene la IP local de la maquina"""
    try:
        # Crear un socket temporal para obtener la IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def abrir_navegador():
    """Abre el navegador despues de que el servidor inicie"""
    time.sleep(2)  # Esperar a que el servidor inicie
    webbrowser.open('https://localhost:5000')

if __name__ == '__main__':
    cert_dir = 'ssl_certs'
    cert_path = os.path.join(cert_dir, 'cert.pem')
    key_path = os.path.join(cert_dir, 'key.pem')
    
    # Verificar que existan los certificados
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("=" * 60)
        print("ERROR: No se encontraron los certificados SSL")
        print("=" * 60)
        print("Ejecuta primero: python generar_certificado_ssl.py")
        print("=" * 60)
        exit(1)
    
    ip_local = obtener_ip_local()
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("=" * 60)
    print("  SISTEMA DE GESTION DE EXTINTORES v2.0 - HTTPS")
    print("  Sincronizacion en Tiempo Real: ACTIVADA")
    print("=" * 60)
    print(f"PC (localhost): https://localhost:5000")
    print(f"Movil (red local): https://{ip_local}:5000")
    print()
    print("IMPORTANTE:")
    print("- El navegador mostrara una advertencia de seguridad")
    print("- Haz clic en 'Avanzado' y luego 'Continuar a localhost'")
    print("- Esto es normal con certificados autofirmados")
    print("=" * 60)
    
    # Abrir navegador en segundo plano
    threading.Thread(target=abrir_navegador, daemon=True).start()
    
    # Ejecutar con SSL usando SocketIO (CRÍTICO para sincronización en tiempo real)
    socketio.run(
        app,
        host='0.0.0.0',  # Permite acceso desde la red local
        port=5000,
        ssl_context=(cert_path, key_path),
        debug=True,
        allow_unsafe_werkzeug=True
    )
