# Sistema de Gestión de Extintores

Sistema web para la gestión integral de extintores, mantenimientos y órdenes de trabajo con sincronización en tiempo real.

## Características

- **Gestión de Órdenes**: 5 etapas (Creación → Asignación → Recojo → Registro → Revisión)
- **Sincronización en Tiempo Real**: Cambios instantáneos entre dispositivos
- **Evidencia Fotográfica**: Captura y gestión de fotos
- **Catálogo de Extintores**: Tipos con colores distintivos, capacidades y marcas
- **Tabla Editable**: Auto-guardado inteligente para registro de extintores
- **Generación de PDFs**: Documentos profesionales
- **Soporte HTTPS**: Acceso seguro desde red local

## Instalación

### Requisitos
- Python 3.8+
- pip

### Pasos

1. Clonar el repositorio
2. Instalar dependencias: `pip install -r requirements.txt`
3. Copiar `.env.example` a `.env` y configurar
4. Inicializar catálogo: `python poblar_catalogo.py`
5. (Opcional) Generar certificados SSL: `python generar_certificado_ssl.py`

## Uso

**Modo HTTP:**
```bash
python app.py
```
Acceder a: `http://localhost:5000`

**Modo HTTPS (red local):**
```bash
python app_https.py
```
Acceder a: `https://localhost:5000`

**Windows:**
```bash
iniciar_app.bat
```

## Tecnologías

- Flask + Flask-SocketIO
- SQLite
- Bootstrap 5 + jQuery
- ReportLab (PDFs)

## Licencia

Uso privado - AB INGENIERIA S.A.C.
