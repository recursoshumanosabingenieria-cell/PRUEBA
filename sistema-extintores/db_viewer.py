"""
Visor y Editor de Base de Datos SQLite
Interfaz web simple para visualizar y editar la base de datos
"""
from flask import Flask, render_template_string, request, jsonify
import sqlite3
import json

app = Flask(__name__)
DB_PATH = 'instance/extintores.db'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Visor de Base de Datos - Sistema Extintores</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .table-container { margin-top: 20px; overflow-x: auto; }
        .editable { background-color: #f8f9fa; cursor: pointer; }
        .editable:hover { background-color: #e9ecef; }
        pre { background: #f4f4f4; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>Visor de Base de Datos SQLite</h1>
        <p class="text-muted">Base de datos: <code>instance/extintores.db</code></p>
        
        <div class="btn-group mb-3" role="group">
            <button type="button" class="btn btn-primary" onclick="mostrarSeccion('tablas')">📋 Tablas</button>
            <button type="button" class="btn btn-outline-primary" onclick="mostrarSeccion('relaciones')">🔗 Relaciones</button>
        </div>
        
        <div id="seccionTablas">
                <div class="row">
                    <div class="col-md-3">
                        <h4>Tablas</h4>
                        <div class="list-group" id="tablesList"></div>
                    </div>
                    
                    <div class="col-md-9">
                        <div id="tableContent">
                            <div class="alert alert-info">
                                Selecciona una tabla de la izquierda para ver su contenido
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h4>Ejecutar SQL</h4>
                            <textarea class="form-control" id="sqlQuery" rows="3" placeholder="SELECT * FROM tabla WHERE ..."></textarea>
                            <button class="btn btn-primary mt-2" onclick="ejecutarSQL()">Ejecutar</button>
                            <div id="sqlResult" class="mt-3"></div>
                        </div>
                    </div>
                </div>
        </div>
        
        <div id="seccionRelaciones" style="display: none;">
            <h4>Diagrama de Relaciones (ERD)</h4>
            <div id="relationshipDiagram" class="mt-3"></div>
            <div class="mt-4">
                <h5>Detalles de Foreign Keys</h5>
                <div id="foreignKeysList"></div>
            </div>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentTable = null;
        
        function mostrarSeccion(seccion) {
            if (seccion === 'tablas') {
                $('#seccionTablas').show();
                $('#seccionRelaciones').hide();
                $('.btn-group button').eq(0).removeClass('btn-outline-primary').addClass('btn-primary');
                $('.btn-group button').eq(1).removeClass('btn-primary').addClass('btn-outline-primary');
            } else {
                $('#seccionTablas').hide();
                $('#seccionRelaciones').show();
                $('.btn-group button').eq(0).removeClass('btn-primary').addClass('btn-outline-primary');
                $('.btn-group button').eq(1).removeClass('btn-outline-primary').addClass('btn-primary');
            }
        }
        
        function cargarTablas() {
            fetch('/api/tables')
                .then(r => r.json())
                .then(tables => {
                    const list = $('#tablesList');
                    list.empty();
                    tables.forEach(table => {
                        list.append(`
                            <a href="#" class="list-group-item list-group-item-action" onclick="cargarTabla('${table.name}'); return false;">
                                ${table.name} <span class="badge bg-secondary">${table.count}</span>
                            </a>
                        `);
                    });
                });
        }
        
        function cargarTabla(tableName) {
            currentTable = tableName;
            fetch('/api/table/' + tableName)
                .then(r => r.json())
                .then(data => {
                    let html = `
                        <h4>${tableName} <span class="badge bg-primary">${data.rows.length} registros</span></h4>
                        <button class="btn btn-success btn-sm mb-2" onclick="agregarRegistro()">+ Agregar</button>
                        <div class="table-container">
                            <table class="table table-striped table-bordered table-sm">
                                <thead class="table-dark">
                                    <tr>
                    `;
                    
                    data.columns.forEach(col => {
                        html += `<th>${col}</th>`;
                    });
                    html += '<th>Acciones</th></tr></thead><tbody>';
                    
                    data.rows.forEach((row, idx) => {
                        html += '<tr>';
                        data.columns.forEach((col, colIdx) => {
                            const value = row[colIdx] || '';
                            html += `<td class="editable" onclick="editarCelda(this, '${col}', ${row[0]})">${value}</td>`;
                        });
                        html += `<td><button class="btn btn-danger btn-sm" onclick="eliminarRegistro(${row[0]})">Eliminar</button></td>`;
                        html += '</tr>';
                    });
                    
                    html += '</tbody></table></div>';
                    $('#tableContent').html(html);
                });
        }
        
        function editarCelda(cell, column, id) {
            const oldValue = $(cell).text();
            const input = $('<input type="text" class="form-control form-control-sm">').val(oldValue);
            $(cell).html(input);
            input.focus();
            
            input.blur(function() {
                const newValue = $(this).val();
                if (newValue !== oldValue) {
                    guardarCelda(currentTable, column, id, newValue, cell);
                } else {
                    $(cell).text(oldValue);
                }
            });
            
            input.keypress(function(e) {
                if (e.which === 13) {
                    $(this).blur();
                }
            });
        }
        
        function guardarCelda(table, column, id, value, cell) {
            fetch('/api/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({table, column, id, value})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    $(cell).text(value);
                    alert('✓ Guardado');
                } else {
                    alert('Error: ' + data.error);
                    cargarTabla(currentTable);
                }
            });
        }
        
        function eliminarRegistro(id) {
            if (!confirm('¿Eliminar este registro?')) return;
            
            fetch('/api/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({table: currentTable, id})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    cargarTabla(currentTable);
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
        
        function ejecutarSQL() {
            const query = $('#sqlQuery').val();
            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    let html = '<div class="alert alert-success">Ejecutado correctamente</div>';
                    if (data.rows) {
                        html += '<pre>' + JSON.stringify(data.rows, null, 2) + '</pre>';
                    }
                    $('#sqlResult').html(html);
                } else {
                    $('#sqlResult').html('<div class="alert alert-danger">Error: ' + data.error + '</div>');
                }
            });
        }
        
        function crearTarjetaTabla(table, color) {
            let html = `
                <div style="border: 2px solid ${color}; background: white; padding: 15px; border-radius: 8px; min-width: 280px; max-width: 350px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h6 style="color: ${color}; margin-bottom: 12px; font-weight: bold; border-bottom: 1px solid ${color}; padding-bottom: 5px;">
                        ${table.name}
                    </h6>
                    <div style="font-size: 0.85em; line-height: 1.6;">
            `;
            
            table.columns.forEach(col => {
                let icon = col.pk ? '🔑 ' : (col.fk ? '🔗 ' : '• ');
                let badge = col.pk ? '<span style="background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.75em; margin-left: 5px;">PK</span>' : 
                           (col.fk ? '<span style="background: #0d6efd; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.75em; margin-left: 5px;">FK</span>' : '');
                let style = col.pk ? 'font-weight: bold; color: #dc3545;' : (col.fk ? 'color: #0d6efd; font-weight: 500;' : 'color: #495057;');
                html += `<div style="${style}">${icon}${col.name} ${badge}<span style="color: #6c757d; font-size: 0.9em; margin-left: 5px;">${col.type}</span></div>`;
            });
            
            html += '</div></div>';
            return html;
        }
        
        function cargarRelaciones() {
            fetch('/api/relationships')
                .then(r => r.json())
                .then(data => {
                    // Organizar tablas por categorías
                    const catalogos = data.tables.filter(t => t.name.includes('tipo_') || t.name.includes('capacidad_') || t.name.includes('marca_'));
                    const principales = data.tables.filter(t => ['cliente', 'orden_trabajo', 'extintor'].includes(t.name));
                    const otras = data.tables.filter(t => !catalogos.includes(t) && !principales.includes(t));
                    
                    let diagramHTML = '<div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">';
                    
                    // Sección de Catálogos
                    diagramHTML += '<div style="margin-bottom: 30px;"><h5 style="color: #6c757d; border-bottom: 2px solid #6c757d; padding-bottom: 5px;">📚 CATÁLOGOS</h5><div style="display: flex; flex-wrap: wrap; gap: 15px;">';
                    catalogos.forEach(table => {
                        diagramHTML += crearTarjetaTabla(table, '#28a745');
                    });
                    diagramHTML += '</div></div>';
                    
                    // Sección de Tablas Principales
                    diagramHTML += '<div style="margin-bottom: 30px;"><h5 style="color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 5px;">🏢 TABLAS PRINCIPALES</h5><div style="display: flex; flex-wrap: wrap; gap: 15px;">';
                    principales.forEach(table => {
                        diagramHTML += crearTarjetaTabla(table, '#0d6efd');
                    });
                    diagramHTML += '</div></div>';
                    
                    // Otras tablas
                    if (otras.length > 0) {
                        diagramHTML += '<div><h5 style="color: #6c757d; border-bottom: 2px solid #6c757d; padding-bottom: 5px;">📋 OTRAS TABLAS</h5><div style="display: flex; flex-wrap: wrap; gap: 15px;">';
                        otras.forEach(table => {
                            diagramHTML += crearTarjetaTabla(table, '#6c757d');
                        });
                        diagramHTML += '</div></div>';
                    }
                    
                    diagramHTML += '</div>';
                    $('#relationshipDiagram').html(diagramHTML);
                    
                    // Mostrar lista de foreign keys con mejor diseño
                    let fkHTML = `
                        <div class="alert alert-info">
                            <strong>📖 Leyenda:</strong> 
                            <span class="badge bg-danger ms-2">PK</span> = Primary Key | 
                            <span class="badge bg-primary ms-2">FK</span> = Foreign Key
                        </div>
                    `;
                    fkHTML += '<div class="table-responsive"><table class="table table-hover table-bordered"><thead class="table-dark"><tr><th>Tabla Origen</th><th>Columna (FK)</th><th style="text-align: center; width: 100px;">Relación</th><th>Tabla Destino</th><th>Columna (PK)</th></tr></thead><tbody>';
                    
                    data.foreign_keys.forEach(fk => {
                        fkHTML += `
                            <tr>
                                <td><span class="badge bg-primary" style="font-size: 0.9em;">${fk.table}</span></td>
                                <td>
                                    <span class="badge bg-primary me-1">FK</span>
                                    <code style="color: #0d6efd; font-weight: bold;">${fk.from}</code>
                                </td>
                                <td style="text-align: center;">
                                    <span style="font-size: 1.8em; color: #28a745;">→</span>
                                </td>
                                <td><span class="badge bg-success" style="font-size: 0.9em;">${fk.to_table}</span></td>
                                <td>
                                    <span class="badge bg-danger me-1">PK</span>
                                    <code style="color: #dc3545; font-weight: bold;">${fk.to}</code>
                                </td>
                            </tr>
                        `;
                    });
                    
                    fkHTML += '</tbody></table></div>';
                    $('#foreignKeysList').html(fkHTML);
                });
        }
        
        $(document).ready(function() {
            cargarTablas();
            cargarRelaciones();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/tables')
def get_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = []
    for row in cursor.fetchall():
        table_name = row[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        tables.append({'name': table_name, 'count': count})
    conn.close()
    return jsonify(tables)

@app.route('/api/table/<table_name>')
def get_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    conn.close()
    return jsonify({'columns': columns, 'rows': rows})

@app.route('/api/update', methods=['POST'])
def update_cell():
    data = request.json
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = f"UPDATE {data['table']} SET {data['column']} = ? WHERE id = ?"
        cursor.execute(query, (data['value'], data['id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete', methods=['POST'])
def delete_row():
    data = request.json
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {data['table']} WHERE id = ?", (data['id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/execute', methods=['POST'])
def execute_sql():
    data = request.json
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(data['query'])
        if data['query'].strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            conn.close()
            return jsonify({'success': True, 'rows': rows})
        else:
            conn.commit()
            conn.close()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/relationships')
def get_relationships():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = []
    foreign_keys = []
    
    for row in cursor.fetchall():
        table_name = row[0]
        
        # Obtener columnas de la tabla
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for col in cursor.fetchall():
            columns.append({
                'name': col[1],
                'type': col[2],
                'pk': bool(col[5]),
                'fk': False
            })
        
        # Obtener foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        for fk in cursor.fetchall():
            foreign_keys.append({
                'table': table_name,
                'from': fk[3],
                'to_table': fk[2],
                'to': fk[4]
            })
            # Marcar columna como FK
            for col in columns:
                if col['name'] == fk[3]:
                    col['fk'] = True
        
        tables.append({
            'name': table_name,
            'columns': columns
        })
    
    conn.close()
    return jsonify({'tables': tables, 'foreign_keys': foreign_keys})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("VISOR DE BASE DE DATOS")
    print("="*60)
    print("\nAbriendo en el navegador...")
    print("URL: http://127.0.0.1:5001")
    print("\nPresiona CTRL+C para detener")
    print("="*60 + "\n")
    app.run(debug=False, port=5001, host='0.0.0.0')
