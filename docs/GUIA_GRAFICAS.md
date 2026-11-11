# Guía de la analítica: por qué cada gráfica y por qué en ese orden

> Todo lo que se ve en modo **simulador** son datos inventados. Esta guía explica el criterio de diseño, que es el mismo
> con datos reales.

## 1. Idea general: de lo global a lo específico, y de «qué pasó» a «qué hago»

La página **Estadísticas** responde preguntas en el orden en que una persona las haría al preparar un reporte:

| Paso | Pregunta | Qué lo responde |
|---|---|---|
| 1 | ¿Cómo estamos en general? | Tarjetas de indicadores (KPI) |
| 2 | ¿Qué debo atender ya? | Hallazgos clave y acciones sugeridas |
| 3 | ¿Cómo evoluciona el trabajo en el tiempo? | Trabajos por período |
| 4 | ¿En qué terminan los trabajos? | Distribución por estado |
| 5 | ¿Qué equipos se usan y cuáles fallan? | Utilización y éxito vs. fallo por impresora, y tabla de detalle |
| 6 | ¿Cuánto material gastamos y cuánto se pierde? | Consumo por período, material más usado |
| 7 | ¿Qué colores y por qué se falla? | Colores, causas de fallo |
| 8 | ¿Cuándo hay más demanda? | Mapa de calor día × hora |
| 9 | ¿Nos alcanzará el material? ¿Quién lo usa? | Autonomía del inventario, usuarios con más trabajos |
| 10 | ¿Cómo se calculó todo? | Nota de definiciones |

Regla de diseño: **primero los números que resumen, luego las alertas, después las gráficas que explican el porqué, y al final
las que sirven para planificar.** Así quien solo mire la parte de arriba ya tiene la conclusión, y quien necesite
justificarla encuentra la evidencia más abajo.

## 2. Filtros (arriba)
Rango de fechas (30 días, 90 días, 6 meses, 12 meses o personalizado), impresora, material y estado. Todo lo que está debajo
se recalcula con esos filtros. **Por qué primero:** un reporte siempre empieza con «de qué período y de qué equipos hablamos».
Si no hay datos con ese filtro, la página lo dice en lugar de mostrar gráficas vacías.

## 3. Tarjetas de indicadores (KPI)
Seis números con comparación contra el **período anterior de igual duración** (flecha verde = mejora, roja = empeora).

| Indicador | Qué mide | Por qué está |
|---|---|---|
| Trabajos | Total de trabajos del período | Volumen de actividad: base de todo lo demás |
| Tasa de éxito | Completadas ÷ (completadas + fallidas) | Calidad del proceso. Verde ≥ 90 %, amarillo ≥ 75 %, rojo menos |
| Filamento usado | Gramos consumidos | Costo y reposición |
| Desperdicio | Gramos en trabajos fallidos o cancelados, y su % | Dinero perdido que se puede reducir |
| Horas de impresión | Tiempo real de máquina | Carga de trabajo de la sala |
| Duración promedio | Duración típica de un trabajo completado | Sirve para estimar colas y reservas |

La comparación con el período anterior solo se muestra si ese período tiene al menos 10 trabajos; con menos datos sería
engañosa (por ejemplo «+2000 %»).

## 4. Hallazgos clave y acciones sugeridas
Texto generado automáticamente a partir de reglas sobre los datos. **Es lo más útil para un reporte**, porque convierte las gráficas
en conclusiones. Ordenados por gravedad (rojo, amarillo, azul, verde). Reglas actuales:

- **Tasa de éxito** y su variación; gramos perdidos.
- **Impresora con fallos anómalos:** ≥ 8 trabajos y fallos al menos 1,6 veces el promedio (y ≥ 15 %).
- **Saturación o subuso:** una impresora ≥ 70 % de utilización, o una operativa con < 10 % mientras otras trabajan mucho.
- **Dependencia de un material** (≥ 55 % del consumo) y **material que falla más** que el resto.
- **Causa principal de fallos.**
- **Inventario:** autonomía ≤ 14 días y bobinas bajas o agotadas.
- **Pico de demanda** por día y bloque de 2 horas.
- **Tendencia de consumo** (± 25 % entre períodos) y **volumen** frente al período previo.
- **Mantenimiento** vencido o próximo.

Cada hallazgo incluye una **acción sugerida**. Son orientaciones, no verdades: la decisión es de quien administra la sala.

## 5. Las gráficas, una por una

### 5.1 Trabajos completados, fallidos y pendientes (barras apiladas + línea)
- **Pregunta:** ¿cómo evoluciona el trabajo y la calidad en el tiempo?
- **Por qué barras apiladas:** muestran a la vez el total y su composición (completados, fallidos, cancelados, pendientes).
- **Por qué una línea con eje derecho:** la tasa de éxito es un porcentaje y las barras son conteos; no se pueden mezclar en un
  mismo eje. La línea punteada verde marca la meta de 90 %.
- **Agrupación automática:** por día (≤ 31 días), semana (≤ 120 días) o mes (más).
- **Cómo leerla:** barras que crecen = más demanda; tramos rojos que crecen o línea bajo la meta = problema de calidad.
- **Va primero** porque es la imagen que resume el período completo (cubre los puntos «trabajos por mes» y «completados/pendientes/fallidos»).

### 5.2 Distribución por estado (anillo)
- **Pregunta:** ¿qué proporción de los trabajos termina bien, mal o sigue abierta?
- **Por qué anillo:** son pocas categorías que suman 100 %; el total va en el centro.
- Complementa a la anterior: aquella muestra *cuándo*, esta *cuánto en total* (cubre «impresiones exitosas frente a fallidas»).

### 5.3 Utilización por impresora (barras horizontales)
- **Pregunta:** ¿qué equipos están sobrecargados y cuáles casi no se usan?
- **Cálculo:** horas de impresión ÷ (días del período × horas operativas por día). Las horas operativas se ajustan en Configuración.
- **Por qué horizontales:** los nombres de impresora son largos y se comparan mejor en barras ordenadas.
- **Línea amarilla al 70 %:** nivel de saturación. Por encima, las reservas y la cola empiezan a sufrir. Las barras que la superan se pintan amarillas.
- **Decisión que apoya:** redistribuir trabajos, comprar otra impresora o promover las poco usadas (cubre «utilización de cada impresora» e «impresoras con mayor utilización»).

### 5.4 Éxito vs. fallo por impresora (barras 100 % apiladas)
- **Pregunta:** ¿qué equipo falla más, sin importar cuánto se use?
- **Por qué 100 % apilada:** una impresora con pocos trabajos y otra con muchos se comparan en proporción, no en cantidad.
- **Orden:** de peor a mejor tasa de éxito: la primera barra es la que requiere atención.
- Se coloca **justo después** de la utilización porque juntas separan dos problemas distintos: «está muy usada» y «falla mucho».
  La tabla **Detalle por impresora** da los números exactos (trabajos, horas, utilización, éxito, gramos, duración).

### 5.5 Consumo de filamento por período (barras apiladas por material + línea)
- **Pregunta:** ¿cuánto material se gasta, de qué tipo, y cuánto se pierde?
- **Por qué apiladas por material:** el total indica el gasto y los colores indican de qué material.
- **Línea roja punteada:** gramos desperdiciados (trabajos fallidos o cancelados) en cada período.
- **Decisión que apoya:** presupuesto y compras (cubre «consumo mensual» y «consumo de materiales por período»).

### 5.6 Material más utilizado (barras de proporción)
- **Pregunta:** ¿de qué material depende la sala, y cuál falla más?
- Cada barra muestra los gramos y el porcentaje del total; debajo, el número de trabajos y la **tasa de éxito** de ese material.
- **Por qué no un gráfico de pastel:** aquí interesa comparar proporciones *y* leer un segundo dato (éxito) por categoría.

### 5.7 Colores más utilizados (barras horizontales con el color real)
- **Pregunta:** ¿qué colores conviene tener siempre en stock?
- Top 10 por gramos; cada barra usa el color real del filamento, para reconocerlo de inmediato.

### 5.8 Por qué fallan las impresiones (barras horizontales)
- **Pregunta:** ¿qué causa los fallos?
- Usa la causa registrada al marcar un trabajo como fallido (mala adhesión, boquilla obstruida, filamento, deformación, corte de energía, error de diseño u otro).
- **Va después de material y color** porque son las primeras variables sospechosas de un fallo; aquí se ve la causa concreta.
- **Decisión que apoya:** capacitación de usuarios, mantenimiento o cambio de perfiles de impresión. Solo es útil si el operador **registra la causa**.

### 5.9 Demanda por día y hora (mapa de calor)
- **Pregunta:** ¿cuándo se solicita más la sala?
- Filas = día de la semana, columnas = hora local; el color más intenso indica más trabajos iniciados.
- **Por qué mapa de calor:** hay dos dimensiones (día y hora) y un valor; es la forma más rápida de ver patrones.
- **Decisión que apoya:** horarios del personal, y en qué franjas ofrecer reservas.

### 5.10 Autonomía del inventario (tabla)
- **Pregunta:** ¿cuántos días nos dura el material al ritmo actual?
- Existencias ÷ consumo diario de los últimos 60 días. Rojo ≤ 7 días, amarillo ≤ 14, verde más.
- **Por qué es una tabla:** son pocas filas y un número que se lee mejor que un gráfico. Va casi al final porque **mira hacia el futuro**: pasa del análisis a la planificación.

### 5.11 Usuarios con más trabajos (tabla)
- **Pregunta:** ¿quiénes concentran la demanda?
- Útil para políticas de uso justo. Es información personal: úsala con criterio en los reportes.

## 6. Panel principal (Dashboard) y su orden
Es la versión corta de lo anterior, pensada para abrir la sala por la mañana:
1. **Tarjetas operativas** (impresoras totales, disponibles, ocupadas, fuera de servicio; trabajos completados y pendientes; % completado; alertas de mantenimiento; inventario bajo; reservas por aprobar): «¿qué está pasando ahora?». Las que son accionables llevan al módulo correspondiente al pulsarlas.
2. **Actividad reciente** (últimos 30 días): contexto inmediato.
3. **Imprimiendo ahora**: progreso en vivo.
4. **Hallazgos y Alertas**: lo que requiere atención.

## 7. Orden del menú lateral (administrador)
Dashboard → Equipos → Inventario → Trabajos → Reservas → Mantenimiento → Estadísticas → Usuarios → Configuración.
Sigue el flujo del día a día: primero ver el estado, luego gestionar recursos (equipos, material), luego la operación (trabajos,
reservas), después el cuidado (mantenimiento), el análisis (estadísticas) y por último la administración del sistema.

## 8. Cómo usar esto para un reporte
1. Elige el período (por ejemplo, el semestre) en los filtros.
2. Pulsa **Imprimir / PDF**: el reporte incluye título, período, filtros, tarjetas, hallazgos, gráficas y definiciones.
3. Para análisis propio, pulsa **CSV** (abre en Excel; incluye cada trabajo con impresora, material, color, estado, gramos, duración y causa del fallo).
4. Si el sistema está en modo simulador, el reporte lo advierte: **no lo presentes como datos reales**.

## 9. Limitaciones a tener en cuenta
- Los hallazgos son reglas automáticas con umbrales fijos; sirven de guía, no sustituyen el criterio humano.
- La utilización depende de las «horas operativas por día» configuradas.
- La causa de los fallos y el filamento realmente usado dependen de que se registren bien.
- Con pocos datos (menos de ~10 trabajos) los porcentajes son poco confiables.
