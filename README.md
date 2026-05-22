# Proyecto Final Procesamiento Distribuido de Datos

Análisis y Modelado Analítico de Transacciones de Supermercado

## Información del Estudiante

**Nombre:** Daniel José Plazas Cortés

**Código:** A00400085

## Dudas del proyecto

### Carga de datos
Cada archivo es una sucursal. Ante un nuevo archivo (nueva sucursal), el sistema genera resultados nuevos de manera general, realizando todo el análisis. **El usuario final no realiza la carga de datos**. Este análisis de los nuevos datos se realizan desde el back, y al estar disponibles, podrán ser visibles desde el front.


### Estructura documento transacciones
`fecha, compra, sucursal, numero de clientes, productos comprados`

> Mesaje del profe: 3. La estructura de las transacciones: `fecha | sucursal | id_cliente | listado de productos comprados en ese momento`