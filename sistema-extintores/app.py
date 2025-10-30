from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Usuario, Categoria, Producto, Movimiento, ProductoModelo, ProductoColor, ProductoCaracteristica
from config import Config
from datetime import datetime
from sqlalchemy import func, desc
import os
import json

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and usuario.check_password(password) and usuario.activo:
            login_user(usuario)
            flash(f'¡Bienvenido {usuario.nombre_completo}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

# ==================== DASHBOARD ====================

@app.route('/')
@login_required
def dashboard():
    # Estadísticas generales
    total_productos = Producto.query.filter_by(activo=True).count()
    total_categorias = Categoria.query.filter_by(activo=True).count()
    
    # Productos con stock bajo
    productos_bajo_stock = Producto.query.filter(
        Producto.activo == True,
        Producto.stock_actual <= Producto.stock_minimo
    ).all()
    
    # Valor total del inventario
    valor_total = db.session.query(func.sum(Producto.stock_actual * Producto.precio_unitario)).filter(
        Producto.activo == True
    ).scalar() or 0
    
    # Últimos movimientos
    ultimos_movimientos = Movimiento.query.order_by(desc(Movimiento.fecha_movimiento)).limit(10).all()
    
    # Productos más movidos (últimos 30 días)
    productos_top = db.session.query(
        Producto.nombre,
        func.count(Movimiento.id).label('total_movimientos')
    ).join(Movimiento).group_by(Producto.id).order_by(desc('total_movimientos')).limit(5).all()
    
    return render_template('dashboard.html',
                         total_productos=total_productos,
                         total_categorias=total_categorias,
                         productos_bajo_stock=productos_bajo_stock,
                         valor_total=valor_total,
                         ultimos_movimientos=ultimos_movimientos,
                         productos_top=productos_top)

# ==================== CATEGORÍAS ====================

@app.route('/categorias')
@login_required
def categorias():
    categorias = Categoria.query.filter_by(activo=True).all()
    return render_template('categorias.html', categorias=categorias)

@app.route('/categorias/nueva', methods=['GET', 'POST'])
@login_required
def nueva_categoria():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        
        if Categoria.query.filter_by(nombre=nombre).first():
            flash('Ya existe una categoría con ese nombre', 'warning')
            return redirect(url_for('nueva_categoria'))
        
        # Generar código automático (siguiente número disponible)
        ultima_categoria = Categoria.query.order_by(Categoria.codigo.desc()).first()
        if ultima_categoria:
            ultimo_num = int(ultima_categoria.codigo)
            nuevo_codigo = f"{ultimo_num + 1:03d}"
        else:
            nuevo_codigo = "001"
        
        categoria = Categoria(codigo=nuevo_codigo, nombre=nombre, descripcion=descripcion)
        db.session.add(categoria)
        db.session.commit()
        
        flash(f'Categoría creada exitosamente con código {nuevo_codigo}', 'success')
        return redirect(url_for('categorias'))
    
    return render_template('categoria_form.html', categoria=None)

@app.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        
        # Verificar si el nombre ya existe (excepto para esta categoría)
        existe = Categoria.query.filter(Categoria.nombre == nombre, Categoria.id != id).first()
        if existe:
            flash('Ya existe una categoría con ese nombre', 'warning')
            return redirect(url_for('editar_categoria', id=id))
        
        categoria.nombre = nombre
        categoria.descripcion = descripcion
        db.session.commit()
        
        flash('Categoría actualizada exitosamente', 'success')
        return redirect(url_for('categorias'))
    
    return render_template('categoria_form.html', categoria=categoria)

@app.route('/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    
    # Verificar si tiene productos asociados
    if categoria.productos:
        flash('No se puede eliminar la categoría porque tiene productos asociados', 'danger')
    else:
        categoria.activo = False
        db.session.commit()
        flash('Categoría eliminada exitosamente', 'success')
    
    return redirect(url_for('categorias'))

# ==================== PRODUCTOS ====================

@app.route('/productos')
@login_required
def productos():
    page = request.args.get('page', 1, type=int)
    categoria_id = request.args.get('categoria', type=int)
    busqueda = request.args.get('busqueda', '')
    
    query = Producto.query.filter_by(activo=True)
    
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    
    if busqueda:
        query = query.filter(
            (Producto.nombre.contains(busqueda)) | 
            (Producto.codigo.contains(busqueda))
        )
    
    productos = query.order_by(Producto.nombre).paginate(
        page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    categorias = Categoria.query.filter_by(activo=True).all()
    
    return render_template('productos.html', 
                         productos=productos, 
                         categorias=categorias,
                         categoria_seleccionada=categoria_id,
                         busqueda=busqueda)

@app.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_producto():
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        categoria_id = request.form.get('categoria_id')
        unidad_medida = request.form.get('unidad_medida')
        stock_actual = float(request.form.get('stock_actual', 0))
        stock_minimo = float(request.form.get('stock_minimo', 0))
        precio_unitario = float(request.form.get('precio_unitario', 0))
        ubicacion = request.form.get('ubicacion')
        tiene_modelos = request.form.get('tiene_modelos') == 'on'
        tiene_colores = request.form.get('tiene_colores') == 'on'
        
        if Producto.query.filter_by(codigo=codigo).first():
            flash('Ya existe un producto con ese código', 'warning')
            return redirect(url_for('nuevo_producto'))
        
        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            categoria_id=categoria_id,
            unidad_medida=unidad_medida,
            stock_actual=stock_actual,
            stock_minimo=stock_minimo,
            precio_unitario=precio_unitario,
            ubicacion=ubicacion,
            tiene_modelos=tiene_modelos,
            tiene_colores=tiene_colores
        )
        
        db.session.add(producto)
        db.session.flush()  # Para obtener el ID del producto
        
        # Guardar características personalizadas
        caracteristicas_json = request.form.get('caracteristicas_data', '[]')
        try:
            caracteristicas = json.loads(caracteristicas_json)
            for caract in caracteristicas:
                if caract.get('nombre') and caract.get('valor'):
                    caracteristica = ProductoCaracteristica(
                        producto_id=producto.id,
                        nombre=caract['nombre'],
                        valor=caract['valor']
                    )
                    db.session.add(caracteristica)
        except json.JSONDecodeError:
            pass
        
        db.session.commit()
        
        # Registrar movimiento inicial si hay stock
        if stock_actual > 0:
            movimiento = Movimiento(
                producto_id=producto.id,
                usuario_id=current_user.id,
                tipo_movimiento='entrada',
                cantidad=stock_actual,
                stock_anterior=0,
                stock_nuevo=stock_actual,
                motivo='Stock inicial'
            )
            db.session.add(movimiento)
            db.session.commit()
        
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('ver_producto', id=producto.id))
    
    categorias = Categoria.query.filter_by(activo=True).all()
    return render_template('producto_form.html', producto=None, categorias=categorias)

@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        categoria_id = request.form.get('categoria_id')
        unidad_medida = request.form.get('unidad_medida')
        stock_minimo = float(request.form.get('stock_minimo', 0))
        precio_unitario = float(request.form.get('precio_unitario', 0))
        ubicacion = request.form.get('ubicacion')
        tiene_modelos = request.form.get('tiene_modelos') == 'on'
        tiene_colores = request.form.get('tiene_colores') == 'on'
        
        # Verificar si el código ya existe (excepto para este producto)
        existe = Producto.query.filter(Producto.codigo == codigo, Producto.id != id).first()
        if existe:
            flash('Ya existe un producto con ese código', 'warning')
            return redirect(url_for('editar_producto', id=id))
        
        producto.codigo = codigo
        producto.nombre = nombre
        producto.descripcion = descripcion
        producto.categoria_id = categoria_id
        producto.unidad_medida = unidad_medida
        producto.stock_minimo = stock_minimo
        producto.precio_unitario = precio_unitario
        producto.ubicacion = ubicacion
        producto.tiene_modelos = tiene_modelos
        producto.tiene_colores = tiene_colores
        
        # Actualizar características
        # Eliminar características existentes
        ProductoCaracteristica.query.filter_by(producto_id=producto.id).delete()
        
        # Agregar nuevas características
        caracteristicas_json = request.form.get('caracteristicas_data', '[]')
        try:
            caracteristicas = json.loads(caracteristicas_json)
            for caract in caracteristicas:
                if caract.get('nombre') and caract.get('valor'):
                    caracteristica = ProductoCaracteristica(
                        producto_id=producto.id,
                        nombre=caract['nombre'],
                        valor=caract['valor']
                    )
                    db.session.add(caracteristica)
        except json.JSONDecodeError:
            pass
        
        db.session.commit()
        
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('ver_producto', id=producto.id))
    
    categorias = Categoria.query.filter_by(activo=True).all()
    return render_template('producto_form.html', producto=producto, categorias=categorias)

@app.route('/productos/ver/<int:id>')
@login_required
def ver_producto(id):
    producto = Producto.query.get_or_404(id)
    movimientos = Movimiento.query.filter_by(producto_id=id).order_by(desc(Movimiento.fecha_movimiento)).limit(20).all()
    return render_template('producto_detalle.html', producto=producto, movimientos=movimientos)

@app.route('/productos/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = False
    db.session.commit()
    
    flash('Producto eliminado exitosamente', 'success')
    return redirect(url_for('productos'))

# ==================== MODELOS DE PRODUCTOS ====================

@app.route('/productos/<int:producto_id>/modelos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_modelo(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    if not producto.tiene_modelos:
        flash('Este producto no está configurado para manejar modelos', 'warning')
        return redirect(url_for('ver_producto', id=producto_id))
    
    if request.method == 'POST':
        nombre_modelo = request.form.get('nombre_modelo')
        codigo_modelo = request.form.get('codigo_modelo')
        descripcion = request.form.get('descripcion')
        stock_actual = float(request.form.get('stock_actual', 0))
        precio_diferencial = float(request.form.get('precio_diferencial', 0))
        
        modelo = ProductoModelo(
            producto_id=producto_id,
            nombre_modelo=nombre_modelo,
            codigo_modelo=codigo_modelo,
            descripcion=descripcion,
            stock_actual=stock_actual,
            precio_diferencial=precio_diferencial
        )
        
        db.session.add(modelo)
        db.session.flush()
        
        # Si el producto también maneja colores, agregar colores al modelo
        if producto.tiene_colores:
            colores_json = request.form.get('colores_data', '[]')
            try:
                colores = json.loads(colores_json)
                for color_data in colores:
                    if color_data.get('nombre'):
                        color = ProductoColor(
                            modelo_id=modelo.id,
                            nombre_color=color_data['nombre'],
                            codigo_color=color_data.get('codigo', ''),
                            stock_actual=float(color_data.get('stock', 0))
                        )
                        db.session.add(color)
            except json.JSONDecodeError:
                pass
        
        db.session.commit()
        
        flash(f'Modelo "{nombre_modelo}" agregado exitosamente', 'success')
        return redirect(url_for('ver_producto', id=producto_id))
    
    return render_template('modelo_form.html', producto=producto, modelo=None)

@app.route('/productos/<int:producto_id>/modelos/<int:modelo_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_modelo(producto_id, modelo_id):
    producto = Producto.query.get_or_404(producto_id)
    modelo = ProductoModelo.query.get_or_404(modelo_id)
    
    if request.method == 'POST':
        modelo.nombre_modelo = request.form.get('nombre_modelo')
        modelo.codigo_modelo = request.form.get('codigo_modelo')
        modelo.descripcion = request.form.get('descripcion')
        modelo.precio_diferencial = float(request.form.get('precio_diferencial', 0))
        
        # Actualizar colores si aplica
        if producto.tiene_colores:
            # Eliminar colores existentes
            ProductoColor.query.filter_by(modelo_id=modelo.id).delete()
            
            # Agregar nuevos colores
            colores_json = request.form.get('colores_data', '[]')
            try:
                colores = json.loads(colores_json)
                for color_data in colores:
                    if color_data.get('nombre'):
                        color = ProductoColor(
                            modelo_id=modelo.id,
                            nombre_color=color_data['nombre'],
                            codigo_color=color_data.get('codigo', ''),
                            stock_actual=float(color_data.get('stock', 0))
                        )
                        db.session.add(color)
            except json.JSONDecodeError:
                pass
        
        db.session.commit()
        
        flash(f'Modelo "{modelo.nombre_modelo}" actualizado exitosamente', 'success')
        return redirect(url_for('ver_producto', id=producto_id))
    
    return render_template('modelo_form.html', producto=producto, modelo=modelo)

@app.route('/productos/<int:producto_id>/modelos/<int:modelo_id>/eliminar', methods=['POST'])
@login_required
def eliminar_modelo(producto_id, modelo_id):
    modelo = ProductoModelo.query.get_or_404(modelo_id)
    modelo.activo = False
    db.session.commit()
    
    flash('Modelo eliminado exitosamente', 'success')
    return redirect(url_for('ver_producto', id=producto_id))

# ==================== MOVIMIENTOS ====================

@app.route('/movimientos')
@login_required
def movimientos():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo', '')
    
    query = Movimiento.query
    
    if tipo:
        query = query.filter_by(tipo_movimiento=tipo)
    
    movimientos = query.order_by(desc(Movimiento.fecha_movimiento)).paginate(
        page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    return render_template('movimientos.html', movimientos=movimientos, tipo_seleccionado=tipo)

@app.route('/movimientos/entrada', methods=['GET', 'POST'])
@login_required
def entrada_stock():
    if request.method == 'POST':
        producto_id = request.form.get('producto_id')
        cantidad = float(request.form.get('cantidad'))
        motivo = request.form.get('motivo')
        observaciones = request.form.get('observaciones')
        documento = request.form.get('documento')
        
        producto = Producto.query.get_or_404(producto_id)
        stock_anterior = producto.stock_actual
        producto.stock_actual += cantidad
        
        movimiento = Movimiento(
            producto_id=producto_id,
            usuario_id=current_user.id,
            tipo_movimiento='entrada',
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=producto.stock_actual,
            motivo=motivo,
            observaciones=observaciones,
            documento_referencia=documento
        )
        
        db.session.add(movimiento)
        db.session.commit()
        
        flash(f'Entrada registrada: +{cantidad} {producto.unidad_medida} de {producto.nombre}', 'success')
        return redirect(url_for('movimientos'))
    
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    return render_template('movimiento_form.html', productos=productos, tipo='entrada')

@app.route('/movimientos/salida', methods=['GET', 'POST'])
@login_required
def salida_stock():
    if request.method == 'POST':
        producto_id = request.form.get('producto_id')
        cantidad = float(request.form.get('cantidad'))
        motivo = request.form.get('motivo')
        observaciones = request.form.get('observaciones')
        documento = request.form.get('documento')
        
        producto = Producto.query.get_or_404(producto_id)
        
        if cantidad > producto.stock_actual:
            flash(f'Stock insuficiente. Stock actual: {producto.stock_actual} {producto.unidad_medida}', 'danger')
            return redirect(url_for('salida_stock'))
        
        stock_anterior = producto.stock_actual
        producto.stock_actual -= cantidad
        
        movimiento = Movimiento(
            producto_id=producto_id,
            usuario_id=current_user.id,
            tipo_movimiento='salida',
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=producto.stock_actual,
            motivo=motivo,
            observaciones=observaciones,
            documento_referencia=documento
        )
        
        db.session.add(movimiento)
        db.session.commit()
        
        flash(f'Salida registrada: -{cantidad} {producto.unidad_medida} de {producto.nombre}', 'success')
        return redirect(url_for('movimientos'))
    
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    return render_template('movimiento_form.html', productos=productos, tipo='salida')

@app.route('/movimientos/ajuste', methods=['GET', 'POST'])
@login_required
def ajuste_stock():
    if request.method == 'POST':
        producto_id = request.form.get('producto_id')
        nuevo_stock = float(request.form.get('nuevo_stock'))
        motivo = request.form.get('motivo')
        observaciones = request.form.get('observaciones')
        
        producto = Producto.query.get_or_404(producto_id)
        stock_anterior = producto.stock_actual
        diferencia = nuevo_stock - stock_anterior
        producto.stock_actual = nuevo_stock
        
        movimiento = Movimiento(
            producto_id=producto_id,
            usuario_id=current_user.id,
            tipo_movimiento='ajuste',
            cantidad=abs(diferencia),
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            motivo=motivo,
            observaciones=observaciones
        )
        
        db.session.add(movimiento)
        db.session.commit()
        
        flash(f'Ajuste registrado: {producto.nombre} - Stock ajustado a {nuevo_stock} {producto.unidad_medida}', 'success')
        return redirect(url_for('movimientos'))
    
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    return render_template('movimiento_form.html', productos=productos, tipo='ajuste')

# ==================== REPORTES ====================

@app.route('/reportes')
@login_required
def reportes():
    return render_template('reportes.html')

@app.route('/reportes/stock-bajo')
@login_required
def reporte_stock_bajo():
    productos = Producto.query.filter(
        Producto.activo == True,
        Producto.stock_actual <= Producto.stock_minimo
    ).order_by(Producto.nombre).all()
    
    return render_template('reporte_stock_bajo.html', productos=productos, now=datetime.now())

@app.route('/reportes/valorizado')
@login_required
def reporte_valorizado():
    productos = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    
    total_general = sum(p.valor_total for p in productos)
    
    return render_template('reporte_valorizado.html', productos=productos, total_general=total_general, now=datetime.now())

# ==================== API ENDPOINTS ====================

@app.route('/api/producto/<int:id>')
@login_required
def api_producto(id):
    producto = Producto.query.get_or_404(id)
    return jsonify({
        'id': producto.id,
        'codigo': producto.codigo,
        'nombre': producto.nombre,
        'stock_actual': producto.stock_actual,
        'unidad_medida': producto.unidad_medida,
        'precio_unitario': producto.precio_unitario
    })

@app.route('/api/siguiente-codigo')
@login_required
def siguiente_codigo():
    import re
    
    categoria_id = request.args.get('categoria_id', '')
    ubicacion = request.args.get('ubicacion', '')
    
    if not categoria_id or not ubicacion:
        return jsonify({'error': 'Faltan parámetros'}), 400
    
    # Obtener la categoría
    categoria = Categoria.query.get(categoria_id)
    if not categoria:
        return jsonify({'error': 'Categoría no encontrada'}), 404
    
    # Mapeo de ubicaciones a códigos de 3 caracteres
    ubicaciones_map = {
        'Oficina': 'OFI',
        'Almacén': 'ALM',
        'Taller': 'TAL'
    }
    
    ubi_codigo = ubicaciones_map.get(ubicacion, ubicacion[:3].upper())
    
    # Formato: CAT(3)-UBI(3)-NNNN(4)
    # Ejemplo: 001-TAL-0001
    patron_base = f"{categoria.codigo}-{ubi_codigo}-"
    
    # Buscar productos con códigos similares
    productos = Producto.query.filter(Producto.codigo.like(f"{patron_base}%")).all()
    
    # Encontrar el número más alto
    max_num = 0
    for producto in productos:
        # Extraer el número del código (últimos 4 dígitos)
        match = re.search(r'-(\d{4})$', producto.codigo)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    # Generar el siguiente número (4 dígitos, soporta hasta 9999)
    siguiente_num = max_num + 1
    codigo_generado = f"{patron_base}{siguiente_num:04d}"
    
    return jsonify({'codigo': codigo_generado})


# ==================== INICIALIZACIÓN ====================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Crear usuario admin por defecto si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                nombre_completo='Administrador',
                email='admin@abingenieria.com',
                rol='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Crear categorías por defecto con códigos únicos
            categorias_default = [
                Categoria(codigo='001', nombre='Herramientas', descripcion='Herramientas manuales y eléctricas'),
                Categoria(codigo='002', nombre='Equipos', descripcion='Equipos y maquinaria de trabajo'),
                Categoria(codigo='003', nombre='Insumos Químicos', descripcion='Productos químicos y materiales de recarga'),
                Categoria(codigo='004', nombre='Materiales', descripcion='Materiales diversos y consumibles'),
                Categoria(codigo='005', nombre='Papelería', descripcion='Útiles de escritorio y papelería'),
                Categoria(codigo='006', nombre='EPPs', descripcion='Equipos de protección personal'),
                Categoria(codigo='007', nombre='Repuestos', descripcion='Repuestos y accesorios'),
                Categoria(codigo='008', nombre='Mobiliario', descripcion='Muebles y mobiliario')
            ]
            
            for cat in categorias_default:
                db.session.add(cat)
            
            db.session.commit()
            print('Base de datos inicializada con datos por defecto')
            print('Usuario: admin | Contraseña: admin123')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
