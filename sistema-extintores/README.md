# 📦 Sistema de Inventario - AB Ingeniería

Sistema web de gestión de inventario desarrollado con Flask para AB Ingeniería S.A.C.

## 🚀 Características

- ✅ Gestión de productos con códigos automáticos
- ✅ Control de stock (entradas, salidas, ajustes)
- ✅ Categorización de productos
- ✅ Sistema de usuarios con roles (admin/usuario)
- ✅ Reportes y exportación a Excel
- ✅ Alertas de stock bajo
- ✅ Historial de movimientos
- ✅ Interfaz responsive (PC y móvil)

## 📋 Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## 🔧 Instalación y Uso

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Ejecutar la aplicación

**Opción A: Usando el script de inicio (Windows)**
```bash
iniciar.bat
```

**Opción B: Manualmente**
```bash
python app.py
```

La aplicación estará disponible en: http://localhost:5000

## 👤 Acceso Inicial

**Usuario por defecto:**
- Usuario: `admin`
- Contraseña: `admin123`

⚠️ **Importante:** Cambia la contraseña después del primer acceso.

## 📁 Estructura del Proyecto

```
inventario/
├── app.py                 # Aplicación principal
├── models.py              # Modelos de base de datos
├── config.py              # Configuración
├── requirements.txt       # Dependencias
├── iniciar.bat           # Script de inicio (Windows)
├── templates/            # Plantillas HTML
├── static/              # Archivos estáticos
└── instance/            # Base de datos SQLite
    └── inventario.db
```

## 💾 Respaldo de Datos

**Ubicación de la base de datos:** `instance/inventario.db`

**Para hacer respaldo manual:**
1. Copia el archivo `instance/inventario.db`
2. Guárdalo en un lugar seguro (OneDrive, USB, etc.)
3. Para restaurar, reemplaza el archivo

## 🛠️ Tecnologías Utilizadas

- **Backend**: Flask 3.0
- **Base de datos**: SQLite
- **ORM**: SQLAlchemy
- **Autenticación**: Flask-Login
- **Frontend**: Bootstrap 5
- **Exportación**: openpyxl

## 🐛 Solución de Problemas

### Error: "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### Error: "Database is locked"
- Cierra otras instancias de la aplicación
- Reinicia el servidor

---

**Desarrollado por AB Ingeniería S.A.C. - 2024**
