"""
Script para poblar el catálogo de extintores con datos iniciales
Adaptado para el mercado peruano
"""
from app import app, db, TipoExtintor, CapacidadExtintor, MarcaExtintor

def poblar_catalogo():
    with app.app_context():
        print("Poblando catálogo de extintores...")
        
        # ============================================
        # TIPOS DE EXTINTORES
        # ============================================
        tipos = [
            {
                'nombre': 'PQS',
                'nombre_completo': 'Polvo Químico Seco',
                'clase_fuego': 'ABC',
                'descripcion': 'Multipropósito para fuegos de clase A, B y C'
            },
            {
                'nombre': 'CO2',
                'nombre_completo': 'Dióxido de Carbono',
                'clase_fuego': 'BC',
                'descripcion': 'Ideal para equipos eléctricos y fuegos clase B y C'
            },
            {
                'nombre': 'H2O Pres.',
                'nombre_completo': 'Agua Presurizada',
                'clase_fuego': 'A',
                'descripcion': 'Para materiales sólidos combustibles'
            },
            {
                'nombre': 'H2O Desm.',
                'nombre_completo': 'Agua Desmineralizada',
                'clase_fuego': 'A',
                'descripcion': 'Para materiales sólidos combustibles y equipos eléctricos desenergizados'
            },
            {
                'nombre': 'AFFF',
                'nombre_completo': 'Espuma Formadora de Película Acuosa',
                'clase_fuego': 'AB',
                'descripcion': 'Para líquidos inflamables y materiales sólidos'
            },
            {
                'nombre': 'Acetato K',
                'nombre_completo': 'Acetato de Potasio',
                'clase_fuego': 'K',
                'descripcion': 'Especial para cocinas comerciales'
            },
            {
                'nombre': 'Halotron',
                'nombre_completo': 'Halotron I',
                'clase_fuego': 'ABC',
                'descripcion': 'Agente limpio para equipos electrónicos sensibles'
            }
        ]
        
        print("\n[TIPOS] Agregando tipos de extintores...")
        for tipo_data in tipos:
            tipo = TipoExtintor.query.filter_by(nombre=tipo_data['nombre']).first()
            if not tipo:
                tipo = TipoExtintor(**tipo_data)
                db.session.add(tipo)
                print(f"  + {tipo_data['nombre']}")
        
        db.session.commit()
        
        # ============================================
        # CAPACIDADES
        # ============================================
        capacidades = [
            # Kilogramos (más común en Perú)
            {'capacidad': '01', 'unidad': 'Kg.'},
            {'capacidad': '02', 'unidad': 'Kg.'},
            {'capacidad': '04', 'unidad': 'Kg.'},
            {'capacidad': '06', 'unidad': 'Kg.'},
            {'capacidad': '09', 'unidad': 'Kg.'},
            {'capacidad': '12', 'unidad': 'Kg.'},
            {'capacidad': '25', 'unidad': 'Kg.'},
            {'capacidad': '50', 'unidad': 'Kg.'},
            {'capacidad': '100', 'unidad': 'Kg.'},
            {'capacidad': '150', 'unidad': 'Kg.'},
            
            # Libras (algunas marcas americanas)
            {'capacidad': '2.5', 'unidad': 'Lbs.'},
            {'capacidad': '05', 'unidad': 'Lbs.'},
            {'capacidad': '10', 'unidad': 'Lbs.'},
            {'capacidad': '20', 'unidad': 'Lbs.'},
            
            # Litros (para agua y espuma)
            {'capacidad': '06', 'unidad': 'Lts.'},
            {'capacidad': '09', 'unidad': 'Lts.'},
            {'capacidad': '10', 'unidad': 'Lts.'},
            {'capacidad': '50', 'unidad': 'Lts.'},
            {'capacidad': '100', 'unidad': 'Lts.'},
            
            # Galones (para agua y espuma)
            {'capacidad': '2.5', 'unidad': 'Glns.'},
            {'capacidad': '05', 'unidad': 'Glns.'},
            {'capacidad': '10', 'unidad': 'Glns.'},
            {'capacidad': '20', 'unidad': 'Glns.'},
            {'capacidad': '33', 'unidad': 'Glns.'}
        ]
        
        print("\n[CAPACIDADES] Agregando capacidades...")
        for cap_data in capacidades:
            capacidad_completa = f"{cap_data['capacidad']} {cap_data['unidad']}"
            # Buscar por capacidad completa (valor + unidad)
            cap = CapacidadExtintor.query.filter_by(capacidad=capacidad_completa).first()
            if not cap:
                cap = CapacidadExtintor(
                    capacidad=capacidad_completa,
                    unidad=cap_data['unidad']
                )
                db.session.add(cap)
                print(f"  + {capacidad_completa}")
        
        db.session.commit()
        
        # ============================================
        # MARCAS
        # ============================================
        marcas = [
            # Marcas Nacionales (Perú)
            {'nombre': 'Solfire', 'origen': 'Nacional'},
            {'nombre': 'Prosein', 'origen': 'Nacional'},
            {'nombre': 'Induseg', 'origen': 'Nacional'},
            {'nombre': 'Firex Perú', 'origen': 'Nacional'},
            {'nombre': 'Segurfire', 'origen': 'Nacional'},
            
            # Marcas Americanas
            {'nombre': 'Amerex', 'origen': 'Americano'},
            {'nombre': 'Ansul', 'origen': 'Americano'},
            {'nombre': 'Badger', 'origen': 'Americano'},
            {'nombre': 'Kidde', 'origen': 'Americano'},
            {'nombre': 'Buckeye', 'origen': 'Americano'},
            {'nombre': 'Pyro-Chem', 'origen': 'Americano'},
            {'nombre': 'Strike First', 'origen': 'Americano'},
            
            # Marcas Chinas
            {'nombre': 'Tianyi', 'origen': 'Chino'},
            {'nombre': 'Ningbo Yunfeng', 'origen': 'Chino'},
            {'nombre': 'Gunnebo', 'origen': 'Chino'},
            {'nombre': 'Anquan', 'origen': 'Chino'},
            {'nombre': 'Firex (China)', 'origen': 'Chino'},
            {'nombre': 'Longcheng', 'origen': 'Chino'},
            
            # Marcas Europeas
            {'nombre': 'Gloria', 'origen': 'Europeo'},
            {'nombre': 'Minimax', 'origen': 'Europeo'},
            {'nombre': 'Jactone', 'origen': 'Europeo'},
            {'nombre': 'Desautel', 'origen': 'Europeo'},
            
            # Otras marcas latinoamericanas
            {'nombre': 'Matafuegos Drago (Chile)', 'origen': 'Otro'},
            {'nombre': 'Extinfire (Colombia)', 'origen': 'Otro'},
            {'nombre': 'Sentry (México)', 'origen': 'Otro'}
        ]
        
        print("\n[MARCAS] Agregando marcas...")
        for marca_data in marcas:
            marca = MarcaExtintor.query.filter_by(nombre=marca_data['nombre']).first()
            if not marca:
                marca = MarcaExtintor(**marca_data)
                db.session.add(marca)
                print(f"  + {marca_data['nombre']} ({marca_data['origen']})")
        
        db.session.commit()
        
        # Resumen
        print("\n" + "="*60)
        print("CATALOGO POBLADO EXITOSAMENTE")
        print("="*60)
        print(f"Tipos de extintores: {TipoExtintor.query.count()}")
        print(f"Capacidades: {CapacidadExtintor.query.count()}")
        print(f"Marcas: {MarcaExtintor.query.count()}")
        print("="*60)

if __name__ == '__main__':
    poblar_catalogo()
