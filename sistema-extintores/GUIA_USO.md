# 📘 Guía de Uso: Modelos, Colores y Características

## 🎯 Introducción

Esta guía explica cómo usar las nuevas funcionalidades del sistema de inventario para gestionar productos con modelos, colores y características personalizadas.

---

## 📦 ¿Qué son los Modelos?

Los **modelos** son variantes de un mismo producto. Por ejemplo:

- **Producto:** Smartphone iPhone
  - **Modelos:** iPhone 13, iPhone 14, iPhone 15
  
- **Producto:** Taladro Eléctrico
  - **Modelos:** 500W, 750W, 1000W

- **Producto:** Casco de Seguridad
  - **Modelos:** Talla S, Talla M, Talla L

---

## 🎨 ¿Qué son los Colores?

Los **colores** son variantes de color dentro de cada modelo. Por ejemplo:

- **Producto:** Smartphone iPhone
  - **Modelo:** iPhone 15
    - **Colores:** Negro, Blanco, Azul, Rosa

Cada color puede tener su propio stock independiente.

---

## 🏷️ ¿Qué son las Características?

Las **características** son propiedades adicionales del producto. Por ejemplo:

- **Material:** Acero inoxidable
- **Voltaje:** 220V
- **Peso:** 2.5 kg
- **Dimensiones:** 30x20x10 cm
- **Marca:** Bosch
- **País de origen:** Alemania

---

## 📝 Cómo Crear un Producto con Modelos

### Paso 1: Crear el Producto Base

1. Ve a **Productos** → **Nuevo Producto**
2. Completa la información básica:
   - Categoría
   - Ubicación
   - Nombre del producto
   - Descripción
   - Unidad de medida
   - Stock mínimo
   - Precio unitario (precio base)

### Paso 2: Activar Modelos y/o Colores

En la sección **"Configuración de Variantes"**:

- ✅ Activa **"Este producto tiene modelos"** si el producto tendrá diferentes versiones
- ✅ Activa **"Este producto tiene colores"** si cada modelo vendrá en diferentes colores

### Paso 3: Agregar Características (Opcional)

En la sección **"Características Adicionales"**:

1. Haz clic en **"Agregar"**
2. Ingresa el nombre de la característica (ej: "Material")
3. Ingresa el valor (ej: "Acero")
4. Repite para todas las características que necesites

### Paso 4: Guardar el Producto

- Si NO activaste "tiene modelos", puedes ingresar el stock inicial
- Si SÍ activaste "tiene modelos", el stock se gestionará por cada modelo

---

## 🔧 Cómo Agregar Modelos a un Producto

### Paso 1: Ir al Detalle del Producto

1. Ve a **Productos**
2. Haz clic en el ícono de **"Ver"** (ojo) del producto

### Paso 2: Agregar Modelo

1. En la sección **"Modelos del Producto"**, haz clic en **"Agregar Modelo"**
2. Completa la información:
   - **Nombre del modelo:** Ej: "iPhone 15 Pro Max"
   - **Código del modelo:** (Opcional) Código específico
   - **Descripción:** Detalles del modelo
   - **Stock inicial:** Cantidad inicial de este modelo
   - **Precio diferencial:** 
     - Positivo (+50.00) si es más caro que el precio base
     - Negativo (-20.00) si es más barato
     - Cero (0) si tiene el mismo precio

### Paso 3: Agregar Colores (Si aplica)

Si el producto tiene colores activados:

1. En la sección **"Colores Disponibles"**, haz clic en **"Agregar Color"**
2. Ingresa:
   - **Nombre del color:** Ej: "Negro"
   - **Código del color:** (Opcional) Código hexadecimal como #000000
   - **Stock:** Cantidad inicial de este color
3. Repite para todos los colores disponibles

### Paso 4: Guardar el Modelo

El modelo quedará registrado con todos sus colores.

---

## 📊 Ejemplos Prácticos

### Ejemplo 1: Smartphone con Modelos y Colores

**Producto Base:**
- Nombre: Smartphone iPhone
- Precio base: S/ 3,000.00
- Tiene modelos: ✅ Sí
- Tiene colores: ✅ Sí

**Modelos:**

1. **iPhone 13**
   - Precio diferencial: -500.00 (Precio final: S/ 2,500.00)
   - Colores:
     - Negro: 5 unidades
     - Blanco: 3 unidades
     - Azul: 2 unidades

2. **iPhone 14**
   - Precio diferencial: 0.00 (Precio final: S/ 3,000.00)
   - Colores:
     - Negro: 8 unidades
     - Blanco: 6 unidades
     - Rosa: 4 unidades

3. **iPhone 15**
   - Precio diferencial: +500.00 (Precio final: S/ 3,500.00)
   - Colores:
     - Negro: 10 unidades
     - Blanco: 8 unidades
     - Azul: 6 unidades

---

### Ejemplo 2: Herramienta con Modelos (Sin Colores)

**Producto Base:**
- Nombre: Taladro Eléctrico Bosch
- Precio base: S/ 250.00
- Tiene modelos: ✅ Sí
- Tiene colores: ❌ No
- Características:
  - Marca: Bosch
  - Voltaje: 220V
  - Material: Plástico reforzado

**Modelos:**

1. **500W**
   - Precio diferencial: -50.00 (Precio final: S/ 200.00)
   - Stock: 15 unidades

2. **750W**
   - Precio diferencial: 0.00 (Precio final: S/ 250.00)
   - Stock: 20 unidades

3. **1000W**
   - Precio diferencial: +100.00 (Precio final: S/ 350.00)
   - Stock: 10 unidades

---

### Ejemplo 3: Producto Simple (Sin Modelos ni Colores)

**Producto Base:**
- Nombre: Cinta Adhesiva Industrial
- Precio base: S/ 15.00
- Tiene modelos: ❌ No
- Tiene colores: ❌ No
- Stock: 100 unidades
- Características:
  - Ancho: 48mm
  - Largo: 100m
  - Material: Polipropileno

Este producto se gestiona de forma tradicional, sin modelos ni colores.

---

## ✏️ Cómo Editar Modelos y Características

### Editar un Modelo

1. Ve al detalle del producto
2. En la tabla de modelos, haz clic en el ícono de **"Editar"** (lápiz)
3. Modifica la información necesaria
4. Si tiene colores, puedes agregar, editar o eliminar colores
5. Guarda los cambios

### Editar Características del Producto

1. Ve a **Productos** → **Editar** (del producto)
2. En la sección **"Características Adicionales"**:
   - Modifica las características existentes
   - Agrega nuevas con el botón **"Agregar"**
   - Elimina características con el ícono de basura
3. Guarda los cambios

---

## 🔄 Agregar Modelos a un Producto Existente

Si ya tienes un producto creado y quieres agregarle modelos:

1. Ve a **Productos** → **Editar** (del producto)
2. Activa la opción **"Este producto tiene modelos"**
3. Activa **"Este producto tiene colores"** si aplica
4. Guarda los cambios
5. Ve al detalle del producto
6. Ahora podrás agregar modelos con el botón **"Agregar Modelo"**

---

## 💡 Consejos y Buenas Prácticas

### ✅ Cuándo usar Modelos

- Cuando el producto tiene diferentes versiones o tamaños
- Cuando cada versión puede tener un precio diferente
- Cuando necesitas controlar el stock por separado de cada versión

### ✅ Cuándo usar Colores

- Cuando cada modelo viene en diferentes colores
- Cuando necesitas saber cuántas unidades hay de cada color
- Productos como ropa, calzado, electrónicos, etc.

### ✅ Cuándo usar Características

- Para especificaciones técnicas
- Para información adicional del producto
- Para facilitar búsquedas y filtros futuros

### ❌ Cuándo NO usar Modelos

- Si el producto es simple y no tiene variantes
- Si todas las unidades son idénticas
- Si no necesitas diferenciar precios o stock

---

## 🆘 Preguntas Frecuentes

### ¿Puedo cambiar un producto de "sin modelos" a "con modelos"?

**Sí**, puedes editar el producto y activar la opción "tiene modelos". El stock actual del producto se mantendrá en el producto base.

### ¿Puedo tener modelos sin colores?

**Sí**, puedes activar solo "tiene modelos" sin activar "tiene colores".

### ¿Puedo tener colores sin modelos?

**No**, los colores están asociados a modelos. Si quieres gestionar colores, primero debes activar "tiene modelos".

### ¿El precio diferencial puede ser negativo?

**Sí**, usa valores negativos para modelos más baratos que el precio base.

### ¿Puedo eliminar un modelo?

**Sí**, desde el detalle del producto, haz clic en el ícono de eliminar. El modelo se marcará como inactivo pero se mantendrá en el historial.

### ¿Las características afectan el stock o precio?

**No**, las características son solo información descriptiva del producto.

---

## 📞 Soporte

Si tienes dudas o problemas con el sistema, contacta al administrador del sistema.

---

**AB Ingeniería S.A.C. - 2024**
