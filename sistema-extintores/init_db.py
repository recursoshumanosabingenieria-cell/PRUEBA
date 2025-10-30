from app import app, db
from models import Usuario, Categoria, Producto, Movimiento
from werkzeug.security import generate_password_hash

def init_database():
    """Inicializa la base de datos creando todas las tablas"""
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        print("✓ Tablas creadas exitosamente")
        
        # Verificar si ya existe un usuario admin
        admin = Usuario.query.filter_by(username='admin').first()
        
        if not admin:
            # Crear usuario administrador por defecto
            admin = Usuario(
                username='admin',
                nombre_completo='Administrador',
                email='admin@abingenieria.com',
                rol='admin',
                activo=True
            )
            admin.set_password('admin123')  # Cambiar esta contraseña después
            db.session.add(admin)
            db.session.commit()
            print("✓ Usuario administrador creado")
            print("  Username: admin")
            print("  Password: admin123")
            print("  ⚠️ IMPORTANTE: Cambia esta contraseña después del primer login")
        else:
            print("✓ Usuario administrador ya existe")

if __name__ == '__main__':
    init_database()
