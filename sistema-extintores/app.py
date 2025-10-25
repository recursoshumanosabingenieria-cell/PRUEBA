from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import webbrowser
from threading import Timer
import socket
import requests
import logging
import hashlib
from functools import wraps

# Importar configuración
from config import config

# Crear aplicación
app = Flask(__name__)

# Cargar configuración
config_name = os.getenv('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])
config[config_name].init_app(app)

# Desactivar caché de plantillas para desarrollo
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configuración de SocketIO
app.config['SECRET_KEY'] = 'tu_clave_secreta_para_socketio'

# Inicializar extensiones
CORS(app)
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ==================== FUNCIONES DE SINCRONIZACIÓN EN TIEMPO REAL ====================

def emitir_cambio_orden(orden_id, tipo_cambio, datos=None):
    """
    Emite un evento de cambio en una orden a todos los clientes conectados
    
    Args:
        orden_id: ID de la orden que cambió
        tipo_cambio: Tipo de cambio ('orden_actualizada', 'foto_agregada', 'foto_eliminada', etc.)
        datos: Datos adicionales del cambio (opcional)
    """
    try:
        evento = {
            'orden_id': orden_id,
            'tipo': tipo_cambio,
            'timestamp': datetime.now().isoformat(),
            'datos': datos or {}
        }
        socketio.emit('cambio_orden', evento, namespace='/')
        app.logger.info(f"[SYNC] 🔄 Evento emitido: {tipo_cambio} - Orden {orden_id}")
    except Exception as e:
        app.logger.error(f"[SYNC] Error al emitir evento: {str(e)}")

def emitir_cambio_global(entidad, tipo_cambio, datos=None, mensaje=None):
    """
    Emite un evento GLOBAL de cambio de datos a todos los clientes conectados
    
    Args:
        entidad: Tipo de entidad ('cliente', 'extintor', 'orden', 'usuario', 'catalogo')
        tipo_cambio: Tipo de cambio ('creado', 'actualizado', 'eliminado')
        datos: Datos adicionales del cambio (opcional)
        mensaje: Mensaje descriptivo para mostrar al usuario
    """
    try:
        evento = {
            'entidad': entidad,
            'tipo': tipo_cambio,
            'timestamp': datetime.now().isoformat(),
            'datos': datos or {},
            'mensaje': mensaje or f'{entidad.capitalize()} {tipo_cambio}'
        }
        socketio.emit('data_changed', evento, namespace='/')
        app.logger.info(f"[GLOBAL-SYNC] 🔄 {entidad} {tipo_cambio}")
    except Exception as e:
        app.logger.error(f"[GLOBAL-SYNC] Error: {str(e)}")

# ==================== SISTEMA DE ACTIVIDAD EN TIEMPO REAL ====================

# Diccionario para rastrear usuarios conectados
usuarios_conectados = {}

@socketio.on('connect')
def handle_connect():
    app.logger.info("[SYNC] ✅ Cliente conectado")

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info("[SYNC] ❌ Cliente desconectado")
    # Remover usuario de la lista de conectados
    sid = request.sid
    if sid in usuarios_conectados:
        usuario_info = usuarios_conectados[sid]
        del usuarios_conectados[sid]
        # Notificar a todos que el usuario se desconectó
        socketio.emit('usuario_desconectado', {
            'usuario': usuario_info['nombre'],
            'timestamp': datetime.now().isoformat()
        }, namespace='/')

@socketio.on('usuario_conectado')
def handle_usuario_conectado(data):
    """Registra cuando un usuario se conecta"""
    sid = request.sid
    usuarios_conectados[sid] = {
        'nombre': data.get('nombre', 'Usuario'),
        'rol': data.get('rol', 'Usuario'),
        'timestamp': datetime.now().isoformat()
    }
    
    # Notificar a todos los usuarios conectados
    socketio.emit('usuario_conectado', {
        'usuario': data.get('nombre'),
        'rol': data.get('rol'),
        'usuarios_online': len(usuarios_conectados),
        'timestamp': datetime.now().isoformat()
    }, namespace='/')
    
    app.logger.info(f"[ACTIVIDAD] 👤 {data.get('nombre')} se conectó")

@socketio.on('actividad_usuario')
def handle_actividad_usuario(data):
    """Registra y transmite actividades de usuarios en tiempo real"""
    actividad = {
        'usuario': data.get('usuario', 'Usuario'),
        'accion': data.get('accion', 'realizó una acción'),
        'pagina': data.get('pagina', ''),
        'detalles': data.get('detalles', ''),
        'timestamp': datetime.now().isoformat()
    }
    
    # Emitir a todos los usuarios conectados
    socketio.emit('nueva_actividad', actividad, namespace='/')
    app.logger.info(f"[ACTIVIDAD] 🔔 {actividad['usuario']}: {actividad['accion']}")

@socketio.on('celda_editada')
def handle_celda_editada(data):
    """Sincronización en tiempo real de edición de celdas (tipo Google Sheets)"""
    # Emitir a todos los clientes EXCEPTO al que envió el cambio
    socketio.emit('actualizar_celda', {
        'orden_id': data.get('orden_id'),
        'extintor_id': data.get('extintor_id'),
        'campo': data.get('campo'),
        'valor': data.get('valor'),
        'usuario': data.get('usuario'),
        'timestamp': datetime.now().isoformat()
    }, namespace='/', skip_sid=request.sid)
    
    app.logger.info(f"[CELDA-SYNC] 📝 {data.get('usuario')}: {data.get('campo')} = {data.get('valor')}")

@socketio.on('campo_editado')
def handle_campo_editado(data):
    """Maneja la edición de cualquier campo de formulario en tiempo real"""
    try:
        app.logger.info(f"[CAMPO-SYNC] 📝 {data.get('usuario', 'Usuario')}: {data.get('campo_id')} = {data.get('valor')}")
        
        # Emitir a todos los clientes EXCEPTO al que envió el cambio
        socketio.emit('actualizar_campo', data, skip_sid=request.sid)
        
    except Exception as e:
        app.logger.error(f"[CAMPO-SYNC] Error: {str(e)}")

@socketio.on('cambio_fecha_recarga')
def handle_cambio_fecha_recarga(data):
    """Maneja el cambio de fecha de recarga en tiempo real"""
    try:
        orden_id = data.get('orden_id')
        fecha = data.get('fecha')
        app.logger.info(f"[FECHA-RECARGA] 📅 Orden {orden_id}: Fecha cambiada a {fecha}")
        
        # Emitir a TODOS los clientes EXCEPTO al que envió el cambio
        socketio.emit('fecha_recarga_cambiada', {
            'orden_id': orden_id,
            'fecha': fecha
        }, skip_sid=request.sid)
        
        app.logger.info(f"[FECHA-RECARGA] ✅ Evento emitido a otros clientes")
        
    except Exception as e:
        app.logger.error(f"[FECHA-RECARGA] Error: {str(e)}")
    
    app.logger.info(f"[CAMPO-SYNC] 📝 {data.get('usuario')}: {data.get('campo_id')} = {data.get('valor')}")

# ==================== FIN SISTEMA DE ACTIVIDAD ====================

@socketio.on('unirse_orden')
def handle_unirse_orden(data):
    """Cliente se une a una sala específica de una orden"""
    orden_id = data.get('orden_id')
    if orden_id:
        app.logger.info(f"[SYNC] 📱 Cliente se unió a orden {orden_id}")

# ==================== FIN FUNCIONES DE SINCRONIZACIÓN ====================

# Funciones de autenticación
def hash_password(password):
    """Hashear contraseña con SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorador para requerir login - DESACTIVADO TEMPORALMENTE"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Crear sesión temporal si no existe
        if 'user_id' not in session:
            session['user_id'] = 1
            session['user_username'] = 'admin'
            session['user_nombre'] = 'Usuario Temporal'
            session['user_rol'] = 'PRINCIPAL'
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorador para requerir roles específicos - DESACTIVADO TEMPORALMENTE"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Crear sesión temporal si no existe
            if 'user_id' not in session:
                session['user_id'] = 1
                session['user_username'] = 'admin'
                session['user_nombre'] = 'Usuario Temporal'
                session['user_rol'] = 'PRINCIPAL'
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Modelos de Base de Datos
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    rfc = db.Column(db.String(13), unique=True)
    direccion = db.Column(db.String(300))
    ubigeo = db.Column(db.String(10))
    distrito = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    estado = db.Column(db.String(50))  # ACTIVO/INACTIVO
    condicion = db.Column(db.String(50))  # HABIDO/NO HABIDO
    es_agente_retencion = db.Column(db.Boolean, default=False)
    es_buen_contribuyente = db.Column(db.Boolean, default=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    extintores = db.relationship('Extintor', backref='cliente', lazy=True)
    locales_anexos = db.relationship('LocalAnexo', backref='cliente', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Cliente {self.nombre}>'

class LocalAnexo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    direccion = db.Column(db.String(300))
    ubigeo = db.Column(db.String(10))
    distrito = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LocalAnexo {self.direccion[:30]}...>'

# Catálogo de Tipos de Extintores
class TipoExtintor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # PQS, CO2, Agua, Espuma, etc. (acrónimo o nombre corto)
    nombre_completo = db.Column(db.String(100))  # Polvo Químico Seco, Dióxido de Carbono, etc.
    clase_fuego = db.Column(db.String(20))  # ABC, BC, A, K, etc.
    descripcion = db.Column(db.String(200))
    color = db.Column(db.String(7), default='#6c757d')  # Color en formato hexadecimal (ej: #FF5733)
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<TipoExtintor {self.nombre}>'

# Catálogo de Capacidades
class CapacidadExtintor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    capacidad = db.Column(db.String(20), unique=True, nullable=False)  # 4kg, 6kg, 9kg, 12kg, etc.
    unidad = db.Column(db.String(10), default='kg')  # kg, lb, L
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<CapacidadExtintor {self.capacidad}>'

# Catálogo de Marcas
class MarcaExtintor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    origen = db.Column(db.String(50), nullable=False)  # Nacional, Chino, Americano, Europeo, etc.
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<MarcaExtintor {self.nombre}>'

class Extintor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    orden_trabajo_id = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=True)
    
    # Columnas de la tabla visual (EXACTAMENTE como aparecen en la interfaz)
    serie = db.Column(db.String(100))              # Columna: SERIE
    tipo = db.Column(db.String(100))               # Columna: TIPO
    capacidad = db.Column(db.String(50))           # Columna: CAP.
    marca = db.Column(db.String(100))              # Columna: MARCA
    fecha_recarga = db.Column(db.String(50))       # Columna: FECHA REC. (formato: Mes-Año)
    vencimiento_recarga = db.Column(db.String(50)) # Columna: VENC. REC. (formato: Mes-Año)
    observaciones = db.Column(db.Text)             # Columna: OBS.
    
    # Campos adicionales
    estado = db.Column(db.String(50), default='Pendiente')
    fecha_creacion = db.Column(db.DateTime, default=datetime.now)
    
    mantenimientos = db.relationship('Mantenimiento', backref='extintor', lazy=True)
    
    def __repr__(self):
        return f'<Extintor {self.serie or self.id}>'

class OrdenTrabajo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_orden = db.Column(db.String(50), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    fecha_recojo = db.Column(db.Date, nullable=False)
    cantidad_extintores = db.Column(db.Integer, nullable=False)
    direccion_recojo = db.Column(db.String(300))
    contacto_recojo = db.Column(db.String(100))
    telefono_contacto = db.Column(db.String(20))
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(50), default='Pendiente')  # Pendiente, En Proceso, Completada
    recogido = db.Column(db.Boolean, default=False)  # Si los extintores ya fueron recogidos
    fecha_recogido_real = db.Column(db.Date)  # Fecha real de recojo
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Sistema de etapas
    etapa_actual = db.Column(db.String(50), default='CREADA')  # CREADA, ASIGNADA, RECOGIDO, COMPLETADO, REVISION, FINALIZADO
    trabajador_asignado = db.Column(db.String(500))  # Aumentado para múltiples trabajadores
    fecha_completado_trabajador = db.Column(db.DateTime)
    fecha_revision_oficina = db.Column(db.DateTime)
    
    # Fecha de recarga seleccionada (formato ISO: YYYY-MM-DD)
    fecha_recarga_seleccionada = db.Column(db.String(20))  # Guarda la última fecha seleccionada en el combobox
    
    # Indicador de si ya se envió a oficina (permanente)
    enviado_a_oficina = db.Column(db.Boolean, default=False)  # True = ya se envió, False = aún no se envía
    fecha_envio_oficina = db.Column(db.DateTime)  # Fecha del primer envío a oficina
    
    # Indicador permanente de si alguna vez se marcó como recogido
    marcado_recogido_alguna_vez = db.Column(db.Boolean, default=False)
    
    # Indicador permanente de si alguna vez se confirmó la asignación
    confirmada_asignacion_alguna_vez = db.Column(db.Boolean, default=False)
    
    # Indicador de si la revisión fue finalizada (se desmarca si hay cambios en etapas anteriores)
    revision_finalizada = db.Column(db.Boolean, default=False)
    
    # Indicador de si tiene evidencia fotográfica (basado en si hay fotos, no en el checkbox)
    tiene_evidencia_fotografica = db.Column(db.Boolean, default=False)
    
    # Indicador de si tiene foto de guía de recojo (basado en si hay fotos de guía)
    tiene_foto_guia = db.Column(db.Boolean, default=False)
    
    extintores = db.relationship('Extintor', backref='orden_trabajo', lazy=True)
    extintores_detalle = db.relationship('OrdenExtintorDetalle', backref='orden', lazy=True, cascade='all, delete-orphan')
    cliente = db.relationship('Cliente', backref='ordenes_trabajo')
    
    def __repr__(self):
        return f'<OrdenTrabajo {self.numero_orden}>'

# Tabla para almacenar el detalle de tipos de extintores en una orden
class OrdenExtintorDetalle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey('tipo_extintor.id'), nullable=False)
    capacidad_id = db.Column(db.Integer, db.ForeignKey('capacidad_extintor.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    tipo = db.relationship('TipoExtintor')
    capacidad = db.relationship('CapacidadExtintor')
    
    def __repr__(self):
        return f'<OrdenExtintorDetalle Orden:{self.orden_id} x{self.cantidad}>'

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    dni = db.Column(db.String(20))
    direccion = db.Column(db.String(300))
    rol = db.Column(db.String(20), nullable=False)  # PRINCIPAL, ADMINISTRATIVO, TECNICO
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class FotoRecojo(db.Model):
    """Tabla para almacenar fotos de evidencia del recojo de extintores"""
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)  # Nombre del archivo en disco
    ruta_archivo = db.Column(db.String(500), nullable=False)    # Ruta relativa desde static/
    fecha_captura = db.Column(db.DateTime, default=datetime.utcnow)
    tamanio_bytes = db.Column(db.Integer)  # Tamaño del archivo en bytes
    
    orden = db.relationship('OrdenTrabajo', backref='fotos_recojo')
    
    def __repr__(self):
        return f'<FotoRecojo Orden:{self.orden_id} - {self.nombre_archivo}>'

class FotoGuiaRecojo(db.Model):
    """Tabla para almacenar fotos de guías de recojo (comprobantes del cliente)"""
    __tablename__ = 'foto_guia_recojo'
    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)  # Nombre del archivo en disco
    ruta_archivo = db.Column(db.String(500), nullable=False)    # Ruta relativa desde static/
    fecha_captura = db.Column(db.DateTime, default=datetime.utcnow)
    tamanio_bytes = db.Column(db.Integer)  # Tamaño del archivo en bytes
    
    orden = db.relationship('OrdenTrabajo', backref='fotos_guia_recojo')
    
    def __repr__(self):
        return f'<FotoGuiaRecojo Orden:{self.orden_id} - {self.nombre_archivo}>'

class Mantenimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    extintor_id = db.Column(db.Integer, db.ForeignKey('extintor.id'), nullable=False)
    fecha_servicio = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_servicio = db.Column(db.String(50), nullable=False)  # Recarga, Inspección, Mantenimiento Preventivo
    tecnico = db.Column(db.String(100))
    observaciones = db.Column(db.Text)
    costo = db.Column(db.Float, default=0.0)
    proximo_servicio = db.Column(db.Date)
    completado = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Mantenimiento {self.tipo_servicio} - Extintor:{self.extintor_id}>'

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        # MODO DESARROLLO: Aceptar cualquier contraseña si el usuario existe
        if usuario and usuario.activo:
            session['user_id'] = usuario.id
            session['user_username'] = usuario.username
            session['user_nombre'] = usuario.nombre_completo
            session['user_rol'] = usuario.rol
            
            # Actualizar último acceso
            usuario.ultimo_acceso = datetime.now()
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'rol': usuario.rol})
            return redirect(url_for('index'))
        
        if request.is_json:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 401
        return render_template('login.html', error='Usuario no encontrado')
    
    # Si ya está logueado, redirigir al index
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Rutas principales
@app.route('/')
@login_required
def index():
    return render_template('index.html', usuario=session)

@app.route('/clientes')
@login_required
def clientes_page():
    return render_template('clientes.html', usuario=session)

@app.route('/catalogo')
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def catalogo_page():
    return render_template('catalogo.html', usuario=session)

@app.route('/extintores')
@login_required
def extintores_page():
    return render_template('extintores.html', usuario=session)

@app.route('/mantenimientos')
@login_required
def mantenimientos_page():
    return render_template('mantenimientos.html', usuario=session)

@app.route('/reportes')
@login_required
def reportes_page():
    return render_template('reportes.html', usuario=session)

@app.route('/ordenes')
@login_required
def ordenes_page():
    return render_template('ordenes.html', usuario=session)

@app.route('/ordenes/<int:orden_id>')
@login_required
def orden_detalle_page(orden_id):
    return render_template('orden_detalle.html', orden_id=orden_id, usuario=session)

@app.route('/personal')
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def personal_page():
    return render_template('personal.html', usuario=session)

@app.route('/logs')
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def logs_page():
    return render_template('logs.html', usuario=session)

# API de Usuarios
@app.route('/api/usuarios', methods=['GET', 'POST'])
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def api_usuarios():
    if request.method == 'GET':
        usuarios = Usuario.query.all()
        return jsonify([{
            'id': u.id,
            'username': u.username,
            'nombre_completo': u.nombre_completo,
            'email': u.email,
            'telefono': u.telefono,
            'dni': u.dni,
            'direccion': u.direccion,
            'rol': u.rol,
            'activo': u.activo,
            'fecha_creacion': u.fecha_creacion.strftime('%Y-%m-%d %H:%M') if u.fecha_creacion else None,
            'ultimo_acceso': u.ultimo_acceso.strftime('%Y-%m-%d %H:%M') if u.ultimo_acceso else None
        } for u in usuarios])
    
    elif request.method == 'POST':
        data = request.json
        nuevo_usuario = Usuario(
            username=data['username'],
            password=hash_password(data['password']),
            nombre_completo=data['nombre_completo'],
            email=data.get('email'),
            telefono=data.get('telefono'),
            dni=data.get('dni'),
            direccion=data.get('direccion'),
            rol=data['rol'],
            activo=data.get('activo', True)
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('usuario', 'creado', {'id': nuevo_usuario.id, 'nombre': nuevo_usuario.nombre_completo}, f'Usuario {nuevo_usuario.nombre_completo} creado')
        
        return jsonify({'success': True, 'id': nuevo_usuario.id})

@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT', 'DELETE'])
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def api_usuario_detalle(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if request.method == 'PUT':
        data = request.json
        usuario.nombre_completo = data.get('nombre_completo', usuario.nombre_completo)
        usuario.email = data.get('email', usuario.email)
        usuario.telefono = data.get('telefono', usuario.telefono)
        usuario.dni = data.get('dni', usuario.dni)
        usuario.direccion = data.get('direccion', usuario.direccion)
        usuario.rol = data.get('rol', usuario.rol)
        usuario.activo = data.get('activo', usuario.activo)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('usuario', 'actualizado', {'id': usuario.id, 'nombre': usuario.nombre_completo}, f'Usuario {usuario.nombre_completo} actualizado')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        # No permitir eliminar el propio usuario
        if usuario.id == session.get('user_id'):
            return jsonify({'success': False, 'error': 'No puedes eliminar tu propio usuario'}), 400
        nombre = usuario.nombre_completo
        db.session.delete(usuario)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('usuario', 'eliminado', {'id': usuario_id, 'nombre': nombre}, f'Usuario {nombre} eliminado')
        
        return jsonify({'success': True})

@app.route('/api/usuarios/<int:usuario_id>/cambiar-password', methods=['POST'])
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def api_cambiar_password(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.json
    nueva_password = data.get('password')
    
    if not nueva_password:
        return jsonify({'success': False, 'error': 'Contraseña requerida'}), 400
    
    usuario.password = hash_password(nueva_password)
    db.session.commit()
    
    # Emitir evento de sincronización
    emitir_cambio_global('usuario', 'actualizado', {'id': usuario.id, 'nombre': usuario.nombre_completo}, f'Contraseña cambiada para {usuario.nombre_completo}')
    
    return jsonify({'success': True})

# API - Clientes
@app.route('/api/clientes', methods=['GET', 'POST'])
def api_clientes():
    if request.method == 'GET':
        clientes = Cliente.query.all()
        return jsonify([{
            'id': c.id,
            'nombre': c.nombre,
            'rfc': c.rfc,
            'direccion': c.direccion,
            'distrito': c.distrito,
            'provincia': c.provincia,
            'departamento': c.departamento,
            'estado': c.estado,
            'condicion': c.condicion,
            'fecha_registro': c.fecha_registro.strftime('%Y-%m-%d'),
            'total_extintores': len(c.extintores),
            'total_locales_anexos': len(c.locales_anexos)
        } for c in clientes])
    
    elif request.method == 'POST':
        data = request.json
        
        try:
            # Verificar si el RUC ya existe
            rfc = data.get('rfc', '')
            if rfc:
                cliente_existente = Cliente.query.filter_by(rfc=rfc).first()
                if cliente_existente:
                    return jsonify({
                        'success': False, 
                        'message': f'Ya existe un cliente con el RUC {rfc}: {cliente_existente.nombre}'
                    }), 400
            
            # Crear nuevo cliente con todos los datos de SUNAT
            nuevo_cliente = Cliente(
                nombre=data['nombre'],
                rfc=rfc,
                direccion=data.get('direccion', ''),
                ubigeo=data.get('ubigeo', ''),
                distrito=data.get('distrito', ''),
                provincia=data.get('provincia', ''),
                departamento=data.get('departamento', ''),
                estado=data.get('estado', ''),
                condicion=data.get('condicion', ''),
                es_agente_retencion=data.get('es_agente_retencion', False),
                es_buen_contribuyente=data.get('es_buen_contribuyente', False)
            )
            db.session.add(nuevo_cliente)
            db.session.flush()  # Para obtener el ID del cliente
            
            # Guardar locales anexos si existen
            if data.get('locales_anexos'):
                for local_data in data['locales_anexos']:
                    local_anexo = LocalAnexo(
                        cliente_id=nuevo_cliente.id,
                        direccion=local_data.get('direccion', ''),
                        ubigeo=local_data.get('ubigeo', ''),
                        distrito=local_data.get('distrito', ''),
                        provincia=local_data.get('provincia', ''),
                        departamento=local_data.get('departamento', '')
                    )
                    db.session.add(local_anexo)
            
            db.session.commit()
            app.logger.info(f"\n[CLIENTE] Guardado: {nuevo_cliente.nombre}")
            app.logger.info(f"[CLIENTE] RUC: {nuevo_cliente.rfc}")
            app.logger.info(f"[CLIENTE] Locales anexos: {len(data.get('locales_anexos', []))}")
            app.logger.info(f"[CLIENTE] Estado: {nuevo_cliente.estado}\n")
            
            # Emitir evento global de sincronización
            emitir_cambio_global('cliente', 'creado', {'id': nuevo_cliente.id, 'nombre': nuevo_cliente.nombre}, f'Cliente {nuevo_cliente.nombre} creado')
            
            return jsonify({'success': True, 'id': nuevo_cliente.id}), 201
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"\n[ERROR] No se pudo guardar el cliente: {str(e)}\n")
            return jsonify({
                'success': False, 
                'message': 'Error al guardar el cliente. Por favor, intente nuevamente.'
            }), 500

@app.route('/api/clientes/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    if request.method == 'GET':
        # Obtener locales anexos
        locales = [{
            'id': local.id,
            'direccion': local.direccion,
            'ubigeo': local.ubigeo,
            'distrito': local.distrito,
            'provincia': local.provincia,
            'departamento': local.departamento
        } for local in cliente.locales_anexos]
        
        return jsonify({
            'id': cliente.id,
            'nombre': cliente.nombre,
            'rfc': cliente.rfc,
            'direccion': cliente.direccion,
            'ubigeo': cliente.ubigeo,
            'distrito': cliente.distrito,
            'provincia': cliente.provincia,
            'departamento': cliente.departamento,
            'estado': cliente.estado,
            'condicion': cliente.condicion,
            'es_agente_retencion': cliente.es_agente_retencion,
            'es_buen_contribuyente': cliente.es_buen_contribuyente,
            'locales_anexos': locales
        })
    
    elif request.method == 'PUT':
        data = request.json
        cliente.nombre = data.get('nombre', cliente.nombre)
        cliente.rfc = data.get('rfc', cliente.rfc)
        cliente.direccion = data.get('direccion', cliente.direccion)
        cliente.ubigeo = data.get('ubigeo', cliente.ubigeo)
        cliente.distrito = data.get('distrito', cliente.distrito)
        cliente.provincia = data.get('provincia', cliente.provincia)
        cliente.departamento = data.get('departamento', cliente.departamento)
        cliente.estado = data.get('estado', cliente.estado)
        cliente.condicion = data.get('condicion', cliente.condicion)
        db.session.commit()
        
        # Emitir evento global
        emitir_cambio_global('cliente', 'actualizado', {'id': cliente.id, 'nombre': cliente.nombre}, f'Cliente {cliente.nombre} actualizado')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        # Eliminación permanente - borrar completamente de la base de datos
        app.logger.info(f"\n[CLIENTE] Eliminando permanentemente: {cliente.nombre} (RUC: {cliente.rfc})")
        
        nombre = cliente.nombre
        db.session.delete(cliente)
        db.session.commit()
        
        app.logger.info(f"[CLIENTE] Cliente eliminado exitosamente\n")
        
        # Emitir evento global
        emitir_cambio_global('cliente', 'eliminado', {'id': id, 'nombre': nombre}, f'Cliente {nombre} eliminado')
        
        return jsonify({'success': True})

@app.route('/api/consultar-ruc/<ruc>', methods=['GET'])
def consultar_ruc(ruc):
    """Consulta datos de una empresa por RUC usando API Factiliza"""
    app.logger.info(f"\n{'='*60}")
    app.logger.info(f"[CONSULTA RUC] Iniciando consulta para RUC: {ruc}")
    app.logger.info(f"[CONSULTA RUC] Metodo: API Factiliza (Info + Establecimientos)")
    app.logger.info(f"{'='*60}")
    
    try:
        # Token de la API
        token = os.getenv('API_FACTILIZA_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzOTY4NSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.5Mp0qmhvim2CWM4Lh_StpqPHzx7yHjaCxplrpHA9Us4')
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # 1. Consultar información general del RUC
        app.logger.info(f"[CONSULTA RUC] Paso 1: Consultando informacion general...")
        url_info = f"https://api.factiliza.com/v1/ruc/info/{ruc}"
        response_info = requests.get(url_info, headers=headers, timeout=15)
        
        app.logger.info(f"[CONSULTA RUC] Info - Status Code: {response_info.status_code}")
        
        if response_info.status_code != 200:
            if response_info.status_code == 401:
                app.logger.error(f"[CONSULTA RUC] ERROR 401: Token invalido o expirado")
                return jsonify({
                    'success': False,
                    'message': 'Error de autenticación con la API. Contacte al administrador.'
                }), 401
            else:
                app.logger.error(f"[CONSULTA RUC] ERROR HTTP: {response_info.status_code}")
                return jsonify({
                    'success': False,
                    'message': f'Error al consultar RUC (codigo {response_info.status_code})'
                }), response_info.status_code
        
        response_data = response_info.json()
        
        if not response_data.get('success') or not response_data.get('data'):
            app.logger.warning(f"[CONSULTA RUC] ERROR: RUC no encontrado o sin datos")
            return jsonify({
                'success': False,
                'message': 'RUC no encontrado'
            }), 404
        
        data = response_data['data']
        app.logger.info(f"[CONSULTA RUC] Razon Social: {data.get('nombre_o_razon_social', 'N/A')}")
        app.logger.info(f"[CONSULTA RUC] Estado: {data.get('estado', 'N/A')}")
        
        # Procesar ubigeo (viene como array)
        ubigeo = data.get('ubigeo', [])
        ubigeo_str = ubigeo[2] if isinstance(ubigeo, list) and len(ubigeo) > 2 else data.get('ubigeo_sunat', '')
        
        # 2. Consultar establecimientos anexos
        app.logger.info(f"[CONSULTA RUC] Paso 2: Consultando establecimientos anexos...")
        url_anexos = f"https://api.factiliza.com/v1/ruc/anexo/{ruc}"
        
        locales_anexos = []
        try:
            response_anexos = requests.get(url_anexos, headers=headers, timeout=30)
            app.logger.info(f"[CONSULTA RUC] Anexos - Status Code: {response_anexos.status_code}")
            
            if response_anexos.status_code == 200:
                anexos_data = response_anexos.json()
                
                if anexos_data.get('status') == 200 and anexos_data.get('data'):
                    establecimientos = anexos_data['data']
                    app.logger.info(f"[CONSULTA RUC] Establecimientos encontrados: {len(establecimientos)}")
                    
                    for establecimiento in establecimientos:
                        # Procesar ubigeo del establecimiento
                        ubigeo_est = establecimiento.get('ubigeo', [])
                        ubigeo_est_str = ubigeo_est[2] if isinstance(ubigeo_est, list) and len(ubigeo_est) > 2 else establecimiento.get('ubigeo_sunat', '')
                        
                        local = {
                            'codigo': establecimiento.get('codigo', ''),
                            'tipo_establecimiento': establecimiento.get('tipo_establecimiento', ''),
                            'direccion': establecimiento.get('direccion_completa', establecimiento.get('direccion', '')),
                            'ubigeo': ubigeo_est_str,
                            'departamento': establecimiento.get('departamento', ''),
                            'provincia': establecimiento.get('provincia', ''),
                            'distrito': establecimiento.get('distrito', ''),
                            'actividad_economica': establecimiento.get('actividad_economica', '')
                        }
                        locales_anexos.append(local)
                        app.logger.info(f"[CONSULTA RUC]   - {local['tipo_establecimiento']}: {local['direccion'][:50]}...")
                else:
                    app.logger.info(f"[CONSULTA RUC] No se encontraron establecimientos anexos")
            else:
                app.logger.warning(f"[CONSULTA RUC] No se pudieron obtener anexos (Status: {response_anexos.status_code})")
        
        except Exception as e:
            app.logger.warning(f"[CONSULTA RUC] Error al consultar anexos: {str(e)}")
            app.logger.info(f"[CONSULTA RUC] Continuando sin establecimientos anexos...")
        
        # Construir resultado final
        resultado = {
            'success': True,
            'data': {
                'nombre': data.get('nombre_o_razon_social', ''),
                'rfc': data.get('numero', ruc),
                'direccion': data.get('direccion_completa', data.get('direccion', '')),
                'ubigeo': ubigeo_str,
                'estado': data.get('estado', ''),
                'condicion': data.get('condicion', ''),
                'departamento': data.get('departamento', ''),
                'provincia': data.get('provincia', ''),
                'distrito': data.get('distrito', ''),
                'es_agente_retencion': bool(data.get('es_agente_de_retencion')),
                'es_buen_contribuyente': bool(data.get('es_buen_contribuyente')),
                'locales_anexos': locales_anexos
            }
        }
        
        app.logger.info(f"[CONSULTA RUC] EXITO - Empresa: {resultado['data']['nombre']}")
        app.logger.info(f"[CONSULTA RUC] Total establecimientos: {len(locales_anexos)}")
        app.logger.info(f"{'='*60}\n")
        return jsonify(resultado)
            
    except requests.Timeout:
        app.logger.error(f"[CONSULTA RUC] TIMEOUT - La peticion tardo mas de 15 segundos")
        return jsonify({
            'success': False,
            'message': 'Tiempo de espera agotado. Intente nuevamente.'
        }), 408
        
    except Exception as e:
        app.logger.error(f"[CONSULTA RUC] ERROR inesperado: {str(e)}")
        app.logger.error(f"[CONSULTA RUC] Tipo de error: {type(e).__name__}")
        import traceback
        app.logger.error(f"[CONSULTA RUC] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error al consultar RUC: {str(e)}'
        }), 500

@app.route('/api/consultar-rucs-masivo', methods=['POST'])
def consultar_rucs_masivo():
    """Consulta múltiples RUCs en lote y los guarda automáticamente"""
    data = request.json
    rucs = data.get('rucs', [])
    
    if not rucs or not isinstance(rucs, list):
        return jsonify({
            'success': False,
            'message': 'Debe proporcionar una lista de RUCs'
        }), 400
    
    app.logger.info(f"\n{'='*60}")
    app.logger.info(f"[CONSULTA MASIVA] Iniciando consulta de {len(rucs)} RUCs")
    app.logger.info(f"{'='*60}")
    
    resultados = []
    exitosos = 0
    duplicados = 0
    errores = 0
    
    # Token de la API
    token = os.getenv('API_FACTILIZA_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzOTY4NSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.5Mp0qmhvim2CWM4Lh_StpqPHzx7yHjaCxplrpHA9Us4')
    headers = {'Authorization': f'Bearer {token}'}
    
    for idx, ruc in enumerate(rucs, 1):
        try:
            app.logger.info(f"[CONSULTA MASIVA] [{idx}/{len(rucs)}] Procesando RUC: {ruc}")
            
            # Verificar si ya existe
            cliente_existente = Cliente.query.filter_by(rfc=ruc).first()
            if cliente_existente:
                duplicados += 1
                resultados.append({
                    'ruc': ruc,
                    'status': 'duplicado',
                    'message': f'Ya existe: {cliente_existente.nombre}'
                })
                app.logger.info(f"[CONSULTA MASIVA] RUC {ruc} ya existe en BD")
                continue
            
            # 1. Consultar información general
            url_info = f"https://api.factiliza.com/v1/ruc/info/{ruc}"
            response_info = requests.get(url_info, headers=headers, timeout=15)
            
            if response_info.status_code != 200:
                errores += 1
                resultados.append({
                    'ruc': ruc,
                    'status': 'error',
                    'message': 'No encontrado en SUNAT'
                })
                continue
            
            data_info = response_info.json()
            if data_info.get('status') != 200:
                errores += 1
                resultados.append({
                    'ruc': ruc,
                    'status': 'error',
                    'message': 'No encontrado en SUNAT'
                })
                continue
            
            data_empresa = data_info['data']
            
            # 2. Consultar establecimientos anexos
            url_anexos = f"https://api.factiliza.com/v1/ruc/anexo/{ruc}"
            locales_anexos = []
            
            try:
                response_anexos = requests.get(url_anexos, headers=headers, timeout=30)
                if response_anexos.status_code == 200:
                    anexos_data = response_anexos.json()
                    if anexos_data.get('status') == 200 and anexos_data.get('data'):
                        for establecimiento in anexos_data['data']:
                            ubigeo_est = establecimiento.get('ubigeo', [])
                            ubigeo_est_str = ubigeo_est[2] if isinstance(ubigeo_est, list) and len(ubigeo_est) > 2 else establecimiento.get('ubigeo_sunat', '')
                            
                            locales_anexos.append({
                                'direccion': establecimiento.get('direccion_completa', establecimiento.get('direccion', '')),
                                'ubigeo': ubigeo_est_str,
                                'departamento': establecimiento.get('departamento', ''),
                                'provincia': establecimiento.get('provincia', ''),
                                'distrito': establecimiento.get('distrito', '')
                            })
            except Exception as e:
                logger.warning(f"[CONSULTA MASIVA] Error al consultar anexos de {ruc}: {str(e)}")
            
            # 3. Guardar cliente
            ubigeo = data_empresa.get('ubigeo', [])
            ubigeo_str = ubigeo[2] if isinstance(ubigeo, list) and len(ubigeo) > 2 else data_empresa.get('ubigeo_sunat', '')
            
            nuevo_cliente = Cliente(
                nombre=data_empresa.get('nombre_o_razon_social', ''),
                rfc=ruc,
                direccion=data_empresa.get('direccion_completa', data_empresa.get('direccion', '')),
                ubigeo=ubigeo_str,
                distrito=data_empresa.get('distrito', ''),
                provincia=data_empresa.get('provincia', ''),
                departamento=data_empresa.get('departamento', ''),
                estado=data_empresa.get('estado', ''),
                condicion=data_empresa.get('condicion', ''),
                es_agente_retencion=False,
                es_buen_contribuyente=False
            )
            db.session.add(nuevo_cliente)
            db.session.flush()
            
            # 4. Guardar locales anexos
            for local_data in locales_anexos:
                local_anexo = LocalAnexo(
                    cliente_id=nuevo_cliente.id,
                    direccion=local_data.get('direccion', ''),
                    ubigeo=local_data.get('ubigeo', ''),
                    distrito=local_data.get('distrito', ''),
                    provincia=local_data.get('provincia', ''),
                    departamento=local_data.get('departamento', '')
                )
                db.session.add(local_anexo)
            
            db.session.commit()
            exitosos += 1
            
            resultados.append({
                'ruc': ruc,
                'status': 'exitoso',
                'nombre': nuevo_cliente.nombre,
                'locales': len(locales_anexos)
            })
            
            app.logger.info(f"[CONSULTA MASIVA] ✅ {ruc} - {nuevo_cliente.nombre} ({len(locales_anexos)} locales)")
            
        except Exception as e:
            db.session.rollback()
            errores += 1
            resultados.append({
                'ruc': ruc,
                'status': 'error',
                'message': str(e)
            })
            app.logger.error(f"[CONSULTA MASIVA] ❌ Error en {ruc}: {str(e)}")
    
    app.logger.info(f"\n[CONSULTA MASIVA] FINALIZADO")
    app.logger.info(f"[CONSULTA MASIVA] Exitosos: {exitosos}, Duplicados: {duplicados}, Errores: {errores}")
    app.logger.info(f"{'='*60}\n")
    
    return jsonify({
        'success': True,
        'total': len(rucs),
        'exitosos': exitosos,
        'duplicados': duplicados,
        'errores': errores,
        'resultados': resultados
    })

# API - Catálogo: Tipos de Extintores
@app.route('/api/catalogo/tipos', methods=['GET', 'POST'])
def api_tipos_extintor():
    if request.method == 'GET':
        tipos = TipoExtintor.query.filter_by(activo=True).all()
        return jsonify([{
            'id': t.id,
            'nombre': t.nombre,
            'nombre_completo': t.nombre_completo,
            'clase_fuego': t.clase_fuego,
            'descripcion': t.descripcion,
            'color': t.color
        } for t in tipos])
    
    elif request.method == 'POST':
        data = request.json
        nuevo_tipo = TipoExtintor(
            nombre=data['nombre'],
            nombre_completo=data.get('nombre_completo', ''),
            clase_fuego=data.get('clase_fuego', ''),
            descripcion=data.get('descripcion', ''),
            color=data.get('color', '#6c757d')
        )
        db.session.add(nuevo_tipo)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'creado', {'id': nuevo_tipo.id, 'tipo': 'tipo_extintor'}, f'Tipo {nuevo_tipo.nombre} creado')
        
        return jsonify({'success': True, 'id': nuevo_tipo.id}), 201

@app.route('/api/catalogo/tipos/<int:id>', methods=['PUT', 'DELETE'])
def api_tipo_extintor(id):
    tipo = TipoExtintor.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.json
        tipo.nombre = data.get('nombre', tipo.nombre)
        tipo.nombre_completo = data.get('nombre_completo', tipo.nombre_completo)
        tipo.clase_fuego = data.get('clase_fuego', tipo.clase_fuego)
        tipo.descripcion = data.get('descripcion', tipo.descripcion)
        tipo.color = data.get('color', tipo.color)
        db.session.commit()
        
        # Emitir evento global
        emitir_cambio_global('tipo_extintor', 'actualizado', {'id': tipo.id, 'nombre': tipo.nombre}, f'Tipo de extintor {tipo.nombre} actualizado')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        nombre = tipo.nombre
        db.session.delete(tipo)
        db.session.commit()
        
        # Emitir evento global
        emitir_cambio_global('tipo_extintor', 'eliminado', {'id': id, 'nombre': nombre}, f'Tipo de extintor {nombre} eliminado')
        
        return jsonify({'success': True})

# API - Catálogo: Capacidades
@app.route('/api/catalogo/capacidades', methods=['GET', 'POST'])
def api_capacidades_extintor():
    if request.method == 'GET':
        capacidades = CapacidadExtintor.query.filter_by(activo=True).all()
        return jsonify([{
            'id': c.id,
            'capacidad': c.capacidad,
            'unidad': c.unidad
        } for c in capacidades])
    
    elif request.method == 'POST':
        data = request.json
        nueva_capacidad = CapacidadExtintor(
            capacidad=data['capacidad'],
            unidad=data.get('unidad', 'kg')
        )
        db.session.add(nueva_capacidad)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'creado', {'id': nueva_capacidad.id, 'tipo': 'capacidad'}, f'Capacidad {nueva_capacidad.capacidad} creada')
        
        return jsonify({'success': True, 'id': nueva_capacidad.id}), 201

@app.route('/api/catalogo/capacidades/<int:id>', methods=['PUT', 'DELETE'])
def api_capacidad_extintor(id):
    capacidad = CapacidadExtintor.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.json
        capacidad.capacidad = data.get('capacidad', capacidad.capacidad)
        capacidad.unidad = data.get('unidad', capacidad.unidad)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'actualizado', {'id': capacidad.id, 'tipo': 'capacidad'}, f'Capacidad {capacidad.capacidad} actualizada')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        cap_nombre = capacidad.capacidad
        db.session.delete(capacidad)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'eliminado', {'id': id, 'tipo': 'capacidad'}, f'Capacidad {cap_nombre} eliminada')
        
        return jsonify({'success': True})

# API - Catálogo: Marcas
@app.route('/api/catalogo/marcas', methods=['GET', 'POST'])
def api_marcas_extintor():
    if request.method == 'GET':
        marcas = MarcaExtintor.query.filter_by(activo=True).all()
        return jsonify([{
            'id': m.id,
            'nombre': m.nombre,
            'origen': m.origen
        } for m in marcas])
    
    elif request.method == 'POST':
        data = request.json
        nueva_marca = MarcaExtintor(
            nombre=data['nombre'],
            origen=data['origen']
        )
        db.session.add(nueva_marca)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'creado', {'id': nueva_marca.id, 'tipo': 'marca'}, f'Marca {nueva_marca.nombre} creada')
        
        return jsonify({'success': True, 'id': nueva_marca.id}), 201

@app.route('/api/catalogo/marcas/<int:id>', methods=['PUT', 'DELETE'])
def api_marca_extintor(id):
    marca = MarcaExtintor.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.json
        marca.nombre = data.get('nombre', marca.nombre)
        marca.origen = data.get('origen', marca.origen)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'actualizado', {'id': marca.id, 'tipo': 'marca'}, f'Marca {marca.nombre} actualizada')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        marca_nombre = marca.nombre
        db.session.delete(marca)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('catalogo', 'eliminado', {'id': id, 'tipo': 'marca'}, f'Marca {marca_nombre} eliminada')
        
        return jsonify({'success': True})

# API - Extintores
@app.route('/api/extintores', methods=['GET', 'POST'])
def api_extintores():
    if request.method == 'GET':
        # Filtrar por cliente_id si se proporciona
        cliente_id = request.args.get('cliente_id', type=int)
        if cliente_id:
            extintores = Extintor.query.filter_by(cliente_id=cliente_id).all()
        else:
            extintores = Extintor.query.all()
        
        return jsonify([{
            'id': e.id,
            'serie': e.serie,
            'cliente_id': e.cliente_id,
            'cliente_nombre': e.cliente.nombre,
            'tipo': e.tipo or '',
            'capacidad': e.capacidad or '',
            'marca': e.marca or '',
            'fecha_recarga': e.fecha_recarga or '',
            'vencimiento_recarga': e.vencimiento_recarga or '',
            'estado': e.estado,
            'observaciones': e.observaciones or ''
        } for e in extintores])
    
    elif request.method == 'POST':
        data = request.json
        nuevo_extintor = Extintor(
            cliente_id=data['cliente_id'],
            serie=data.get('serie', ''),
            tipo=data.get('tipo', ''),
            capacidad=data.get('capacidad', ''),
            marca=data.get('marca', ''),
            fecha_recarga=data.get('fecha_recarga', ''),
            vencimiento_recarga=data.get('vencimiento_recarga', ''),
            estado=data.get('estado', 'Pendiente'),
            observaciones=data.get('observaciones', '')
        )
        db.session.add(nuevo_extintor)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('extintor', 'creado', {'id': nuevo_extintor.id, 'serie': nuevo_extintor.serie}, f'Extintor {nuevo_extintor.serie} creado')
        
        return jsonify({'success': True, 'id': nuevo_extintor.id}), 201

@app.route('/api/extintores/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_extintor(id):
    extintor = Extintor.query.get_or_404(id)
    
    if request.method == 'GET':
        return jsonify({
            'id': extintor.id,
            'serie': extintor.serie,
            'cliente_id': extintor.cliente_id,
            'tipo': extintor.tipo,
            'capacidad': extintor.capacidad,
            'marca': extintor.marca,
            'fecha_recarga': extintor.fecha_recarga,
            'vencimiento_recarga': extintor.vencimiento_recarga,
            'estado': extintor.estado,
            'observaciones': extintor.observaciones
        })
    
    elif request.method == 'PUT':
        data = request.json
        app.logger.info(f"\n[EXTINTOR UPDATE] ID: {id}")
        app.logger.info(f"[EXTINTOR UPDATE] Datos recibidos: {data}")
        
        # Actualizar campos de la tabla visual
        if 'serie' in data:
            extintor.serie = data['serie']
            app.logger.info(f"[EXTINTOR UPDATE] Serie: {extintor.serie}")
        if 'codigo' in data:  # Alias para serie
            extintor.serie = data['codigo']
        if 'tipo' in data:
            extintor.tipo = data['tipo']
        if 'capacidad' in data:
            extintor.capacidad = data['capacidad']
        if 'marca' in data or 'marca_nombre' in data:
            extintor.marca = data.get('marca') or data.get('marca_nombre')
            app.logger.info(f"[EXTINTOR UPDATE] Marca: {extintor.marca}")
        if 'fecha_recarga' in data:
            extintor.fecha_recarga = data['fecha_recarga']
            app.logger.info(f"[EXTINTOR UPDATE] Fecha recarga: {extintor.fecha_recarga}")
        if 'vencimiento_recarga' in data:
            extintor.vencimiento_recarga = data['vencimiento_recarga']
            app.logger.info(f"[EXTINTOR UPDATE] Vencimiento: {extintor.vencimiento_recarga}")
        if 'observaciones' in data:
            extintor.observaciones = data['observaciones']
        if 'estado' in data:
            extintor.estado = data['estado']
            
        db.session.commit()
        app.logger.info(f"[EXTINTOR UPDATE] ✅ Guardado en BD exitosamente\n")
        
        # Emitir evento de sincronización
        emitir_cambio_global('extintor', 'actualizado', {'id': extintor.id, 'serie': extintor.serie}, f'Extintor {extintor.serie} actualizado')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        db.session.delete(extintor)
        db.session.commit()
        return jsonify({'success': True})

# API - Mantenimientos
@app.route('/api/mantenimientos', methods=['GET', 'POST'])
def api_mantenimientos():
    if request.method == 'GET':
        mantenimientos = Mantenimiento.query.order_by(Mantenimiento.fecha_servicio.desc()).all()
        return jsonify([{
            'id': m.id,
            'extintor_id': m.extintor_id,
            'extintor_serie': m.extintor.serie,
            'cliente_nombre': m.extintor.cliente.nombre,
            'fecha_servicio': m.fecha_servicio.strftime('%Y-%m-%d %H:%M'),
            'tipo_servicio': m.tipo_servicio,
            'tecnico': m.tecnico,
            'observaciones': m.observaciones,
            'costo': m.costo,
            'proximo_servicio': m.proximo_servicio.strftime('%Y-%m-%d') if m.proximo_servicio else None,
            'completado': m.completado
        } for m in mantenimientos])
    
    elif request.method == 'POST':
        data = request.json
        nuevo_mantenimiento = Mantenimiento(
            extintor_id=data['extintor_id'],
            tipo_servicio=data['tipo_servicio'],
            tecnico=data.get('tecnico', ''),
            observaciones=data.get('observaciones', ''),
            costo=data.get('costo', 0.0),
            proximo_servicio=datetime.strptime(data['proximo_servicio'], '%Y-%m-%d').date() if data.get('proximo_servicio') else None,
            completado=data.get('completado', True)
        )
        
        db.session.add(nuevo_mantenimiento)
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_global('mantenimiento', 'creado', {'id': nuevo_mantenimiento.id}, 'Nuevo mantenimiento registrado')
        
        return jsonify({'success': True, 'id': nuevo_mantenimiento.id}), 201

# API - Dashboard
@app.route('/api/dashboard')
def api_dashboard():
    total_clientes = Cliente.query.filter_by(activo=True).count()
    total_extintores = Extintor.query.count()
    
    # Contar extintores por estado
    extintores_proximos = 0  # Se puede calcular desde vencimiento_recarga si es necesario
    extintores_vencidos = 0  # Se puede calcular desde vencimiento_recarga si es necesario
    
    # Mantenimientos del mes
    inicio_mes = datetime.now().replace(day=1)
    mantenimientos_mes = Mantenimiento.query.filter(
        Mantenimiento.fecha_servicio >= inicio_mes
    ).count()
    
    # Ingresos del mes
    ingresos_mes = db.session.query(db.func.sum(Mantenimiento.costo)).filter(
        Mantenimiento.fecha_servicio >= inicio_mes
    ).scalar() or 0
    
    return jsonify({
        'total_clientes': total_clientes,
        'total_extintores': total_extintores,
        'extintores_proximos': extintores_proximos,
        'extintores_vencidos': extintores_vencidos,
        'mantenimientos_mes': mantenimientos_mes,
        'ingresos_mes': float(ingresos_mes)
    })

# API - Alertas
@app.route('/api/alertas')
def api_alertas():
    # Sistema de alertas simplificado - se puede implementar lógica basada en vencimiento_recarga
    # Por ahora retornamos listas vacías
    return jsonify({
        'vencidos': [],
        'proximos_7': [],
        'proximos_30': []
    })

# API - Órdenes de Trabajo
@app.route('/api/ordenes', methods=['GET', 'POST'])
def api_ordenes():
    if request.method == 'GET':
        ordenes = OrdenTrabajo.query.order_by(OrdenTrabajo.fecha_creacion.desc()).all()
        return jsonify([{
            'id': o.id,
            'numero_orden': o.numero_orden,
            'cliente_id': o.cliente_id,
            'cliente_nombre': o.cliente.nombre,
            'fecha_recojo': o.fecha_recojo.strftime('%Y-%m-%d'),
            'cantidad_extintores': o.cantidad_extintores,
            'direccion_recojo': o.direccion_recojo,
            'contacto_recojo': o.contacto_recojo,
            'telefono_contacto': o.telefono_contacto,
            'observaciones': o.observaciones,
            'estado': o.estado,
            'extintores_registrados': len([e for e in o.extintores if e.serie]),
            'fecha_creacion': o.fecha_creacion.strftime('%Y-%m-%d %H:%M')
        } for o in ordenes])
    
    elif request.method == 'POST':
        data = request.json
        
        # Generar número de orden automático
        ultimo_numero = db.session.query(db.func.max(OrdenTrabajo.id)).scalar() or 0
        numero_orden = f"OT-{(ultimo_numero + 1):05d}"
        
        # Determinar etapa inicial según si hay trabajadores asignados
        trabajador_asignado = data.get('trabajador_asignado', '').strip()
        etapa_inicial = 'ASIGNADA' if trabajador_asignado else 'CREADA'
        
        # Si se asignan trabajadores desde la creación, marcar como confirmada
        asignacion_confirmada = True if trabajador_asignado else False
        
        orden = OrdenTrabajo(
            numero_orden=numero_orden,
            cliente_id=data['cliente_id'],
            fecha_recojo=datetime.strptime(data['fecha_recojo'], '%Y-%m-%d').date(),
            cantidad_extintores=data['cantidad_extintores'],
            direccion_recojo=data.get('direccion_recojo', ''),
            contacto_recojo=data.get('contacto_recojo', ''),
            telefono_contacto=data.get('telefono_contacto', ''),
            observaciones=data.get('observaciones', ''),
            trabajador_asignado=trabajador_asignado,
            estado='En Proceso' if trabajador_asignado else 'Pendiente',
            etapa_actual=etapa_inicial,
            confirmada_asignacion_alguna_vez=asignacion_confirmada,
            marcado_recogido_alguna_vez=False,
            enviado_a_oficina=False
        )
        db.session.add(orden)
        db.session.flush()  # Para obtener el ID de la orden
        
        # Guardar detalle de extintores Y crear registros individuales vacíos
        if 'extintores' in data and data['extintores']:
            for ext_data in data['extintores']:
                # Guardar detalle (resumen)
                detalle = OrdenExtintorDetalle(
                    orden_id=orden.id,
                    tipo_id=ext_data['tipo_id'],
                    capacidad_id=ext_data['capacidad_id'],
                    cantidad=ext_data['cantidad']
                )
                db.session.add(detalle)
                
                # Crear registros individuales vacíos (uno por cada extintor)
                tipo = db.session.get(TipoExtintor, ext_data['tipo_id'])
                capacidad = db.session.get(CapacidadExtintor, ext_data['capacidad_id'])
                
                for i in range(ext_data['cantidad']):
                    extintor = Extintor(
                        cliente_id=data['cliente_id'],
                        orden_trabajo_id=orden.id,
                        tipo=tipo.nombre if tipo else '',
                        capacidad=capacidad.capacidad if capacidad else '',
                        serie='',  # Pendiente de llenar
                        marca='',  # Pendiente de llenar
                        fecha_recarga='',  # Pendiente de llenar
                        vencimiento_recarga='',  # Pendiente de llenar
                        observaciones='',
                        estado='Pendiente'
                    )
                    db.session.add(extintor)
        
        db.session.commit()
        
        # Emitir evento de nueva orden creada
        emitir_cambio_orden(orden.id, 'orden_creada', {'numero_orden': orden.numero_orden})
        emitir_cambio_global('orden', 'creado', {'id': orden.id, 'numero_orden': orden.numero_orden}, f'Orden {orden.numero_orden} creada')
        
        return jsonify({
            'success': True,
            'id': orden.id,
            'numero_orden': orden.numero_orden
        })

@app.route('/api/ordenes/<int:orden_id>', methods=['GET', 'PUT', 'DELETE'])
def api_orden_detalle(orden_id):
    orden = OrdenTrabajo.query.get_or_404(orden_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': orden.id,
            'numero_orden': orden.numero_orden,
            'cliente_id': orden.cliente_id,
            'cliente_nombre': orden.cliente.nombre,
            'fecha_recojo': orden.fecha_recojo.strftime('%Y-%m-%d'),
            'cantidad_extintores': orden.cantidad_extintores,
            'direccion_recojo': orden.direccion_recojo,
            'contacto_recojo': orden.contacto_recojo,
            'telefono_contacto': orden.telefono_contacto,
            'observaciones': orden.observaciones,
            'estado': orden.estado,
            'recogido': orden.recogido,
            'fecha_recogido_real': orden.fecha_recogido_real.strftime('%Y-%m-%d') if orden.fecha_recogido_real else None,
            'extintores_detalle': [{
                'tipo_id': d.tipo_id,
                'tipo_nombre': d.tipo.nombre,
                'capacidad_id': d.capacidad_id,
                'capacidad_nombre': d.capacidad.capacidad,
                'cantidad': d.cantidad
            } for d in orden.extintores_detalle],
            'extintores': [{
                'id': e.id,
                'serie': e.serie or '',
                'tipo': e.tipo or '',
                'capacidad': e.capacidad or '',
                'marca': e.marca or '',
                'fecha_recarga': e.fecha_recarga or '',
                'vencimiento_recarga': e.vencimiento_recarga or '',
                'observaciones': e.observaciones or '',
                'estado': e.estado
            } for e in orden.extintores],
            'fecha_creacion': orden.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
            'etapa_actual': orden.etapa_actual or 'CREADA',
            'trabajador_asignado': orden.trabajador_asignado,
            'fecha_completado_trabajador': orden.fecha_completado_trabajador.strftime('%Y-%m-%d %H:%M') if orden.fecha_completado_trabajador else None,
            'fecha_revision_oficina': orden.fecha_revision_oficina.strftime('%Y-%m-%d %H:%M') if orden.fecha_revision_oficina else None,
            'fecha_recarga_seleccionada': orden.fecha_recarga_seleccionada,  # Última fecha seleccionada en el combobox
            'enviado_a_oficina': orden.enviado_a_oficina or False,  # Indicador permanente de envío a oficina
            'fecha_envio_oficina': orden.fecha_envio_oficina.strftime('%Y-%m-%d %H:%M') if orden.fecha_envio_oficina else None,
            'marcado_recogido_alguna_vez': orden.marcado_recogido_alguna_vez or False,  # Indicador permanente de recojo
            'confirmada_asignacion_alguna_vez': orden.confirmada_asignacion_alguna_vez or False,  # Indicador permanente de asignación
            'revision_finalizada': orden.revision_finalizada or False,  # Indicador de si la revisión fue finalizada
            'tiene_evidencia_fotografica': orden.tiene_evidencia_fotografica or False,  # Indicador de si tiene fotos (basado en cantidad de fotos, no en checkbox)
            'tiene_foto_guia': orden.tiene_foto_guia or False  # Indicador de si tiene fotos de guía de recojo
        })
    
    elif request.method == 'PUT':
        data = request.json
        orden.estado = data.get('estado', orden.estado)
        orden.observaciones = data.get('observaciones', orden.observaciones)
        db.session.commit()
        
        # Emitir evento de cambio
        emitir_cambio_orden(orden_id, 'orden_actualizada')
        emitir_cambio_global('orden', 'actualizado', {'id': orden_id, 'numero_orden': orden.numero_orden}, f'Orden {orden.numero_orden} actualizada')
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        numero_orden = orden.numero_orden
        
        try:
            # Eliminar primero las fotos asociadas
            FotoRecojo.query.filter_by(orden_id=orden_id).delete()
            FotoGuiaRecojo.query.filter_by(orden_id=orden_id).delete()
            
            # Eliminar extintores asociados a esta orden
            Extintor.query.filter_by(orden_trabajo_id=orden_id).delete()
            
            # Ahora eliminar la orden
            db.session.delete(orden)
            db.session.commit()
            
            # Emitir evento global
            emitir_cambio_global('orden', 'eliminado', {'id': orden_id, 'numero_orden': numero_orden}, f'Orden {numero_orden} eliminada')
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error al eliminar orden {numero_orden}: {str(e)}")
            return jsonify({'success': False, 'error': f'No se pudo eliminar la orden: {str(e)}'}), 500

@app.route('/api/ordenes/<int:orden_id>/marcar-recogido', methods=['POST'])
def api_marcar_recogido(orden_id):
    try:
        app.logger.info(f"\n[MARCAR-RECOGIDO] Orden ID: {orden_id}")
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        
        # Guardar estado anterior para saber si es primera vez
        # Usar el campo permanente para determinar si ALGUNA VEZ se marcó
        ya_fue_marcado_antes = orden.marcado_recogido_alguna_vez == True
        
        data = request.json
        recogido = data.get('recogido', False)
        
        app.logger.info(f"[MARCAR-RECOGIDO] ===== INICIO =====")
        app.logger.info(f"[MARCAR-RECOGIDO] Estado en BD ANTES: orden.recogido = {orden.recogido}")
        app.logger.info(f"[MARCAR-RECOGIDO] Nuevo valor solicitado: {recogido}")
        app.logger.info(f"[MARCAR-RECOGIDO] Ya fue marcado alguna vez (permanente): {ya_fue_marcado_antes}")
        
        # Verificar si los campos existen en el modelo
        if not hasattr(orden, 'recogido'):
            app.logger.error("[MARCAR-RECOGIDO] ERROR: Campo 'recogido' no existe")
            return jsonify({
                'success': False,
                'error': 'La base de datos necesita ser migrada. Ejecuta: python migrar_db.py'
            }), 400
        
        app.logger.info(f"[MARCAR-RECOGIDO] Extintores detalle: {len(orden.extintores_detalle) if hasattr(orden, 'extintores_detalle') else 0}")
        orden.recogido = recogido
        
        if recogido:
            # Marcar fecha de recojo real y cambiar etapa
            orden.fecha_recogido_real = datetime.now().date()
            orden.etapa_actual = 'RECOGIDO'
            
            # Marcar como recogido alguna vez (permanente, nunca vuelve a False)
            if not orden.marcado_recogido_alguna_vez:
                orden.marcado_recogido_alguna_vez = True
            
            # IMPORTANTE: Desmarcar revisión finalizada al CONFIRMAR cambio en Recojo
            if orden.revision_finalizada:
                orden.revision_finalizada = False
                app.logger.info(f"[MARCAR-RECOGIDO] ⚠️ Revisión desmarcada por cambio CONFIRMADO en Recojo")
            
            # Generar extintores automáticamente basados en el detalle
            extintores_generados = 0
            if hasattr(orden, 'extintores_detalle') and orden.extintores_detalle:
                for detalle in orden.extintores_detalle:
                    for i in range(detalle.cantidad):
                        # Verificar si ya existen extintores generados
                        extintores_existentes = len([e for e in orden.extintores])
                        if extintores_existentes >= orden.cantidad_extintores:
                            break
                        
                        # Crear extintor con tipo y capacidad predefinidos
                        extintor = Extintor(
                            cliente_id=orden.cliente_id,
                            orden_trabajo_id=orden.id,
                            tipo=detalle.tipo.nombre if detalle.tipo else '',
                            capacidad=detalle.capacidad.capacidad if detalle.capacidad else '',
                            estado='Pendiente'
                        )
                        db.session.add(extintor)
                        extintores_generados += 1
            
            # Cambiar estado de la orden
            if orden.estado == 'Pendiente':
                orden.estado = 'En Proceso'
        else:
            # Desmarcar: volver a etapa ASIGNADA
            orden.recogido = False  # IMPORTANTE: Guardar como False en BD
            orden.fecha_recogido_real = None
            orden.etapa_actual = 'ASIGNADA'
            # Si se desmarca, eliminar extintores generados automáticamente (sin serie)
            for extintor in orden.extintores:
                if not extintor.serie:
                    db.session.delete(extintor)
        
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_orden(orden_id, 'recogido_actualizado', {'recogido': recogido})
        
        total_extintores = len(orden.extintores)
        
        # Determinar si es primera vez (solo si se está marcando Y nunca fue marcado antes)
        es_primera_vez = recogido and not ya_fue_marcado_antes
        
        app.logger.info(f"[MARCAR-RECOGIDO] ===== RESULTADO =====")
        app.logger.info(f"[MARCAR-RECOGIDO] Estado en BD DESPUÉS: orden.recogido = {orden.recogido}")
        app.logger.info(f"[MARCAR-RECOGIDO] Campo permanente DESPUÉS: marcado_recogido_alguna_vez = {orden.marcado_recogido_alguna_vez}")
        app.logger.info(f"[MARCAR-RECOGIDO] Es primera vez: {es_primera_vez}")
        app.logger.info(f"[MARCAR-RECOGIDO] Lógica: recogido={recogido} AND NOT ya_fue_marcado_antes={ya_fue_marcado_antes}")
        
        # Emitir evento de cambio
        emitir_cambio_orden(orden_id, 'recogido_actualizado', {'recogido': recogido})
        
        return jsonify({
            'success': True,
            'recogido': orden.recogido,
            'extintores_generados': total_extintores,
            'es_primera_vez': es_primera_vez
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== ENDPOINTS PARA FOTOS DE RECOJO ====================

def actualizar_evidencia_fotografica(orden_id):
    """Actualiza el campo tiene_evidencia_fotografica basado en si hay fotos"""
    try:
        orden = OrdenTrabajo.query.get(orden_id)
        if orden:
            # Contar cuántas fotos tiene la orden
            cantidad_fotos = FotoRecojo.query.filter_by(orden_id=orden_id).count()
            # Actualizar el campo: True si hay al menos 1 foto, False si no hay ninguna
            orden.tiene_evidencia_fotografica = (cantidad_fotos > 0)
            db.session.commit()
            app.logger.info(f"[EVIDENCIA] Orden {orden_id}: {cantidad_fotos} foto(s) - tiene_evidencia_fotografica={orden.tiene_evidencia_fotografica}")
    except Exception as e:
        app.logger.error(f"[EVIDENCIA] Error al actualizar evidencia: {str(e)}")

@app.route('/api/ordenes/<int:orden_id>/fotos', methods=['POST'])
def api_subir_foto_recojo(orden_id):
    """Subir una foto de evidencia del recojo"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        
        # Verificar que se envió un archivo
        if 'foto' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ninguna foto'}), 400
        
        file = request.files['foto']
        
        # Verificar que el archivo tiene nombre
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Archivo sin nombre'}), 400
        
        # Verificar que es una imagen
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Formato de archivo no permitido'}), 400
        
        # Crear carpeta para las fotos si no existe
        fotos_dir = os.path.join('static', 'fotos_recojo', f'orden_{orden_id}')
        os.makedirs(fotos_dir, exist_ok=True)
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        nombre_archivo = f'foto_{timestamp}.{file_ext}'
        ruta_completa = os.path.join(fotos_dir, nombre_archivo)
        
        # Guardar el archivo
        file.save(ruta_completa)
        
        # Obtener tamaño del archivo
        tamanio = os.path.getsize(ruta_completa)
        
        # Guardar registro en la base de datos
        ruta_relativa = f'fotos_recojo/orden_{orden_id}/{nombre_archivo}'
        foto = FotoRecojo(
            orden_id=orden_id,
            nombre_archivo=nombre_archivo,
            ruta_archivo=ruta_relativa,
            tamanio_bytes=tamanio
        )
        
        db.session.add(foto)
        db.session.commit()
        
        # Actualizar el campo tiene_evidencia_fotografica
        actualizar_evidencia_fotografica(orden_id)
        
        app.logger.info(f"[FOTO-RECOJO] Foto guardada: {nombre_archivo} ({tamanio} bytes)")
        
        # Emitir evento de cambio
        emitir_cambio_orden(orden_id, 'foto_evidencia_agregada', {'foto_id': foto.id})
        
        return jsonify({
            'success': True,
            'foto': {
                'id': foto.id,
                'nombre_archivo': foto.nombre_archivo,
                'url': f'/static/{ruta_relativa}',
                'fecha_captura': foto.fecha_captura.strftime('%Y-%m-%d %H:%M:%S'),
                'tamanio_bytes': foto.tamanio_bytes
            }
        })
        
    except Exception as e:
        app.logger.error(f"[FOTO-RECOJO] Error al subir foto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/fotos', methods=['GET'])
def api_obtener_fotos_recojo(orden_id):
    """Obtener todas las fotos de una orden"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        fotos = FotoRecojo.query.filter_by(orden_id=orden_id).order_by(FotoRecojo.fecha_captura.desc()).all()
        
        fotos_data = []
        for foto in fotos:
            fotos_data.append({
                'id': foto.id,
                'nombre_archivo': foto.nombre_archivo,
                'url': f'/static/{foto.ruta_archivo}',
                'fecha_captura': foto.fecha_captura.strftime('%Y-%m-%d %H:%M:%S'),
                'tamanio_bytes': foto.tamanio_bytes
            })
        
        return jsonify({
            'success': True,
            'fotos': fotos_data,
            'total': len(fotos_data)
        })
        
    except Exception as e:
        app.logger.error(f"[FOTO-RECOJO] Error al obtener fotos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/fotos/<int:foto_id>', methods=['DELETE'])
def api_eliminar_foto_recojo(orden_id, foto_id):
    """Eliminar una foto de evidencia"""
    try:
        foto = FotoRecojo.query.filter_by(id=foto_id, orden_id=orden_id).first_or_404()
        
        # Eliminar archivo físico
        ruta_completa = os.path.join('static', foto.ruta_archivo)
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
            app.logger.info(f"[FOTO-RECOJO] Archivo eliminado: {ruta_completa}")
        
        # Eliminar registro de la BD
        db.session.delete(foto)
        db.session.commit()
        
        # Actualizar el campo tiene_evidencia_fotografica
        actualizar_evidencia_fotografica(orden_id)
        
        app.logger.info(f"[FOTO-RECOJO] Foto eliminada: ID {foto_id}")
        
        # Emitir evento de cambio
        emitir_cambio_orden(orden_id, 'foto_evidencia_eliminada', {'foto_id': foto_id})
        
        return jsonify({'success': True, 'message': 'Foto eliminada correctamente'})
        
    except Exception as e:
        app.logger.error(f"[FOTO-RECOJO] Error al eliminar foto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENDPOINTS PARA FOTOS DE GUÍA DE RECOJO ====================

def actualizar_foto_guia(orden_id):
    """Actualiza el campo tiene_foto_guia basado en si hay fotos de guía"""
    try:
        orden = OrdenTrabajo.query.get(orden_id)
        if orden:
            # Contar cuántas fotos de guía tiene la orden
            cantidad_fotos = FotoGuiaRecojo.query.filter_by(orden_id=orden_id).count()
            # Actualizar el campo: True si hay al menos 1 foto, False si no hay ninguna
            orden.tiene_foto_guia = (cantidad_fotos > 0)
            db.session.commit()
            app.logger.info(f"[FOTO-GUIA] Orden {orden_id}: {cantidad_fotos} foto(s) - tiene_foto_guia={orden.tiene_foto_guia}")
    except Exception as e:
        app.logger.error(f"[FOTO-GUIA] Error al actualizar foto guía: {str(e)}")

@app.route('/api/ordenes/<int:orden_id>/fotos-guia', methods=['POST'])
def api_subir_foto_guia(orden_id):
    """Subir una foto de guía de recojo"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        
        # Verificar que se envió un archivo
        if 'foto' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ninguna foto'}), 400
        
        file = request.files['foto']
        
        # Verificar que el archivo tiene nombre
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Archivo sin nombre'}), 400
        
        # Verificar que es una imagen
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Formato de archivo no permitido'}), 400
        
        # Crear carpeta para las fotos si no existe
        fotos_dir = os.path.join('static', 'fotos_guia_recojo', f'orden_{orden_id}')
        os.makedirs(fotos_dir, exist_ok=True)
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        nombre_archivo = f'guia_{timestamp}.{file_ext}'
        ruta_completa = os.path.join(fotos_dir, nombre_archivo)
        
        # Guardar el archivo
        file.save(ruta_completa)
        
        # Obtener tamaño del archivo
        tamanio = os.path.getsize(ruta_completa)
        
        # Guardar registro en la base de datos
        ruta_relativa = f'fotos_guia_recojo/orden_{orden_id}/{nombre_archivo}'
        foto = FotoGuiaRecojo(
            orden_id=orden_id,
            nombre_archivo=nombre_archivo,
            ruta_archivo=ruta_relativa,
            tamanio_bytes=tamanio
        )
        
        db.session.add(foto)
        db.session.commit()
        
        # Actualizar el campo tiene_foto_guia
        actualizar_foto_guia(orden_id)
        
        app.logger.info(f"[FOTO-GUIA] Foto guardada: {nombre_archivo} ({tamanio} bytes)")
        
        # Emitir evento de cambio
        emitir_cambio_orden(orden_id, 'foto_guia_agregada', {'foto_id': foto.id})
        
        return jsonify({
            'success': True,
            'foto': {
                'id': foto.id,
                'nombre_archivo': foto.nombre_archivo,
                'url': f'/static/{ruta_relativa}',
                'fecha_captura': foto.fecha_captura.strftime('%Y-%m-%d %H:%M:%S'),
                'tamanio_bytes': foto.tamanio_bytes
            }
        })
        
    except Exception as e:
        app.logger.error(f"[FOTO-GUIA] Error al subir foto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/fotos-guia', methods=['GET'])
def api_obtener_fotos_guia(orden_id):
    """Obtener todas las fotos de guía de una orden"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        fotos = FotoGuiaRecojo.query.filter_by(orden_id=orden_id).order_by(FotoGuiaRecojo.fecha_captura.desc()).all()
        
        fotos_data = []
        for foto in fotos:
            fotos_data.append({
                'id': foto.id,
                'nombre_archivo': foto.nombre_archivo,
                'url': f'/static/{foto.ruta_archivo}',
                'fecha_captura': foto.fecha_captura.strftime('%Y-%m-%d %H:%M:%S'),
                'tamanio_bytes': foto.tamanio_bytes
            })
        
        return jsonify({
            'success': True,
            'fotos': fotos_data,
            'total': len(fotos_data)
        })
        
    except Exception as e:
        app.logger.error(f"[FOTO-GUIA] Error al obtener fotos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/fotos-guia/<int:foto_id>', methods=['DELETE'])
def api_eliminar_foto_guia(orden_id, foto_id):
    """Eliminar una foto de guía"""
    try:
        foto = FotoGuiaRecojo.query.filter_by(id=foto_id, orden_id=orden_id).first_or_404()
        
        # Eliminar archivo físico
        ruta_completa = os.path.join('static', foto.ruta_archivo)
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
            app.logger.info(f"[FOTO-GUIA] Archivo eliminado: {ruta_completa}")
        
        # Eliminar registro de la BD
        db.session.delete(foto)
        db.session.commit()
        
        # Actualizar el campo tiene_foto_guia
        actualizar_foto_guia(orden_id)
        
        app.logger.info(f"[FOTO-GUIA] Foto eliminada: ID {foto_id}")
        
        # Emitir evento de cambio
        emitir_cambio_orden(orden_id, 'foto_guia_eliminada', {'foto_id': foto_id})
        
        return jsonify({'success': True, 'message': 'Foto eliminada correctamente'})
        
    except Exception as e:
        app.logger.error(f"[FOTO-GUIA] Error al eliminar foto: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== FIN ENDPOINTS FOTOS ====================

# Endpoints para sistema de etapas
@app.route('/api/ordenes/<int:orden_id>/asignar-trabajador', methods=['POST'])
def api_asignar_trabajador(orden_id):
    """Guarda trabajadores SIN cambiar la etapa (para agregar/eliminar trabajadores)"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        data = request.json
        
        trabajador = data.get('trabajador', '').strip()
        orden.trabajador_asignado = trabajador if trabajador else None
        
        # Si se eliminan TODOS los trabajadores, volver a CREADA
        if not trabajador:
            orden.etapa_actual = 'CREADA'
            # NO DESMARCAR confirmada_asignacion_alguna_vez - es permanente
            # NO tocar orden.recogido - cada pestaña es independiente
        # Si hay trabajadores pero la etapa es CREADA, mantenerla en CREADA
        # (no cambiar hasta que se confirme)
        
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_orden(orden_id, 'trabajadores_asignados', {
            'trabajadores': trabajador
        })
        
        return jsonify({'success': True, 'etapa': orden.etapa_actual})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/confirmar-asignacion', methods=['POST'])
def api_confirmar_asignacion(orden_id):
    """Confirma la asignación de trabajadores y cambia la etapa a ASIGNADA"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        
        # Verificar que haya trabajadores
        if not orden.trabajador_asignado or not orden.trabajador_asignado.strip():
            return jsonify({'success': False, 'error': 'No hay trabajadores asignados'}), 400
        
        # Guardar estado anterior para saber si es primera vez
        ya_fue_confirmada_antes = orden.confirmada_asignacion_alguna_vez == True
        
        # Cambiar etapa a ASIGNADA
        orden.etapa_actual = 'ASIGNADA'
        
        # Marcar como confirmada alguna vez (permanente, nunca vuelve a False)
        if not orden.confirmada_asignacion_alguna_vez:
            orden.confirmada_asignacion_alguna_vez = True
        
        # IMPORTANTE: Desmarcar revisión finalizada al CONFIRMAR cambio en Asignación
        if orden.revision_finalizada:
            orden.revision_finalizada = False
            app.logger.info(f"[CONFIRMAR-ASIGNACION] ⚠️ Revisión desmarcada por cambio CONFIRMADO en Asignación")
        
        db.session.commit()
        
        # Es primera vez si nunca fue confirmada antes
        es_primera_vez = not ya_fue_confirmada_antes
        
        # Emitir evento de sincronización para que todos los dispositivos se actualicen
        emitir_cambio_orden(orden_id, 'trabajadores_confirmados', {
            'trabajadores': orden.trabajador_asignado,
            'etapa': orden.etapa_actual
        })
        emitir_cambio_global('orden', 'actualizado', {
            'id': orden_id,
            'numero_orden': orden.numero_orden
        }, f'Trabajadores confirmados en orden {orden.numero_orden}')
        
        return jsonify({
            'success': True,
            'etapa': orden.etapa_actual,
            'es_primera_vez': es_primera_vez
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Endpoint obsoleto eliminado - usar /enviar-revision en su lugar

@app.route('/api/ordenes/<int:orden_id>/guardar-fecha-recarga', methods=['POST'])
def api_guardar_fecha_recarga(orden_id):
    """Guarda la fecha de recarga seleccionada automáticamente"""
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        data = request.json or {}
        
        fecha_recarga = data.get('fecha_recarga_seleccionada')
        if fecha_recarga:
            orden.fecha_recarga_seleccionada = fecha_recarga
            db.session.commit()
            
            app.logger.info(f"[FECHA-RECARGA] ✅ Guardada automáticamente: {fecha_recarga}")
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Fecha no proporcionada'}), 400
            
    except Exception as e:
        app.logger.error(f"[FECHA-RECARGA] ❌ Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/enviar-revision', methods=['POST'])
def api_enviar_revision(orden_id):
    """Envía la orden a oficina para revisión (cambia de RECOGIDO a REVISION)"""
    try:
        app.logger.info(f"\n[ENVIAR-REVISION] ========== INICIO ==========")
        app.logger.info(f"[ENVIAR-REVISION] Orden ID: {orden_id}")
        
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        data = request.json or {}
        
        app.logger.info(f"[ENVIAR-REVISION] Datos recibidos: {data}")
        app.logger.info(f"[ENVIAR-REVISION] Content-Type: {request.content_type}")
        
        # Marcar como completado por el trabajador y enviar a revisión
        orden.etapa_actual = 'REVISION'
        orden.fecha_completado_trabajador = datetime.now()
        
        # IMPORTANTE: Marcar como enviado a oficina (permanente, no se revierte)
        if not orden.enviado_a_oficina:
            orden.enviado_a_oficina = True
            orden.fecha_envio_oficina = datetime.now()
            app.logger.info(f"[ENVIAR-REVISION] ✅ Primera vez enviado a oficina - Marcado permanentemente")
        else:
            app.logger.info(f"[ENVIAR-REVISION] ℹ️ Ya estaba marcado como enviado a oficina")
        
        # Guardar la fecha de recarga seleccionada si se envió
        if 'fecha_recarga_seleccionada' in data:
            orden.fecha_recarga_seleccionada = data['fecha_recarga_seleccionada']
            app.logger.info(f"[ENVIAR-REVISION] ✅ Fecha recarga guardada: {orden.fecha_recarga_seleccionada}")
        else:
            app.logger.warning(f"[ENVIAR-REVISION] ⚠️ NO se recibió fecha_recarga_seleccionada en los datos")
        
        # IMPORTANTE: Desmarcar revisión finalizada al CONFIRMAR envío a oficina (cambio en Registro)
        if orden.revision_finalizada:
            orden.revision_finalizada = False
            app.logger.info(f"[ENVIAR-REVISION] ⚠️ Revisión desmarcada por cambio CONFIRMADO en Registro")
        
        db.session.commit()
        app.logger.info(f"[ENVIAR-REVISION] ✅ Cambios guardados en BD")
        
        # Emitir evento de sincronización
        emitir_cambio_orden(orden_id, 'orden_actualizada', {
            'etapa': orden.etapa_actual
        })
        emitir_cambio_global('orden', 'actualizado', {
            'id': orden_id,
            'numero_orden': orden.numero_orden
        }, f'Orden {orden.numero_orden} enviada a oficina')
        
        app.logger.info(f"[ENVIAR-REVISION] ========== FIN ==========\n")
        
        return jsonify({'success': True, 'etapa': orden.etapa_actual})
    except Exception as e:
        app.logger.error(f"[ENVIAR-REVISION] ❌ ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/finalizar', methods=['POST'])
def api_finalizar_orden(orden_id):
    try:
        orden = OrdenTrabajo.query.get_or_404(orden_id)
        
        orden.etapa_actual = 'FINALIZADO'
        orden.fecha_revision_oficina = datetime.now()
        orden.estado = 'Completada'
        
        # Marcar revisión como finalizada
        orden.revision_finalizada = True
        
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_orden(orden_id, 'orden_actualizada', {
            'etapa': 'FINALIZADO',
            'estado': 'Completada'
        })
        emitir_cambio_global('orden', 'actualizado', {
            'id': orden_id,
            'numero_orden': orden.numero_orden
        }, f'Orden {orden.numero_orden} finalizada')
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ordenes/<int:orden_id>/extintores', methods=['POST'])
def api_orden_agregar_extintor(orden_id):
    orden = OrdenTrabajo.query.get_or_404(orden_id)
    data = request.json
    
    extintor = Extintor(
        cliente_id=orden.cliente_id,
        orden_trabajo_id=orden.id,
        serie=data.get('serie', ''),
        tipo=data.get('tipo', ''),
        capacidad=data.get('capacidad', ''),
        marca=data.get('marca', ''),
        fecha_recarga=data.get('fecha_recarga', ''),
        vencimiento_recarga=data.get('vencimiento_recarga', ''),
        estado=data.get('estado', 'Pendiente'),
        observaciones=data.get('observaciones')
    )
    db.session.add(extintor)
    
    # Actualizar estado de la orden si todos los extintores están registrados
    extintores_registrados = len([e for e in orden.extintores if e.serie]) + 1
    if extintores_registrados >= orden.cantidad_extintores:
        orden.estado = 'Completada'
    elif extintores_registrados > 0:
        orden.estado = 'En Proceso'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': extintor.id
    })

@app.route('/api/ordenes/<int:orden_id>/extintores/<int:extintor_id>', methods=['PUT', 'DELETE'])
def api_orden_extintor_detalle(orden_id, extintor_id):
    extintor = Extintor.query.get_or_404(extintor_id)
    orden = OrdenTrabajo.query.get_or_404(orden_id)
    
    if request.method == 'PUT':
        data = request.json
        
        # Actualizar campos del extintor
        if 'serie' in data:
            extintor.serie = data['serie']
        if 'tipo' in data:
            extintor.tipo = data['tipo']
        if 'capacidad' in data:
            extintor.capacidad = data['capacidad']
        if 'marca' in data:
            extintor.marca = data['marca']
        if 'fecha_recarga' in data:
            extintor.fecha_recarga = data['fecha_recarga']
        if 'vencimiento_recarga' in data:
            extintor.vencimiento_recarga = data['vencimiento_recarga']
        if 'observaciones' in data:
            extintor.observaciones = data['observaciones']
        
        db.session.commit()
        
        # Emitir evento de sincronización
        emitir_cambio_orden(orden_id, 'celda_actualizada', {
            'extintor_id': extintor_id,
            'campo': list(data.keys())[0] if data else 'unknown',
            'valor': list(data.values())[0] if data else ''
        })
        
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        db.session.delete(extintor)
        db.session.commit()
        return jsonify({'success': True})

# Generar PDF de certificado
@app.route('/api/certificado/<int:mantenimiento_id>')
def generar_certificado(mantenimiento_id):
    mantenimiento = Mantenimiento.query.get_or_404(mantenimiento_id)
    extintor = mantenimiento.extintor
    cliente = extintor.cliente
    
    filename = f'certificado_{extintor.serie}_{datetime.now().strftime("%Y%m%d")}.pdf'
    filepath = os.path.join('static', 'temp', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Título
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 50, "CERTIFICADO DE MANTENIMIENTO")
    
    # Información
    c.setFont("Helvetica", 12)
    y = height - 100
    
    c.drawString(50, y, f"Cliente: {cliente.nombre}")
    y -= 25
    c.drawString(50, y, f"Dirección: {cliente.direccion}")
    y -= 40
    
    c.drawString(50, y, f"Serie Extintor: {extintor.serie}")
    y -= 25
    c.drawString(50, y, f"Tipo: {extintor.tipo} - Capacidad: {extintor.capacidad}")
    y -= 25
    c.drawString(50, y, f"Marca: {extintor.marca or 'N/A'}")
    y -= 40
    
    c.drawString(50, y, f"Tipo de Servicio: {mantenimiento.tipo_servicio}")
    y -= 25
    c.drawString(50, y, f"Fecha de Servicio: {mantenimiento.fecha_servicio.strftime('%d/%m/%Y')}")
    y -= 25
    c.drawString(50, y, f"Técnico: {mantenimiento.tecnico}")
    y -= 25
    if mantenimiento.proximo_servicio:
        c.drawString(50, y, f"Próximo Servicio: {mantenimiento.proximo_servicio.strftime('%d/%m/%Y')}")
    y -= 40
    
    if mantenimiento.observaciones:
        c.drawString(50, y, "Observaciones:")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(70, y, mantenimiento.observaciones[:100])
    
    c.save()
    
    return send_file(filepath, as_attachment=True, download_name=filename)

def abrir_navegador():
    webbrowser.open('http://127.0.0.1:5000')

# API de Logs
@app.route('/api/logs', methods=['GET'])
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def api_logs():
    """Obtener logs del sistema"""
    try:
        cantidad = int(request.args.get('cantidad', 100))
        
        # Leer el archivo de logs
        log_file = 'logs/app.log'
        
        if not os.path.exists(log_file):
            return jsonify({'logs': [], 'mensaje': 'No hay archivo de logs'})
        
        # Leer las últimas N líneas
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lineas = f.readlines()
            ultimas_lineas = lineas[-cantidad:] if len(lineas) > cantidad else lineas
        
        return jsonify({'logs': [linea.strip() for linea in ultimas_lineas]})
    except Exception as e:
        app.logger.error(f"Error al leer logs: {str(e)}")
        return jsonify({'logs': [], 'error': str(e)}), 500

@app.route('/api/logs/limpiar', methods=['POST'])
@login_required
@role_required('PRINCIPAL')
def api_limpiar_logs():
    """Limpiar archivo de logs (solo PRINCIPAL)"""
    try:
        log_file = 'logs/app.log'
        
        if os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('')
            app.logger.info(f"[LOGS] Logs limpiados por usuario: {session.get('user_nombre')}")
        
        return jsonify({'success': True, 'mensaje': 'Logs limpiados exitosamente'})
    except Exception as e:
        app.logger.error(f"Error al limpiar logs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# API de Gestión de Servidores
@app.route('/api/servidores', methods=['GET'])
@login_required
@role_required('PRINCIPAL', 'ADMINISTRATIVO')
def api_servidores():
    """Obtener lista de servidores Python activos"""
    try:
        import psutil
        
        servidores = []
        pid_actual = os.getpid()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Solo mostrar procesos que ejecutan app.py
                    if 'app.py' not in cmdline:
                        continue
                    
                    # Detectar puerto (siempre 5000 por defecto)
                    puerto = 5000
                    if '--port' in cmdline:
                        try:
                            parts = cmdline.split()
                            idx = parts.index('--port')
                            if idx + 1 < len(parts):
                                puerto = int(parts[idx + 1])
                        except:
                            puerto = 5000
                    
                    # Calcular tiempo activo
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    tiempo_activo = datetime.now() - create_time
                    
                    # Formatear tiempo
                    horas = int(tiempo_activo.total_seconds() // 3600)
                    minutos = int((tiempo_activo.total_seconds() % 3600) // 60)
                    tiempo_str = f"{horas}h {minutos}m"
                    
                    es_actual = (proc.info['pid'] == pid_actual)
                    
                    servidores.append({
                        'pid': proc.info['pid'],
                        'comando': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline,
                        'puerto': puerto,
                        'tiempo_activo': tiempo_str,
                        'es_este_servidor': es_actual
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return jsonify({'servidores': servidores})
    except Exception as e:
        app.logger.error(f"Error al obtener servidores: {str(e)}")
        return jsonify({'servidores': [], 'error': str(e)}), 500

@app.route('/api/servidores/detener', methods=['POST'])
@login_required
@role_required('PRINCIPAL')
def api_detener_servidor():
    """Detener un servidor específico por PID"""
    try:
        import psutil
        
        data = request.json
        pid = data.get('pid')
        pid_actual = os.getpid()
        
        if pid == pid_actual:
            return jsonify({'success': False, 'error': 'No puedes detener el servidor actual desde aquí'}), 400
        
        try:
            proceso = psutil.Process(pid)
            proceso.terminate()
            proceso.wait(timeout=5)
            
            app.logger.info(f"[SERVIDORES] Servidor PID {pid} detenido por usuario: {session.get('user_nombre')}")
            return jsonify({'success': True, 'mensaje': f'Servidor {pid} detenido'})
        except psutil.NoSuchProcess:
            return jsonify({'success': False, 'error': 'Proceso no encontrado'}), 404
        except psutil.TimeoutExpired:
            proceso.kill()
            return jsonify({'success': True, 'mensaje': f'Servidor {pid} forzado a detenerse'})
    except Exception as e:
        app.logger.error(f"Error al detener servidor: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servidores/detener-todos', methods=['POST'])
@login_required
@role_required('PRINCIPAL')
def api_detener_todos_servidores():
    """Detener todos los servidores Python"""
    try:
        import psutil
        
        pid_actual = os.getpid()
        detenidos = 0
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    if proc.info['pid'] != pid_actual:
                        proc.terminate()
                        detenidos += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        app.logger.info(f"[SERVIDORES] {detenidos} servidores detenidos por usuario: {session.get('user_nombre')}")
        
        # Detener este servidor al final
        import threading
        def detener_este():
            import time
            time.sleep(1)
            os._exit(0)
        
        threading.Thread(target=detener_este).start()
        
        return jsonify({'success': True, 'mensaje': f'{detenidos} servidores detenidos'})
    except Exception as e:
        app.logger.error(f"Error al detener servidores: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/servidores/reiniciar', methods=['POST'])
@login_required
@role_required('PRINCIPAL')
def api_reiniciar_servidor():
    """Reiniciar el servidor actual"""
    try:
        import sys
        import subprocess
        
        app.logger.info(f"[SERVIDORES] Servidor reiniciado por usuario: {session.get('user_nombre')}")
        
        # Reiniciar el servidor usando subprocess
        import threading
        def reiniciar():
            import time
            time.sleep(2)
            
            # Obtener el comando actual
            python_exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            
            # Iniciar nuevo proceso
            if os.name == 'nt':  # Windows
                subprocess.Popen([python_exe, script], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE,
                               cwd=os.path.dirname(script))
            else:  # Linux/Mac
                subprocess.Popen([python_exe, script])
            
            # Cerrar este proceso
            time.sleep(1)
            os._exit(0)
        
        threading.Thread(target=reiniciar, daemon=True).start()
        
        return jsonify({'success': True, 'mensaje': 'Servidor reiniciando...'})
    except Exception as e:
        app.logger.error(f"Error al reiniciar servidor: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Inicializar base de datos
with app.app_context():
    db.create_all()
    
    # Poblar catálogo si está vacío (para producción)
    if TipoExtintor.query.count() == 0:
        print("📦 Poblando catálogo inicial...")
        
        # Tipos de extintores
        tipos = [
            {'nombre': 'PQS', 'nombre_completo': 'Polvo Químico Seco', 'clase_fuego': 'ABC', 'color': '#dc3545'},
            {'nombre': 'CO2', 'nombre_completo': 'Dióxido de Carbono', 'clase_fuego': 'BC', 'color': '#000000'},
            {'nombre': 'H2O Pres.', 'nombre_completo': 'Agua Presurizada', 'clase_fuego': 'A', 'color': '#0d6efd'},
            {'nombre': 'H2O Desm.', 'nombre_completo': 'Agua Desmineralizada', 'clase_fuego': 'A', 'color': '#17a2b8'},
            {'nombre': 'AFFF', 'nombre_completo': 'Espuma Formadora de Película Acuosa', 'clase_fuego': 'AB', 'color': '#28a745'},
            {'nombre': 'Acetato de Potasio', 'nombre_completo': 'Acetato de Potasio', 'clase_fuego': 'K', 'color': '#6f42c1'},
            {'nombre': 'Halotron', 'nombre_completo': 'Halotron I', 'clase_fuego': 'ABC', 'color': '#fd7e14'}
        ]
        
        for tipo_data in tipos:
            tipo = TipoExtintor(**tipo_data)
            db.session.add(tipo)
        
        # Capacidades
        capacidades = [
            {'valor': 1, 'unidad': 'kg'}, {'valor': 2, 'unidad': 'kg'}, {'valor': 4, 'unidad': 'kg'},
            {'valor': 6, 'unidad': 'kg'}, {'valor': 9, 'unidad': 'kg'}, {'valor': 12, 'unidad': 'kg'},
            {'valor': 2.5, 'unidad': 'gal'}, {'valor': 10, 'unidad': 'lb'}, {'valor': 20, 'unidad': 'lb'}
        ]
        
        for cap_data in capacidades:
            cap = CapacidadExtintor(**cap_data)
            db.session.add(cap)
        
        # Marcas
        marcas = [
            {'nombre': 'FIREX', 'origen': 'Nacional'},
            {'nombre': 'SOLKAFLAM', 'origen': 'Nacional'},
            {'nombre': 'AMEREX', 'origen': 'Americano'},
            {'nombre': 'BADGER', 'origen': 'Americano'},
            {'nombre': 'ANSUL', 'origen': 'Americano'}
        ]
        
        for marca_data in marcas:
            marca = MarcaExtintor(**marca_data)
            db.session.add(marca)
        
        db.session.commit()
        print("✅ Catálogo poblado correctamente")

if __name__ == '__main__':
    import sys
    import os
    from logging.handlers import RotatingFileHandler
    
    # Crear carpeta de logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configurar logging ANTES de iniciar Flask
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    
    # Handler para archivo (con rotación)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    
    # Configurar logging con ambos handlers
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )
    
    # Deshabilitar logs de werkzeug para usar nuestros propios logs
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Obtener IP local
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "No disponible"
    
    logging.info("\n" + "="*60)
    logging.info("  SISTEMA DE GESTION DE EXTINTORES v2.0")
    logging.info("  Consulta RUC: API Factiliza")
    logging.info("  🔄 Sincronización en Tiempo Real: ACTIVADA")
    logging.info("="*60)
    logging.info("\n[OK] Servidor iniciado correctamente")
    logging.info("[OK] Abre la vista previa del navegador en tu IDE")
    logging.info("\n-> URL Local: http://127.0.0.1:5000")
    logging.info(f"-> Desde tu celular: http://{local_ip}:5000")
    logging.info("\n[INFO] Los logs se mostraran aqui en tiempo real:")
    logging.info("  - Consultas RUC (API Factiliza)")
    logging.info("  - Clientes guardados correctamente")
    logging.info("  - Cambios sincronizados entre dispositivos")
    logging.info("  - Errores y warnings detallados")
    logging.info("\n[INFO] Para detener: Presiona CTRL+C")
    logging.info("="*60 + "\n")
    
    # Usar SocketIO en lugar de app.run() para soporte de WebSockets
    socketio.run(
        app,
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG'],
        use_reloader=app.config['USE_RELOADER'],
        allow_unsafe_werkzeug=True
    )
