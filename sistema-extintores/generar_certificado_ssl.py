"""
Script para generar certificado SSL autofirmado para desarrollo
Esto permite usar HTTPS en la red local para acceder a la camara desde moviles
"""
from OpenSSL import crypto
import os

def generar_certificado():
    # Crear directorio para certificados
    cert_dir = 'ssl_certs'
    os.makedirs(cert_dir, exist_ok=True)
    
    # Generar clave privada
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    
    # Generar certificado
    cert = crypto.X509()
    cert.get_subject().C = "PE"
    cert.get_subject().ST = "Lima"
    cert.get_subject().L = "Lima"
    cert.get_subject().O = "AB Ingenieria"
    cert.get_subject().OU = "IT"
    cert.get_subject().CN = "localhost"
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Valido por 1 año
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    
    # Guardar certificado y clave
    cert_path = os.path.join(cert_dir, 'cert.pem')
    key_path = os.path.join(cert_dir, 'key.pem')
    
    with open(cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    
    print("=" * 60)
    print("Certificado SSL generado exitosamente")
    print("=" * 60)
    print(f"Certificado: {cert_path}")
    print(f"Clave privada: {key_path}")
    print()
    print("IMPORTANTE:")
    print("1. Este es un certificado autofirmado para desarrollo")
    print("2. Los navegadores mostraran una advertencia de seguridad")
    print("3. Debes aceptar el riesgo para continuar")
    print("4. Para usar HTTPS, ejecuta: python app_https.py")
    print("=" * 60)

if __name__ == '__main__':
    try:
        generar_certificado()
    except ImportError:
        print("=" * 60)
        print("ERROR: Falta el modulo pyOpenSSL")
        print("=" * 60)
        print("Instala con: pip install pyOpenSSL")
        print("=" * 60)
