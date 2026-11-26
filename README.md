# Estación Meteorológica Automática — Esc. 4752 Aráoz Costas
**Campo Quijano, Salta - Argentina**  
**ID Weather Underground:** `ICAMPO519`

Sistema web autónomo de visualización agrometeorológica desarrollado para el **INTA EEA Salta** y la comunidad educativa de Campo Quijano.

---

## 🌟 Estructura del Sitio Web
El repositorio contiene 3 vistas principales inspiradas en la plantilla de *El Brete*:
1. **`index.html`**: Dashboard principal interactivo de escritorio y tablet con tarjetas en tiempo real, brújula de viento, evolución térmica, gráficas dinámicas de 24 hs (Chart.js) y tablas horarias.
2. **`tiempohoy.html`**: Aplicación web móvil optimizada (PWA) de carga ultra-rápida, instalable en la pantalla de inicio del teléfono celular.
3. **`resumen.html`**: Balance climatológico mensual y anual con hietograma de lluvias por día, curvas térmicas y registro histórico tabular.
4. **`historico_diario.xlsx`**: Archivo Excel con estilos institucionales y datos acumulados de cada día para descarga directa.

---

## ⚙️ Automatización (GitHub Actions)
El flujo `.github/workflows/actualizar.yml` se ejecuta automáticamente **cada 30 minutos**:
1. Consulta los servidores de Weather Underground mediante `actualizar_datos.py`.
2. Obtiene las mediciones en tiempo real, la serie detallada del día y el histórico.
3. Genera y actualiza los archivos `datos_actuales.json`, `hoy_5min.json` y `historico_diario.csv`.
4. Realiza un auto-commit para que **GitHub Pages** actualice el sitio de forma inmediata.

---

## 🚀 Cómo publicar este repositorio en GitHub

1. **Crear el repositorio en GitHub:**
   Crea un nuevo repositorio público llamado:
   ```text
   ema_esc4752
   ```

2. **Subir los archivos:**
   Desde la carpeta `ema_esc4752`:
   ```bash
   git init
   git add .
   git commit -m "Versión inicial Estación Esc 4752 Campo Quijano"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/ema_esc4752.git
   git push -u origin main
   ```

3. **Activar GitHub Pages:**
   * En GitHub ve a **Settings** > **Pages**.
   * En **Source**, selecciona `Deploy from a branch`.
   * En **Branch**, selecciona `main` y `/ (root)`. Guarda los cambios.
   * En pocos minutos tu sitio estará disponible en:
     `https://TU_USUARIO.github.io/ema_esc4752/`

4. **Permisos de GitHub Actions:**
   * Ve a **Settings** > **Actions** > **General** > **Workflow permissions**.
   * Asegúrate de marcar **"Read and write permissions"** para que el bot pueda guardar los datos actualizados cada 30 minutos.

---

## 🔄 Cómo crear otra estación para un nuevo colaborador
Para clonar este sistema para otra estación de Weather Underground:
1. Copia toda esta carpeta con otro nombre (ej. `ema_otraestacion`).
2. Abre `actualizar_datos.py` y cambia las primeras líneas:
   ```python
   STATION_ID = "ID_DE_WUNDERGROUND"
   STATION_NAME = "Nombre de la nueva estación"
   STATION_LOCATION = "Localidad, Provincia"
   STATION_LAT = -XX.XXXXXX
   STATION_LON = -YY.YYYYYY
   ```
3. En `index.html`, `tiempohoy.html` y `resumen.html`, actualiza los textos del título o encabezado si deseas.
4. Súbelo a su propio repositorio y ¡listo!
