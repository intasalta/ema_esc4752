#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_datos.py
Extractor automatizado de datos meteorológicos desde Weather Underground
para la Estación: Esc 4752 Araoz Costas - Campo Quijano Salta (ID: ICAMPO519)
Diseñado para ejecutarse periódicamente en GitHub Actions sin dependencias externas.
"""

import urllib.request
import json
import datetime
import re
import os
import sys
import csv

# --- CONFIGURACIÓN DE LA ESTACIÓN ---
STATION_ID = "ICAMPO519"
STATION_NAME = "Esc. 4752 Aráoz Costas"
STATION_LOCATION = "Campo Quijano, Salta - Argentina"
STATION_LAT = -24.911553
STATION_LON = -65.632192
STATION_ALTITUDE = 1520.0  # Altitud oficial en metros sobre el nivel del mar (msnm)
STATION_HARDWARE = "DAZA Wireless Weather Station"
DEFAULT_API_KEY = "f6d2efe5720d47ea92efe5720df7eaa8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def calcular_presion_absoluta(p_rel, temp_c, altitud=STATION_ALTITUDE):
    """
    Calcula la Presión Absoluta (Pabs) a partir de la Presión Relativa (Prel),
    la altitud (h en msnm) y la temperatura (°C) según la fórmula barométrica:
    Pabs = Prel * (1 - (0.0065 * h) / (T + 0.0065 * h + 273.15)) ^ 5.257
    """
    if p_rel is None:
        return None
    try:
        t = float(temp_c) if temp_c is not None else 15.0
        h = float(altitud)
        term = (0.0065 * h) / (t + 0.0065 * h + 273.15)
        factor = (1.0 - term) ** 5.257
        return round(float(p_rel) * factor, 1)
    except Exception as e:
        print(f"[!] Error al calcular presión absoluta: {e}")
        return round(float(p_rel), 1)

def obtener_api_key_dinamica(station_id=STATION_ID):
    """Extrae dinámicamente el API Key público vigente desde el frontend de Wunderground."""
    url = f"https://www.wunderground.com/dashboard/pws/{station_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode("utf-8", "ignore")
            # Buscar patrones de apiKey
            found = re.findall(r'"API_KEY"\s*:\s*"([a-f0-9]{32})"', html, re.I)
            if not found:
                found = re.findall(r'apiKey=([a-f0-9]{32})', html, re.I)
            if found:
                print(f"[*] API Key obtenida dinámicamente: {found[0]}")
                return found[0]
    except Exception as e:
        print(f"[!] Advertencia al extraer clave dinámica: {e}. Usando clave por defecto.")
    return DEFAULT_API_KEY


def consultar_endpoint(url):
    """Consulta una URL y retorna el objeto JSON decodificado, manejando 204 No Content."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 204:
                return None
            cuerpo = resp.read().decode("utf-8")
            if not cuerpo or not cuerpo.strip():
                return None
            return json.loads(cuerpo)
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return None
        raise e


def procesar_datos():
    print(f"=== Iniciando actualización para estación {STATION_NAME} ({STATION_ID}) ===")
    ahora = datetime.datetime.now()
    fecha_hoy_str = ahora.strftime("%Y%m%d") # Formato YYYYMMDD
    
    api_key = obtener_api_key_dinamica(STATION_ID)
    
    # 1. Obtener observación actual
    url_actual = (
        f"https://api.weather.com/v2/pws/observations/current"
        f"?stationId={STATION_ID}&format=json&units=m&numericPrecision=decimal&apiKey={api_key}"
    )
    
    # 2. Obtener datos detallados de hoy (intervalos de 5-10 min)
    url_hoy = (
        f"https://api.weather.com/v2/pws/observations/all/1day"
        f"?stationId={STATION_ID}&format=json&units=m&numericPrecision=decimal&apiKey={api_key}"
    )
    
    # 3. Obtener resumen de las últimas 7 días (horario)
    url_7dias = (
        f"https://api.weather.com/v2/pws/observations/hourly/7day"
        f"?stationId={STATION_ID}&format=json&units=m&numericPrecision=decimal&apiKey={api_key}"
    )
    
    # 4. Obtener resumen del día
    url_resumen_dia = (
        f"https://api.weather.com/v2/pws/history/daily"
        f"?stationId={STATION_ID}&format=json&units=m&numericPrecision=decimal&date={fecha_hoy_str}&apiKey={api_key}"
    )

    data_actual = None
    data_hoy = None
    data_7dias = None
    data_resumen_dia = None

    try:
        print("[*] Descargando datos actuales...")
        data_actual = consultar_endpoint(url_actual)
    except Exception as e:
        print(f"[!] Error al descargar datos actuales: {e}")

    try:
        print("[*] Descargando serie detallada de hoy (1 día)...")
        data_hoy = consultar_endpoint(url_hoy)
    except Exception as e:
        print(f"[!] Error al descargar serie de hoy: {e}")

    try:
        print("[*] Descargando serie horaria de 7 días...")
        data_7dias = consultar_endpoint(url_7dias)
    except Exception as e:
        print(f"[!] Error al descargar serie 7 días: {e}")

    try:
        print("[*] Descargando resumen estadístico de hoy...")
        data_resumen_dia = consultar_endpoint(url_resumen_dia)
    except Exception as e:
        print(f"[!] Error al descargar resumen del día: {e}")

    # Fallback inteligente: Si /current devolvió 204 No Content, tomar el último registro de /1day
    obs_actual = None
    if data_actual and "observations" in data_actual and data_actual["observations"]:
        obs_actual = data_actual["observations"][0]
        metric_act = obs_actual.get("metric", {})
    elif data_hoy and "observations" in data_hoy and data_hoy["observations"]:
        print("[*] Usando la última observación registrada en la serie de hoy como valor actual...")
        obs_hist = data_hoy["observations"][-1]
        m_hist = obs_hist.get("metric", {})
        temp_val = m_hist.get("tempAvg") if m_hist.get("tempAvg") is not None else (m_hist.get("tempHigh") or m_hist.get("tempLow"))
        
        metric_act = {
            "temp": temp_val,
            "heatIndex": m_hist.get("heatindexAvg") or temp_val,
            "dewpt": m_hist.get("dewptAvg"),
            "windChill": m_hist.get("windchillAvg") or temp_val,
            "windSpeed": m_hist.get("windspeedAvg") or 0.0,
            "windGust": m_hist.get("windgustHigh") or 0.0,
            "pressure": m_hist.get("pressureMin") or m_hist.get("pressureMax") or 1013.0,
            "precipRate": m_hist.get("precipRate", 0.0),
            "precipTotal": m_hist.get("precipTotal", 0.0),
            "elev": 453.5
        }
        obs_actual = {
            "stationID": STATION_ID,
            "obsTimeUtc": obs_hist.get("obsTimeUtc"),
            "obsTimeLocal": obs_hist.get("obsTimeLocal"),
            "epoch": obs_hist.get("epoch"),
            "neighborhood": "Campo Quijano",
            "softwareType": "EasyWeather V9.3.0",
            "country": "AR",
            "lat": obs_hist.get("lat", STATION_LAT),
            "lon": obs_hist.get("lon", STATION_LON),
            "winddir": obs_hist.get("winddirAvg", 0),
            "humidity": obs_hist.get("humidityAvg") or obs_hist.get("humidityHigh"),
            "solarRadiation": obs_hist.get("solarRadiationHigh"),
            "uv": obs_hist.get("uvHigh"),
            "qcStatus": obs_hist.get("qcStatus", 1),
            "metric": metric_act
        }

    if not obs_actual:
        print("[X] No se pudo obtener la observación actual ni el fallback. Abortando guardado.")
        return False

    # Calcular estadísticas del día a partir de la serie de hoy si el resumen diario no está completo
    temps_hoy = []
    hum_hoy = []
    pres_rel_hoy = []
    pres_abs_hoy = []
    viento_max = 0.0
    rafaga_max = 0.0
    lluvia_total = metric_act.get("precipTotal") or 0.0

    if data_hoy and "observations" in data_hoy:
        for obs in data_hoy["observations"]:
            m = obs.get("metric", {})
            t = m.get("tempAvg") if m.get("tempAvg") is not None else (m.get("tempHigh") or m.get("tempLow"))
            if t is not None:
                temps_hoy.append(t)
            h = obs.get("humidityAvg") if obs.get("humidityAvg") is not None else obs.get("humidityHigh")
            if h is not None:
                hum_hoy.append(h)
            
            p_rel = m.get("pressureMin") or m.get("pressureMax") or m.get("pressure")
            if p_rel is not None and p_rel > 700:
                pres_rel_hoy.append(p_rel)
                p_abs = calcular_presion_absoluta(p_rel, t, STATION_ALTITUDE)
                pres_abs_hoy.append(p_abs)
                m["pressureRel"] = p_rel
                m["pressureAbs"] = p_abs

            w = m.get("windspeedHigh") or m.get("windspeedAvg") or 0.0
            if w > viento_max:
                viento_max = w
            g = m.get("windgustHigh") or m.get("windgustAvg") or 0.0
            if g > rafaga_max:
                rafaga_max = g
            ll = m.get("precipTotal") or 0.0
            if ll > lluvia_total:
                lluvia_total = ll

    # Presiones actuales
    p_rel_actual = metric_act.get("pressure")
    p_abs_actual = calcular_presion_absoluta(p_rel_actual, metric_act.get("temp"), STATION_ALTITUDE)
    if p_abs_actual is not None:
        pres_abs_hoy.append(p_abs_actual)
    if p_rel_actual is not None:
        pres_rel_hoy.append(p_rel_actual)

    # Si hay resumen diario de la API, cotejar
    if data_resumen_dia and "observations" in data_resumen_dia and data_resumen_dia["observations"]:
        dia_m = data_resumen_dia["observations"][0].get("metric", {})
        temp_max_dia = dia_m.get("tempHigh") if dia_m.get("tempHigh") is not None else (max(temps_hoy) if temps_hoy else metric_act.get("temp"))
        temp_min_dia = dia_m.get("tempLow") if dia_m.get("tempLow") is not None else (min(temps_hoy) if temps_hoy else metric_act.get("temp"))
        temp_avg_dia = dia_m.get("tempAvg") if dia_m.get("tempAvg") is not None else (sum(temps_hoy)/len(temps_hoy) if temps_hoy else metric_act.get("temp"))
        viento_max = max(viento_max, dia_m.get("windspeedHigh") or 0.0)
        rafaga_max = max(rafaga_max, dia_m.get("windgustHigh") or 0.0)
        lluvia_total = max(lluvia_total, dia_m.get("precipTotal") or 0.0)
    else:
        temp_max_dia = max(temps_hoy) if temps_hoy else metric_act.get("temp")
        temp_min_dia = min(temps_hoy) if temps_hoy else metric_act.get("temp")
        temp_avg_dia = round(sum(temps_hoy)/len(temps_hoy), 1) if temps_hoy else metric_act.get("temp")

    # Asegurar que los extremos incluyan la observación actual en tiempo real
    if metric_act.get("temp") is not None:
        temp_cur = metric_act.get("temp")
        if temp_max_dia is None or temp_cur > temp_max_dia:
            temp_max_dia = temp_cur
        if temp_min_dia is None or temp_cur < temp_min_dia:
            temp_min_dia = temp_cur

    # Dirección del viento en texto cardinal
    def deg_to_compass(d):
        if d is None:
            return "---"
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = int((d + 11.25) / 22.5) % 16
        return dirs[idx]

    wind_deg = obs_actual.get("winddir")
    wind_cardinal = deg_to_compass(wind_deg)

    # Estructura limpia para datos_actuales.json
    salida_actual = {
        "estacion": {
            "id": STATION_ID,
            "nombre": STATION_NAME,
            "ubicacion": STATION_LOCATION,
            "barrio": obs_actual.get("neighborhood", "Campo Quijano"),
            "pais": obs_actual.get("country", "AR"),
            "latitud": obs_actual.get("lat", STATION_LAT),
            "longitud": obs_actual.get("lon", STATION_LON),
            "elevacion_m": STATION_ALTITUDE,
            "software": STATION_HARDWARE,
            "actualizado_utc": obs_actual.get("obsTimeUtc"),
            "actualizado_local": obs_actual.get("obsTimeLocal"),
            "epoch": obs_actual.get("epoch"),
            "estado_qc": obs_actual.get("qcStatus")
        },
        "clima_actual": {
            "temperatura": metric_act.get("temp"),
            "sensacion_termica": metric_act.get("windChill"),
            "indice_calor": metric_act.get("heatIndex"),
            "punto_rocio": metric_act.get("dewpt"),
            "humedad": obs_actual.get("humidity"),
            "presion": p_rel_actual,
            "presion_relativa": p_rel_actual,
            "presion_absoluta": p_abs_actual,
            "viento_velocidad": metric_act.get("windSpeed"),
            "viento_rafaga": metric_act.get("windGust"),
            "viento_direccion_grados": wind_deg,
            "viento_direccion_cardinal": wind_cardinal,
            "lluvia_tasa": metric_act.get("precipRate", 0.0),
            "lluvia_hoy": lluvia_total,
            "radiacion_solar": obs_actual.get("solarRadiation"),
            "uv": obs_actual.get("uv")
        },
        "extremos_hoy": {
            "temperatura_max": temp_max_dia,
            "temperatura_min": temp_min_dia,
            "temperatura_media": temp_avg_dia,
            "humedad_max": max(hum_hoy) if hum_hoy else obs_actual.get("humidity"),
            "humedad_min": min(hum_hoy) if hum_hoy else obs_actual.get("humidity"),
            "presion_max": max(pres_rel_hoy) if pres_rel_hoy else p_rel_actual,
            "presion_min": min(pres_rel_hoy) if pres_rel_hoy else p_rel_actual,
            "presion_rel_max": max(pres_rel_hoy) if pres_rel_hoy else p_rel_actual,
            "presion_rel_min": min(pres_rel_hoy) if pres_rel_hoy else p_rel_actual,
            "presion_abs_max": max(pres_abs_hoy) if pres_abs_hoy else p_abs_actual,
            "presion_abs_min": min(pres_abs_hoy) if pres_abs_hoy else p_abs_actual,
            "viento_maximo": round(viento_max, 1),
            "rafaga_maxima": round(rafaga_max, 1),
            "lluvia_total": round(lluvia_total, 2)
        }
    }

    # Guardar datos_actuales.json
    path_actual = os.path.join(SCRIPT_DIR, "datos_actuales.json")
    with open(path_actual, "w", encoding="utf-8") as f:
        json.dump(salida_actual, f, indent=2, ensure_ascii=False)
    print(f"[OK] Guardado: {path_actual}")

    # Guardar hoy_5min.json (filtrando valores vacíos)
    if data_hoy and "observations" in data_hoy:
        path_hoy = os.path.join(SCRIPT_DIR, "hoy_5min.json")
        with open(path_hoy, "w", encoding="utf-8") as f:
            json.dump(data_hoy["observations"], f, indent=2, ensure_ascii=False)
        print(f"[OK] Guardado: {path_hoy} ({len(data_hoy['observations'])} registros)")

    # Guardar historico_7dias.json
    if data_7dias and "observations" in data_7dias:
        path_7dias = os.path.join(SCRIPT_DIR, "historico_7dias.json")
        with open(path_7dias, "w", encoding="utf-8") as f:
            json.dump(data_7dias["observations"], f, indent=2, ensure_ascii=False)
        print(f"[OK] Guardado: {path_7dias} ({len(data_7dias['observations'])} registros)")

    # Actualizar o agregar registro al acumulativo CSV histórico (historico_diario.csv)
    path_csv = os.path.join(SCRIPT_DIR, "historico_diario.csv")
    path_xlsx = os.path.join(SCRIPT_DIR, "historico_diario.xlsx")
    filas_actualizadas = actualizar_csv_historico(path_csv, ahora.strftime("%Y-%m-%d"), salida_actual)
    actualizar_excel_historico(path_xlsx, filas_actualizadas)

    print("=== Proceso finalizado con éxito ===")
    return True


def actualizar_csv_historico(csv_path, fecha_iso, datos):
    """Guarda o actualiza la fila del día en un CSV permanente para los resúmenes mensuales/anuales."""
    campos = [
        "Fecha", "Temp_Max", "Temp_Min", "Temp_Media", "Humedad_Max", "Humedad_Min",
        "Presion_Abs_Max", "Presion_Abs_Min", "Presion_Rel_Max", "Presion_Rel_Min",
        "Viento_Max", "Rafaga_Max", "Lluvia_Total"
    ]
    
    filas = {}
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    # Retrocompatibilidad si existían campos viejos
                    if "Presion_Abs_Max" not in r or not r.get("Presion_Abs_Max"):
                        p_rel_max = float(r.get("Presion_Max") or 1013.0)
                        p_rel_min = float(r.get("Presion_Min") or 1013.0)
                        t_med = float(r.get("Temp_Media") or 15.0)
                        r["Presion_Abs_Max"] = calcular_presion_absoluta(p_rel_max, t_med, STATION_ALTITUDE)
                        r["Presion_Abs_Min"] = calcular_presion_absoluta(p_rel_min, t_med, STATION_ALTITUDE)
                        r["Presion_Rel_Max"] = p_rel_max
                        r["Presion_Rel_Min"] = p_rel_min
                    filas[r["Fecha"]] = r
        except Exception as e:
            print(f"[!] Error al leer CSV existente: {e}")

    ext = datos["extremos_hoy"]
    filas[fecha_iso] = {
        "Fecha": fecha_iso,
        "Temp_Max": ext["temperatura_max"],
        "Temp_Min": ext["temperatura_min"],
        "Temp_Media": ext["temperatura_media"],
        "Humedad_Max": ext["humedad_max"],
        "Humedad_Min": ext["humedad_min"],
        "Presion_Abs_Max": ext.get("presion_abs_max", ext.get("presion_max")),
        "Presion_Abs_Min": ext.get("presion_abs_min", ext.get("presion_min")),
        "Presion_Rel_Max": ext.get("presion_rel_max", ext.get("presion_max")),
        "Presion_Rel_Min": ext.get("presion_rel_min", ext.get("presion_min")),
        "Viento_Max": ext["viento_maximo"],
        "Rafaga_Max": ext["rafaga_maxima"],
        "Lluvia_Total": ext["lluvia_total"]
    }

    # Escribir ordenado cronológicamente
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        for fecha in sorted(filas.keys()):
            # Filtrar para escribir solo los campos del nuevo esquema
            row_dict = {k: filas[fecha].get(k, "") for k in campos}
            writer.writerow(row_dict)
    print(f"[OK] CSV histórico actualizado: {csv_path} ({len(filas)} días registrados)")
    return filas


def actualizar_excel_historico(xlsx_path, filas):
    """Genera un archivo Excel (.xlsx) con formato institucional y fórmulas para abrir directamente en Microsoft Excel."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Histórico Diario"

        # Título y Subtítulo
        ws.merge_cells("A1:M1")
        ws["A1"] = f"Estación Meteorológica Automática — {STATION_NAME} ({STATION_ID})"
        ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="1F4E78")
        ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

        ws.merge_cells("A2:M2")
        ws["A2"] = f"Ubicación: {STATION_LOCATION} | Altitud: {int(STATION_ALTITUDE)} msnm | {STATION_HARDWARE} | Proyecto MATTEO - INTA Salta"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="595959")
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")

        # Encabezados
        columnas = [
            ("Fecha", "Fecha"),
            ("Temp_Max", "Temp Máx (°C)"),
            ("Temp_Min", "Temp Mín (°C)"),
            ("Temp_Media", "Temp Media (°C)"),
            ("Humedad_Max", "Humedad Máx (%)"),
            ("Humedad_Min", "Humedad Mín (%)"),
            ("Presion_Abs_Max", "Presión Abs Máx (hPa)"),
            ("Presion_Abs_Min", "Presión Abs Mín (hPa)"),
            ("Presion_Rel_Max", "Presión Rel Máx (hPa)"),
            ("Presion_Rel_Min", "Presión Rel Mín (hPa)"),
            ("Viento_Max", "Viento Máx (km/h)"),
            ("Rafaga_Max", "Ráfaga Máx (km/h)"),
            ("Lluvia_Total", "Lluvia Total (mm)")
        ]

        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        zebra_fill = PatternFill(start_color="F2F7FA", end_color="F2F7FA", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
        )

        for col_idx, (clave, titulo) in enumerate(columnas, 1):
            cell = ws.cell(row=4, column=col_idx, value=titulo)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        # Datos
        row_num = 5
        for idx, fecha in enumerate(sorted(filas.keys())):
            r = filas[fecha]
            fill = zebra_fill if idx % 2 == 1 else PatternFill(fill_type=None)

            for col_idx, (clave, _) in enumerate(columnas, 1):
                cell = ws.cell(row=row_num, column=col_idx)
                val_raw = r.get(clave, "")
                cell.fill = fill
                cell.border = thin_border

                if clave == "Fecha":
                    cell.value = str(val_raw)
                    cell.alignment = Alignment(horizontal="center")
                else:
                    try:
                        num = float(val_raw)
                        cell.value = num
                        cell.alignment = Alignment(horizontal="right")
                        if "Lluvia" in clave:
                            cell.number_format = "0.00"
                        elif "Temp" in clave or "Presion" in clave:
                            cell.number_format = "0.0"
                        else:
                            cell.number_format = "0"
                    except (ValueError, TypeError):
                        cell.value = str(val_raw)
                        cell.alignment = Alignment(horizontal="center")

            row_num += 1

        # Ajuste automático del ancho de columnas
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        ws.row_dimensions[4].height = 28
        wb.save(xlsx_path)
        print(f"[OK] Excel generado con éxito: {xlsx_path}")
    except ImportError:
        print("[!] openpyxl no está instalado. No se pudo generar .xlsx")
    except Exception as e:
        print(f"[!] Error al generar Excel: {e}")


if __name__ == "__main__":
    procesar_datos()
