# Business Model Canvas

El lienzo de la decisión que apoya el modelo está en el [AI Canvas](06_ai_canvas.md).

Se puede cargar directamente en [Canvas Studio](https://juankidd.github.io/canvas/) con **Importar JSON** usando [lienzos/canvas.json](lienzos/canvas.json).

El orden de trabajo fue el que sugiere la herramienta: primero clientes y propuesta de valor, después canales, relación e ingresos, y al final la parte operativa.

## 07 · Segmentos de clientes
- Restaurantes pequeños de Cali (20 a 60 almuerzos diarios) que compran en Cavasa o en galerías.
- Tenderos de barrio que revenden fruta y verdura.
- Casinos y cocinas de empresas pequeñas.
- Más adelante: los mismos segmentos en otras ciudades con central mayorista en el SIPSA.

## 04 · Propuesta de valor
- "Te decimos qué insumos van a subir en Cavasa para que los compres antes."
- Traduce un Excel de miles de filas a 3 líneas por WhatsApp.
- Semáforo por producto: compra ya, espera o compra normal.
- Comparación del precio de Cavasa con el resto del país.
- Gratis en la versión básica y sin instalar nada.

## 06 · Canales
- Boletín semanal por WhatsApp (canal principal en la siguiente versión).
- Dashboard web para quien quiera ver el detalle.
- Asociaciones de restaurantes y grupos de compras de Cavasa.
- Proveedores de insumos que reparten el boletín a sus clientes.

## 05 · Relación con clientes
- Automática: el pipeline busca el boletín nuevo miércoles y sábado.
- Transparente: cada producto muestra cuántas veces acertó el modelo, y el dashboard avisa si la recomendación venció.
- Retroalimentación: el usuario responde en el dashboard si le sirvió o no, y eso se ve en el monitoreo.

## 09 · Fuentes de ingresos
- Freemium: boletín básico gratis y plan pago con más productos, alertas a mitad de semana y lista de compras sugerida.
- Suscripción para cadenas pequeñas con varios locales.
- Comisión por compras agrupadas con mayoristas de Cavasa (fase posterior).
- Espacios patrocinados de proveedores en el boletín.

## 01 · Socios clave
- DANE (SIPSA) como fuente pública de datos.
- Corporación de Abastecimientos del Valle (Cavasa) y comerciantes mayoristas.
- Asociaciones de restaurantes y la Cámara de Comercio de Cali.
- Proveedor del modelo de lenguaje (por API) para redactar los boletines.
- Proveedores de WhatsApp Business API.

## 02 · Actividades clave
- Descargar, limpiar y validar cada semana los boletines del SIPSA.
- Entrenar, evaluar y monitorear el modelo de predicción.
- Generar y revisar el boletín en lenguaje sencillo.
- Conseguir usuarios y medir si el boletín les ahorra plata.

## 03 · Recursos clave
- Pipeline de datos con arquitectura medallón y reglas de calidad.
- Histórico de precios semanales desde 2023.
- Modelo versionado y su sistema de monitoreo.
- Equipo con conocimiento en datos y en el negocio de restaurantes.

## 08 · Estructura de costos
- Infraestructura casi nula: SQLite, contenedores y GitHub Actions.
- Llamadas a la API del modelo de lenguaje: un boletín por semana y por segmento, con un costo de centavos de dólar.
- Mensajería de WhatsApp Business por mensaje enviado.
- Tiempo del equipo para mantenimiento y para conseguir usuarios.

## Viabilidad

| Dimensión | Evaluación |
|---|---|
| Técnica | Alta. Todo corre en un portátil o en un contenedor; el pipeline completo tarda menos de un minuto. |
| Datos | Alta en disponibilidad (fuente oficial, semanal y gratuita) y media en estabilidad, porque el DANE puede cambiar el formato del Excel o publicar con rezago. Las reglas de calidad detectan lo primero y el dashboard avisa lo segundo. |
| Negocio | Media. El ahorro simulado es de 1,0 % y en el límite de la meta; hay que validar con restaurantes reales si el valor percibido justifica pagar. |
