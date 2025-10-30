from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(50), default='usuario')  # admin, usuario
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    movimientos = db.relationship('Movimiento', backref='usuario', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'


class Categoria(db.Model):
    __tablename__ = 'categorias'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(3), unique=True, nullable=False)  # Código único de 3 dígitos
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    productos = db.relationship('Producto', backref='categoria', lazy=True)
    
    def __repr__(self):
        return f'<Categoria {self.codigo} - {self.nombre}>'


class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    unidad_medida = db.Column(db.String(50), nullable=False)  # unidad, caja, litro, kg, etc.
    stock_actual = db.Column(db.Float, default=0)
    stock_minimo = db.Column(db.Float, default=0)
    precio_unitario = db.Column(db.Float, default=0)
    ubicacion = db.Column(db.String(100))  # Estante, almacén, etc.
    tiene_modelos = db.Column(db.Boolean, default=False)  # Indica si el producto maneja modelos
    tiene_colores = db.Column(db.Boolean, default=False)  # Indica si el producto maneja colores
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    movimientos = db.relationship('Movimiento', backref='producto', lazy=True)
    modelos = db.relationship('ProductoModelo', backref='producto', lazy=True, cascade='all, delete-orphan')
    caracteristicas = db.relationship('ProductoCaracteristica', backref='producto', lazy=True, cascade='all, delete-orphan')
    
    @property
    def valor_total(self):
        return self.stock_actual * self.precio_unitario
    
    @property
    def necesita_reposicion(self):
        return self.stock_actual <= self.stock_minimo
    
    def __repr__(self):
        return f'<Producto {self.codigo} - {self.nombre}>'


class ProductoModelo(db.Model):
    __tablename__ = 'producto_modelos'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    nombre_modelo = db.Column(db.String(100), nullable=False)
    codigo_modelo = db.Column(db.String(50))  # Código específico del modelo
    descripcion = db.Column(db.Text)
    stock_actual = db.Column(db.Float, default=0)
    precio_diferencial = db.Column(db.Float, default=0)  # Diferencia de precio respecto al producto base
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    colores = db.relationship('ProductoColor', backref='modelo', lazy=True, cascade='all, delete-orphan')
    
    @property
    def precio_final(self):
        return self.producto.precio_unitario + self.precio_diferencial
    
    def __repr__(self):
        return f'<ProductoModelo {self.nombre_modelo}>'


class ProductoColor(db.Model):
    __tablename__ = 'producto_colores'
    
    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('producto_modelos.id'), nullable=False)
    nombre_color = db.Column(db.String(50), nullable=False)
    codigo_color = db.Column(db.String(20))  # Código hexadecimal o referencia
    stock_actual = db.Column(db.Float, default=0)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProductoColor {self.nombre_color}>'


class ProductoCaracteristica(db.Model):
    __tablename__ = 'producto_caracteristicas'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)  # Ej: "Talla", "Material", "Voltaje"
    valor = db.Column(db.String(200), nullable=False)  # Ej: "XL", "Acero", "220V"
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProductoCaracteristica {self.nombre}: {self.valor}>'


class Movimiento(db.Model):
    __tablename__ = 'movimientos'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    modelo_id = db.Column(db.Integer, db.ForeignKey('producto_modelos.id'), nullable=True)  # Opcional si el movimiento es de un modelo específico
    color_id = db.Column(db.Integer, db.ForeignKey('producto_colores.id'), nullable=True)  # Opcional si el movimiento es de un color específico
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tipo_movimiento = db.Column(db.String(20), nullable=False)  # entrada, salida, ajuste
    cantidad = db.Column(db.Float, nullable=False)
    stock_anterior = db.Column(db.Float, nullable=False)
    stock_nuevo = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(200))
    observaciones = db.Column(db.Text)
    documento_referencia = db.Column(db.String(100))  # Factura, guía, etc.
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Movimiento {self.tipo_movimiento} - {self.cantidad}>'
