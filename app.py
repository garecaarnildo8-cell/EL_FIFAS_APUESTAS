
def buscar_logo_en_bd(nombre, cursor):
    if not nombre:
        return ""
    nom = str(nombre).strip().lower()
    try:
        # 1. Coincidencia EXACTA en Equipos_Escudos
        cursor.execute("SELECT logo_url FROM Equipos_Escudos WHERE LOWER(nombre_equipo) = ? LIMIT 1", (nom,))
        r = cursor.fetchone()
        if r and r[0]:
            return r[0]

        # 2. Coincidencia EXACTA en Equipos_Maestro
        cursor.execute("SELECT escudo FROM Equipos_Maestro WHERE LOWER(nombre_bd) = ? LIMIT 1", (nom,))
        r = cursor.fetchone()
        if r and r[0]:
            return r[0]

        # 3. Coincidencia EXACTA en Partidos_Global (local)
        cursor.execute("SELECT escudo_local FROM Partidos_Global WHERE LOWER(equipo_local) = ? AND escudo_local LIKE 'http%' LIMIT 1", (nom,))
        r = cursor.fetchone()
        if r and r[0]:
            return r[0]

        # 4. Coincidencia EXACTA en Partidos_Global (visitante)
        cursor.execute("SELECT escudo_visita FROM Partidos_Global WHERE LOWER(equipo_visitante) = ? AND escudo_visita LIKE 'http%' LIMIT 1", (nom,))
        r = cursor.fetchone()
        if r and r[0]:
            return r[0]
    except Exception:
        pass
    return ""

def resolver_escudo_auto(nombre):
    if not nombre: return ""
    n = str(nombre).lower().replace(" ", "").replace("-", "")
    mapa = {
        "juve": 496, "atal": 499, "mila": 489, "lecc": 891,
        "cori": 132, "brag": 794, "athl": 134, "bahi": 118,
        "vasc": 133, "saop": 126, "inte": 119, "flam": 127,
        "palm": 121, "grem": 130, "live": 40,  "bour": 35,
        "leed": 63,  "crys": 52,  "fulh": 36,  "manc": 33,
        "manu": 33,  "geta": 546, "mala": 544, "auxe": 1063,
        "bres": 106, "nice": 84,  "lill": 79,  "beti": 543,
        "real": 541, "atle": 530, "barc": 529
    }
    for k, tid in mapa.items():
        if k in n:
            return f"https://media.api-sports.io/football/teams/{tid}.png"
    return ""

import datetime
import os
import subprocess
from flask import Flask, request, jsonify, render_template
import requests
import sqlite3
import pandas as pd
import os
import subprocess
from datetime import date
import urllib.parse
import cloudscraper
from bs4 import BeautifulSoup
import google.generativeai as genai

GEMINI_API_KEY = "AQ.Ab8RN6KZS_npgm4rY28X4TrOzn64-mqZdru4gA447f0gMMMArw"
genai.configure(api_key=GEMINI_API_KEY)
modelo_ia = genai.GenerativeModel("gemini-3.5-flash-lite", generation_config={"max_output_tokens": 250, "temperature": 0.7})

app = Flask(__name__)

# ==============================================================================
# AUTO-ACTUALIZACIÓN DIARIA INTELIGENTE (SIN TAREAS DE PAGO)
# ==============================================================================
@app.before_request
def verificar_actualizacion_diaria():
    archivo_control = "ultima_actualizacion.txt"
    hoy = datetime.now().strftime("%Y-%m-%d")

    try:
        if os.path.exists(archivo_control):
            with open(archivo_control, "r") as f:
                if f.read().strip() == hoy:
                    return  # Ya se actualizó hoy, carga la web normalmente

        # Anotar la fecha de hoy para no volver a ejecutar en las siguientes visitas
        with open(archivo_control, "w") as f:
            f.write(hoy)

        # Ejecutar los actualizadores en segundo plano (en silencio)
        cmd = (
            "/home/Arnildo/app_apuestas/venv/bin/python"
            " /home/Arnildo/app_apuestas/actualizador_diario.py &&"
            " /home/Arnildo/app_apuestas/venv/bin/python"
            " /home/Arnildo/app_apuestas/actualizador_brasil.py"
        )
        subprocess.Popen(cmd, shell=True)
        print(f"⚡ [AUTO-UPDATE] Primera visita del día: sincronizando partidos de {hoy}...")
    except Exception as e:
        print(f"⚠️ [AUTO-UPDATE ERROR]: {e}")


# ----------------------------------------------------
# MAPEO AMPLIO DE ALIAS PARA BASE DE DATOS
# ----------------------------------------------------
ALIAS_HISTORICOS = {
    "Atletico Madrid": ["Atletico Madrid", "Ath Madrid", "Atlético Madrid", "Atletico de Madrid"],
    "Real Madrid": ["Real Madrid", "R Madrid"],
    "Barcelona": ["Barcelona", "FC Barcelona"],
    "Athletic Club": ["Athletic Club", "Ath Bilbao", "Athletic Bilbao"],
    "Wolverhampton": ["Wolverhampton", "Wolves", "Wolverhampton Wanderers"],
    "Nottingham Forest": ["Nottingham Forest", "Nott'm Forest"],
    "Paris Saint Germain": ["Paris Saint Germain", "Paris SG", "PSG"],
    "Manchester City": ["Manchester City", "Man City"],
    "Manchester United": ["Manchester United", "Man United"],
    "Newcastle": ["Newcastle", "Newcastle United"],
    "Tottenham": ["Tottenham", "Tottenham Hotspur", "Spurs"],
    "Celta Vigo": ["Celta Vigo", "Celta"],
    "Real Betis": ["Real Betis", "Betis"],
    "Real Sociedad": ["Real Sociedad", "Sociedad"],
    "Rayo Vallecano": ["Rayo Vallecano", "Vallecano"],
    "Espanyol": ["Espanyol", "Espanol"],
    "Deportivo La Coruna": ["Deportivo La Coruna", "La Coruna"],
    "Palmeiras": ["Palmeiras", "SE Palmeiras"],
    "Flamengo": ["Flamengo", "CR Flamengo"],
    "Corinthians": ["Corinthians", "SC Corinthians"],
    "Gremio": ["Gremio", "Grêmio"]
}

def obtener_alias(nombre_oficial):
    nombre_limpio = nombre_oficial.strip()
    sin_tildes = nombre_limpio.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    variantes = {nombre_limpio, nombre_limpio.lower(), sin_tildes, sin_tildes.lower()}

    for oficial, lista in ALIAS_HISTORICOS.items():
        if oficial.lower() in nombre_limpio.lower() or nombre_limpio.lower() in oficial.lower():
            for alias in lista:
                variantes.add(alias.strip())
                variantes.add(alias.strip().lower())
                variantes.add(alias.strip().lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u'))
    return list(variantes)

def resolver_logo_db(nombre_equipo):
    """Busca el escudo oficial con prioridad estricta para evitar falsos positivos."""
    if not nombre_equipo:
        return "https://cdn-icons-png.flaticon.com/512/53/53283.png"

    nom = str(nombre_equipo).strip().lower()
    sin_tildes = nom.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')

    try:
        con = sqlite3.connect('apuestas_master.db')
        cur = con.cursor()

        # 1. PRIORIDAD MÁXIMA: Coincidencia exacta del nombre completo
        cur.execute("""
            SELECT logo_url FROM Equipos_Escudos
            WHERE LOWER(nombre_equipo) = ? OR LOWER(nombre_equipo) = ?
            LIMIT 1
        """, (nom, sin_tildes))
        fila = cur.fetchone()
        if fila and fila[0]:
            con.close()
            return fila[0]

        # 2. PRIORIDAD MEDIA: Alias históricos oficiales ya mapeados
        alias_posibles = obtener_alias(nombre_equipo)
        for al in alias_posibles:
            cur.execute("SELECT logo_url FROM Equipos_Escudos WHERE LOWER(nombre_equipo) = ? LIMIT 1", (al.lower(),))
            fila = cur.fetchone()
            if fila and fila[0]:
                con.close()
                return fila[0]

        # 3. PRIORIDAD BAJA: Búsqueda parcial SOLO con nombres largos (mínimo 4 letras)
        if len(nom) >= 4:
            cur.execute("""
                SELECT logo_url FROM Equipos_Escudos
                WHERE LENGTH(nombre_equipo) >= 4
                  AND (LOWER(nombre_equipo) LIKE ? OR ? LIKE '%' || LOWER(nombre_equipo) || '%')
                ORDER BY LENGTH(nombre_equipo) DESC
                LIMIT 1
            """, (f"%{nom}%", nom))
            fila = cur.fetchone()
            if fila and fila[0]:
                con.close()
                return fila[0]

        con.close()
    except Exception:
        pass

    return "https://cdn-icons-png.flaticon.com/512/53/53283.png"

def auto_scrapear_y_guardar_arbitro(nombre_arbitro):
    """Busca al árbitro automáticamente en la web, extrae datos y lo guarda en SQLite."""
    try:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        query = urllib.parse.quote(nombre_arbitro.strip())
        url_busqueda = f"https://www.transfermarkt.es/schnellsuche/ergebnis/schnellsuche?query={query}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = scraper.get(url_busqueda, headers=headers, timeout=6)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, 'html.parser')

        link_arb = None
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if 'schiedsrichter' in href and ('profil' in href or 'bilanz' in href):
                link_arb = a
                break

        if not link_arb:
            return None

        href_limpio = link_arb['href']
        url_perfil = href_limpio if href_limpio.startswith('http') else "https://www.transfermarkt.es" + href_limpio
        if '/profil/' in url_perfil:
            url_perfil = url_perfil.replace('/profil/', '/bilanz/')

        nombre_oficial = link_arb.text.strip() or nombre_arbitro

        res_perfil = scraper.get(url_perfil, headers=headers, timeout=6)
        soup_p = BeautifulSoup(res_perfil.text, 'html.parser')

        tabla = soup_p.find('table', class_='items')
        if not tabla or not tabla.find('tfoot'):
            res_perfil = scraper.get(href_limpio if href_limpio.startswith('http') else "https://www.transfermarkt.es" + href_limpio, headers=headers, timeout=6)
            soup_p = BeautifulSoup(res_perfil.text, 'html.parser')
            tabla = soup_p.find('table', class_='items')

        if not tabla or not tabla.find('tfoot'):
            return None

        celdas = tabla.find('tfoot').find_all('td')
        if len(celdas) < 6:
            return None

        pj = int(celdas[2].text.strip().replace('.', '') or 0)
        amarillas = int(celdas[3].text.strip().replace('.', '') or 0)
        doble_ama = int(celdas[4].text.strip().replace('.', '') or 0)
        rojas = int(celdas[5].text.strip().replace('.', '') or 0)

        if pj == 0:
            return None

        tot_tarjetas = amarillas + doble_ama + rojas
        promedio = round(tot_tarjetas / pj, 1)

        if promedio >= 5.3:
            perfil = "🔴 Muy Tarjetero"
        elif promedio >= 4.2:
            perfil = "🟡 Rigor Medio"
        else:
            perfil = "🟢 Permisivo"

        o35 = min(round(promedio * 16.5, 1), 95.0)
        o45 = min(round(promedio * 11.5, 1), 85.0)
        o55 = min(round(promedio * 6.5, 1), 70.0)

        con = sqlite3.connect('apuestas_master.db')
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Arbitros_Historico (
                nombre_arbitro TEXT PRIMARY KEY,
                partidos INTEGER,
                promedio REAL,
                perfil TEXT,
                over_3_5_pct REAL,
                over_4_5_pct REAL,
                over_5_5_pct REAL
            )
        """)
        cur.execute("""
            INSERT OR REPLACE INTO Arbitros_Historico
            (nombre_arbitro, partidos, promedio, perfil, over_3_5_pct, over_4_5_pct, over_5_5_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre_oficial, pj, promedio, perfil, o35, o45, o55))
        con.commit()
        con.close()

        return {
            'partidos': pj,
            'promedio': promedio,
            'perfil': perfil,
            'over_3_5_pct': o35,
            'over_4_5_pct': o45,
            'over_5_5_pct': o55
        }
    except Exception:
        return None
# ----------------------------------------------------
# RUTA 1: LA PANTALLA PRINCIPAL (Cartelera Automática)
# ----------------------------------------------------
@app.route('/')
def inicio():
    import sqlite3
    import requests
    from datetime import datetime, timezone, timedelta
    import pytz
    import time

    tz_bolivia = pytz.timezone('America/La_Paz')
    ahora = datetime.now(tz_bolivia)
    # --- CORTE OPERATIVO 4:00 AM (Hora de Bolivia UTC-4) ---

    ahora_utc = datetime.now(timezone.utc)

    ahora_op = ahora_utc - timedelta(hours=8) # Resta 4h de zona horaria y 4h de corte operativo

    f_hoy = ahora_op.strftime('%Y-%m-%d')

    f_ayer = (ahora_op - timedelta(days=1)).strftime('%Y-%m-%d')

    f_manana = (ahora_op + timedelta(days=1)).strftime('%Y-%m-%d')

    dia_sel = request.args.get('dia', '').lower()

    # Función para consultar la última fecha completa en la BD local
    def cargar_ultima_jornada_bd():
        try:
            conn = sqlite3.connect('apuestas_master.db')
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT fecha FROM Partidos_Global WHERE fecha IS NOT NULL AND fecha != ''")
            fechas = [r[0] for r in cursor.fetchall()]
            if not fechas:
                conn.close()
                return [], "Sin registros"

            def norm_f(f_str):
                p = str(f_str).replace('/', '-').split('-')
                if len(p) == 3 and len(p[0]) == 2:
                    return f"{p[2]}-{p[1]}-{p[0]}"
                return str(f_str)

            ultima_f = sorted(fechas, key=norm_f, reverse=True)[0]
            cursor.execute("""
                SELECT p.rowid AS row_id, p.*, 
                       el.escudo AS master_esc_l, el.liga AS master_liga_l,
                       ev.escudo AS master_esc_v, ev.liga AS master_liga_v
                FROM Partidos_Global p
                LEFT JOIN Equipos_Maestro el ON p.equipo_local = el.nombre_bd
                LEFT JOIN Equipos_Maestro ev ON p.equipo_visitante = ev.nombre_bd
                WHERE p.fecha = ?
            """, (ultima_f,))
            filas = cursor.fetchall()
            col_names = [d[0].lower() for d in cursor.description]
            idx_map = {name: i for i, name in enumerate(col_names)}

            def val(fila, keys, default=None):
                for k in keys:
                    if k in idx_map:
                        v = fila[idx_map[k]]
                        if v is not None:
                            return v
                return default

            partidos = []
            partidos_unicos_vistos = set()
            for r in filas:
                clave_dedup = (val(r, ['equipo_local', 'local'], '').lower()[:5], val(r, ['equipo_visitante', 'visitante'], '').lower()[:5])
                if clave_dedup in partidos_unicos_vistos:
                    continue
                partidos_unicos_vistos.add(clave_dedup)
                loc_nom = val(r, ['equipo_local', 'local'], 'Local')
                vis_nom = val(r, ['equipo_visitante', 'visitante', 'visita'], 'Visitante')
                
                # 1. Usar el guardado, o buscar en la BD histórica por coincidencia
                esc_l = val(r, ['escudo_local', 'logo_local'], '')
                if not esc_l or not str(esc_l).startswith('http'):
                    esc_l = buscar_logo_en_bd(loc_nom, cursor)

                esc_v = val(r, ['escudo_visita', 'logo_visita'], '')
                if not esc_v or not str(esc_v).startswith('http'):
                    esc_v = buscar_logo_en_bd(vis_nom, cursor)

                partidos.append({
                    'id': r[0],
                    'fecha': val(r, ['fecha'], ultima_f),
                    'hora': val(r, ['hora'], 'Finalizado'),
                    'liga': val(r, ['liga', 'campeonato', 'master_liga_l', 'master_liga_v'], 'Liga Principal'),
                    'local': loc_nom,
                    'visitante': vis_nom,
                    'escudo_local': esc_l,
                    'escudo_visita': esc_v,
                    'goles_local': val(r, ['goles_local', 'gol_l'], '-'),
                    'goles_visita': val(r, ['goles_visitante', 'goles_visita', 'gol_v'], '-'),
                    'estado': 'FT'
                })
            conn.close()
            return partidos, ultima_f
        except Exception as err:
            print(f"Error cargando BD local: {err}")
            return [], "Error BD"

    # Función para consultar API con Lazy Cache en SQLite (1 sola llamada al día)
    def consultar_api(f_str):
        ligas_permitidas = {
            71: 'Brasileirão',
            39: 'Premier League',
            140: 'La Liga',
            135: 'Serie A',
            78: 'Bundesliga',
            61: 'Ligue 1',
            2: 'Champions League',
            13: 'Copa Libertadores',
            11: 'Copa Sudamericana'
        }
        partidos_db = []
        try:
            conn = sqlite3.connect('apuestas_master.db')
            cur = conn.cursor()
            cur.execute("""
                SELECT fixture_id, fecha, hora, liga, local, visitante,
                       escudo_local, escudo_visita, goles_local, goles_visita, estado, arbitro
                FROM Partidos_Cache_Diario
                WHERE fecha = ?
                ORDER BY hora ASC
            """, (f_str,))
            filas = cur.fetchall()
            for r in filas:
                partidos_db.append({
                    'id': r[0],
                    'fecha': r[1],
                    'hora': r[2],
                    'liga': r[3],
                    'local': r[4],
                    'visitante': r[5],
                    'escudo_local': r[6],
                    'escudo_visita': r[7],
                    'goles_local': r[8] if r[8] is not None else '-',
                    'goles_visita': r[9] if r[9] is not None else '-',
                    'estado': r[10] if r[10] else 'NS',
                    'arbitro': r[11] if r[11] else 'Por definir'
                })
            conn.close()
        except Exception as e:
            print(f"Error leyendo Partidos_Cache_Diario: {e}")

        if partidos_db:
            return partidos_db

        filtrados = []
        try:
            headers_api = {"x-apisports-key": "77f9132f21d5664ba6f556d8d42893dd"}
            url = "https://sportapi7.p.rapidapi.com/fixtures"
            params = {"date": f_str, "timezone": "America/La_Paz"}
            res = requests.get(url, headers=headers_api, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json().get('response', [])
                conn = sqlite3.connect('apuestas_master.db')
                cur = conn.cursor()
                for p in data:
                    lid = p.get('league', {}).get('id')
                    if lid in ligas_permitidas:
                        fid = p['fixture']['id']
                        fch = p['fixture']['date'][:10]
                        hra = p['fixture']['date'][11:16]
                        lga = ligas_permitidas[lid]
                        loc = p['teams']['home']['name']
                        vis = p['teams']['away']['name']
                        esc_l = p['teams']['home'].get('logo', '')
                        esc_v = p['teams']['away'].get('logo', '')
                        gol_l = p['goals'].get('home')
                        gol_v = p['goals'].get('away')
                        est = p['fixture']['status'].get('short', 'NS')
                        arb = p['fixture'].get('referee') or 'Por definir'

                        cur.execute("""
                            INSERT OR REPLACE INTO Partidos_Cache_Diario (
                                fixture_id, fecha, hora, liga, local, visitante,
                                escudo_local, escudo_visita, goles_local, goles_visita, estado, arbitro
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fid, fch, hra, lga, loc, vis, esc_l, esc_v, gol_l, gol_v, est, arb))

                        filtrados.append({
                            'id': fid,
                            'fecha': fch,
                            'hora': hra,
                            'liga': lga,
                            'local': loc,
                            'visitante': vis,
                            'escudo_local': esc_l,
                            'escudo_visita': esc_v,
                            'goles_local': gol_l if gol_l is not None else '-',
                            'goles_visita': gol_v if gol_v is not None else '-',
                            'estado': est,
                            'arbitro': arb
                        })
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Error API {f_str}: {e}")

        return filtrados

    # Ruteo según el botón pulsado
    if dia_sel == 'ultima':
        partidos, f_titulo = cargar_ultima_jornada_bd()
        estado = f"Última Jornada Guardada ({len(partidos)} partidos)"
        dia_activo = 'ultima'
    elif dia_sel == 'ayer':
        partidos = consultar_api(f_ayer)
        f_titulo = f_ayer
        estado = f"Jornada de Ayer ({len(partidos)} partidos)"
        dia_activo = 'ayer'
    elif dia_sel == 'manana':
        partidos = consultar_api(f_manana)
        f_titulo = f_manana
        estado = f"Jornada de Mañana ({len(partidos)} partidos)"
        dia_activo = 'manana'
    else:
        # Por defecto HOY: si no hay partidos en vivo hoy, abre automáticamente la última jornada registrada
        partidos_hoy = consultar_api(f_hoy)
        if partidos_hoy:
            partidos = partidos_hoy
            f_titulo = f_hoy
            estado = f"Jornada de Hoy ({len(partidos)} partidos)"
            dia_activo = 'hoy'
        else:
            partidos, f_titulo = cargar_ultima_jornada_bd()
            estado = f"Sin partidos hoy — Mostrando Última Jornada Guardada ({len(partidos)} partidos)"
            dia_activo = 'ultima'

    return render_template(
        'index.html',
        partidos=partidos,
        fecha_hoy=f_titulo,
        dia_seleccionado=dia_activo,
        estado_jornada=estado
    )


@app.route('/analisis/<liga_o_id>/<equipo_local>/<equipo_visitante>')
@app.route('/analizar/<liga_o_id>/<equipo_local>/<equipo_visitante>')
@app.route('/analisis/<equipo_local>/<equipo_visitante>')
@app.route('/analizar/<equipo_local>/<equipo_visitante>')
def analizar_partido(equipo_local, equipo_visitante, liga_o_id=None):
    # Detectar si se pasó un fixture_id numérico real de API-Sports
    fixture_id = None
    if liga_o_id and str(liga_o_id).isdigit():
        fixture_id = int(liga_o_id)

    # --- 1. CAPTURA COMBINADA DE ÁRBITRO Y ALINEACIONES (CON CACHÉ SQLITE) ---
    arbitro_vivo = "Por definir"
    formacion_local = "Aún no disponible"
    formacion_visita = "Aún no disponible"

    if fixture_id:
        try:
            conn_cache = sqlite3.connect('apuestas_master.db')
            cur_cache = conn_cache.cursor()
            
            # Revisar si ya están en Alineaciones_Cache
            cur_cache.execute("SELECT datos_json, arbitro FROM Alineaciones_Cache WHERE fixture_id = ?", (fixture_id,))
            row_ali = cur_cache.fetchone()
            
            # Revisar si el árbitro ya está en Partidos_Cache_Diario
            cur_cache.execute("SELECT hora, arbitro FROM Partidos_Cache_Diario WHERE fixture_id = ?", (fixture_id,))
            row_par = cur_cache.fetchone()
            hora_partido = row_par[0] if row_par else None
            if row_par and row_par[1] and row_par[1] != 'Por definir':
                arbitro_vivo = row_par[1]

            if row_ali and row_ali[0]:
                import json
                datos_ali = json.loads(row_ali[0])
                if len(datos_ali) == 2:
                    formacion_local = datos_ali[0].get('formation', 'Confirmada')
                    formacion_visita = datos_ali[1].get('formation', 'Confirmada')
                if row_ali[1] and row_ali[1] != 'Por definir':
                    arbitro_vivo = row_ali[1]
            else:
                # Comprobar ventana de 40 minutos
                consultar_api_ahora = True
                if hora_partido and ':' in hora_partido:
                    try:
                        ahora_bo = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime('%H:%M')
                        hp, mp = map(int, hora_partido.split(':'))
                        ha, ma = map(int, ahora_bo.split(':'))
                        diff_min = (hp * 60 + mp) - (ha * 60 + ma)
                        if diff_min > 40:
                            consultar_api_ahora = False
                    except Exception:
                        pass

                if consultar_api_ahora:
                    url_vivo = f"https://sportapi7.p.rapidapi.com/fixtures?id={fixture_id}"
                    headers_api = {"x-apisports-key": "77f9132f21d5664ba6f556d8d42893dd"}
                    res_api = requests.get(url_vivo, headers=headers_api, timeout=6).json()
                    if res_api.get('response'):
                        datos_partido = res_api['response'][0]
                        ref = datos_partido.get('fixture', {}).get('referee')
                        if ref:
                            arbitro_vivo = ref
                            cur_cache.execute("UPDATE Partidos_Cache_Diario SET arbitro = ? WHERE fixture_id = ?", (arbitro_vivo, fixture_id))
                        lineups = datos_partido.get('lineups', [])
                        if len(lineups) == 2:
                            formacion_local = lineups[0].get('formation', '4-3-3')
                            formacion_visita = lineups[1].get('formation', '4-3-3')
                            import json
                            cur_cache.execute("""
                                INSERT OR REPLACE INTO Alineaciones_Cache (fixture_id, fecha, datos_json, arbitro)
                                VALUES (?, date('now'), ?, ?)
                            """, (fixture_id, json.dumps(lineups), arbitro_vivo))
                        conn_cache.commit()
            conn_cache.close()
        except Exception as e:
            print(f"Error procesando caché de partido: {e}")

    try:
        respuesta_vivo = requests.get(url_vivo, headers=headers).json() if url_vivo else {}
        datos_partido = respuesta_vivo['response'][0]
        if datos_partido['fixture']['referee']: arbitro_vivo = datos_partido['fixture']['referee']
        if len(datos_partido.get('lineups', [])) == 2:
            formacion_local = datos_partido['lineups'][0]['formation']
            formacion_visita = datos_partido['lineups'][1]['formation']
    except Exception:
        pass

    # --- 2. BÚSQUEDA ROBUSTA EN LA BASE DE DATOS ---
    alias_local = obtener_alias(equipo_local)
    alias_visita = obtener_alias(equipo_visitante)

    condiciones = []
    for a in set(alias_local + alias_visita):
        a_escapado = a.replace("'", "''")
        condiciones.append(f"equipo_local LIKE '%{a_escapado}%'")
        condiciones.append(f"equipo_visitante LIKE '%{a_escapado}%'")

    where_sql = " OR ".join(condiciones)
    conexion = sqlite3.connect('apuestas_master.db')

    # --- HISTORIAL ÁRBITRO CON AUTO-APRENDIZAJE AUTOMÁTICO ---
    stats_arbitro = {
        'asignado': arbitro_vivo,
        'partidos': 0,
        'promedio': "Sin datos en BD",
        'perfil': "Desconocido",
        'over_3_5_pct': 0,
        'over_4_5_pct': 0,
        'over_5_5_pct': 0
    }
    promedio_arbitro = "Sin historial en tu BD"

    if arbitro_vivo != "Por definir":
        nombre_limpio = arbitro_vivo.split(',')[0].strip()
        apellido_arbitro = nombre_limpio.split()[-1]

        # 1. Búsqueda primaria en partidos locales (24/25 a 26/27)
        query_arb = f"""
            SELECT tarjetas_local, tarjetas_visitante
            FROM Partidos_Global
            WHERE arbitro LIKE '%{apellido_arbitro}%'
              AND fecha >= '2024-08-01'
        """
        try:
            df_arb = pd.read_sql_query(query_arb, conexion)
            if not df_arb.empty:
                tot_p = len(df_arb)
                df_arb['t_tot'] = pd.to_numeric(df_arb['tarjetas_local'], errors='coerce').fillna(0) + pd.to_numeric(df_arb['tarjetas_visitante'], errors='coerce').fillna(0)
                prom = round(df_arb['t_tot'].mean(), 1)

                if prom >= 5.3: perfil = "🔴 Muy Tarjetero"
                elif prom >= 4.2: perfil = "🟡 Rigor Medio"
                else: perfil = "🟢 Permisivo"

                stats_arbitro['partidos'] = tot_p
                stats_arbitro['promedio'] = prom
                stats_arbitro['perfil'] = perfil
                stats_arbitro['over_3_5_pct'] = round(len(df_arb[df_arb['t_tot'] > 3.5]) / tot_p * 100, 1)
                stats_arbitro['over_4_5_pct'] = round(len(df_arb[df_arb['t_tot'] > 4.5]) / tot_p * 100, 1)
                stats_arbitro['over_5_5_pct'] = round(len(df_arb[df_arb['t_tot'] > 5.5]) / tot_p * 100, 1)
                promedio_arbitro = f"Promedio: {prom} ({perfil}) en {tot_p} PJ (24/27)"
            else:
                # 2. Búsqueda secundaria en Arbitros_Historico
                cur_arb = conexion.cursor()
                cur_arb.execute("""
                    CREATE TABLE IF NOT EXISTS Arbitros_Historico (
                        nombre_arbitro TEXT PRIMARY KEY,
                        partidos INTEGER,
                        promedio REAL,
                        perfil TEXT,
                        over_3_5_pct REAL,
                        over_4_5_pct REAL,
                        over_5_5_pct REAL
                    )
                """)
                cur_arb.execute("""
                    SELECT partidos, promedio, perfil, over_3_5_pct, over_4_5_pct, over_5_5_pct
                    FROM Arbitros_Historico
                    WHERE LOWER(nombre_arbitro) LIKE ? OR ? LIKE '%' || LOWER(nombre_arbitro) || '%'
                    LIMIT 1
                """, (f"%{apellido_arbitro.lower()}%", apellido_arbitro.lower()))
                fila_arb = cur_arb.fetchone()

                if fila_arb:
                    stats_arbitro['partidos'] = fila_arb[0]
                    stats_arbitro['promedio'] = fila_arb[1]
                    stats_arbitro['perfil'] = fila_arb[2]
                    stats_arbitro['over_3_5_pct'] = fila_arb[3]
                    stats_arbitro['over_4_5_pct'] = fila_arb[4]
                    stats_arbitro['over_5_5_pct'] = fila_arb[5]
                    promedio_arbitro = f"Promedio: {fila_arb[1]} ({fila_arb[2]}) [Guardado en BD]"
                else:
                    # 3. RESPALDO: Si no tiene historial, usar la media general de tarjetas de la liga
                    try:
                        cur_arb.execute("SELECT ROUND(AVG(tarjetas_local + tarjetas_visitante), 1) FROM Partidos_Global WHERE tarjetas_local IS NOT NULL")
                        media_liga = cur_arb.fetchone()[0] or 4.3
                    except Exception:
                        media_liga = 4.3
                    perfil_liga = "🟡 Rigor Medio" if media_liga >= 4.2 else ("🔴 Muy Tarjetero" if media_liga >= 5.3 else "🟢 Permisivo")
                    stats_arbitro['partidos'] = "Liga"
                    stats_arbitro['promedio'] = media_liga
                    stats_arbitro['perfil'] = perfil_liga
                    stats_arbitro['over_3_5_pct'] = 65.0
                    stats_arbitro['over_4_5_pct'] = 45.0
                    stats_arbitro['over_5_5_pct'] = 25.0
                    promedio_arbitro = f"Media de la Liga: {media_liga} tarj ({perfil_liga}) [Respaldo General]" 
        except Exception:
            pass

    query = f"""
        SELECT fecha, equipo_local, equipo_visitante, goles_local, goles_visitante,
               corners_local, corners_visitante, tarjetas_local, tarjetas_visitante, rojas_local, rojas_visitante, arbitro
        FROM Partidos_Global
        WHERE {where_sql}
        ORDER BY fecha DESC LIMIT 200
    """
    df = pd.read_sql_query(query, conexion)
    conexion.close()

    if df.empty:
        return f"<h2 style='color:white; text-align:center;'>No hay datos en la BD para {equipo_local} vs {equipo_visitante}.</h2><a href='/' style='color:#00ff88; display:block; text-align:center;'>Volver</a>"

    for col in ['goles_local', 'goles_visitante', 'corners_local', 'corners_visitante', 'tarjetas_local', 'tarjetas_visitante', 'rojas_local', 'rojas_visitante']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- 3. FILTRADO CON MUESTRA CONTINUA ---
    alias_local_lower = [a.lower() for a in alias_local]
    alias_visita_lower = [a.lower() for a in alias_visita]

    df['loc_clean'] = df['equipo_local'].astype(str).str.strip().str.lower()
    df['vis_clean'] = df['equipo_visitante'].astype(str).str.strip().str.lower()

    es_local = df['loc_clean'].apply(lambda n: any(a in n or n in a for a in alias_local_lower)) | \
               df['vis_clean'].apply(lambda n: any(a in n or n in a for a in alias_local_lower))

    es_visita = df['loc_clean'].apply(lambda n: any(a in n or n in a for a in alias_visita_lower)) | \
                df['vis_clean'].apply(lambda n: any(a in n or n in a for a in alias_visita_lower))

    df_local = df[es_local].head(12).copy()
    df_visita = df[es_visita].head(12).copy()

    es_h2h = (df['loc_clean'].apply(lambda n: any(a in n or n in a for a in alias_local_lower)) &
              df['vis_clean'].apply(lambda n: any(a in n or n in a for a in alias_visita_lower))) | \
             (df['loc_clean'].apply(lambda n: any(a in n or n in a for a in alias_visita_lower)) &
              df['vis_clean'].apply(lambda n: any(a in n or n in a for a in alias_local_lower)))
    df_h2h = df[es_h2h].head(5).copy()

    df_combinado = pd.concat([df_local, df_visita]).drop_duplicates(subset=['fecha', 'equipo_local', 'equipo_visitante'])
    total_partidos = len(df_combinado)

    print(f"\n🔍 [ANÁLISIS] {equipo_local} ({len(df_local)} PJ) vs {equipo_visitante} ({len(df_visita)} PJ) | Muestra combinada: {total_partidos} partidos")

    if total_partidos > 0:
        df_combinado['goles_totales'] = df_combinado['goles_local'] + df_combinado['goles_visitante']
        df_combinado['corners_totales'] = df_combinado['corners_local'] + df_combinado['corners_visitante']
        df_combinado['tarjetas_totales'] = df_combinado['tarjetas_local'] + df_combinado['tarjetas_visitante']
    else:
        df_combinado['goles_totales'], df_combinado['corners_totales'], df_combinado['tarjetas_totales'] = 0, 0, 0

    if not df_local.empty:
        es_home_l = df_local['loc_clean'].apply(lambda n: any(a in n or n in a for a in alias_local_lower))
        df_local['goles_p'] = df_local['goles_local'].where(es_home_l, df_local['goles_visitante'])
        df_local['goles_contra'] = df_local['goles_visitante'].where(es_home_l, df_local['goles_local'])
        df_local['corners_p'] = df_local['corners_local'].where(es_home_l, df_local['corners_visitante'])
        df_local['corners_contra'] = df_local['corners_visitante'].where(es_home_l, df_local['corners_local'])
        df_local['tarjetas_p'] = df_local['tarjetas_local'].where(es_home_l, df_local['tarjetas_visitante'])

    if not df_visita.empty:
        es_home_v = df_visita['loc_clean'].apply(lambda n: any(a in n or n in a for a in alias_visita_lower))
        df_visita['goles_p'] = df_visita['goles_local'].where(es_home_v, df_visita['goles_visitante'])
        df_visita['goles_contra'] = df_visita['goles_visitante'].where(es_home_v, df_visita['goles_local'])
        df_visita['corners_p'] = df_visita['corners_local'].where(es_home_v, df_visita['corners_visitante'])
        df_visita['corners_contra'] = df_visita['corners_visitante'].where(es_home_v, df_visita['corners_local'])
        df_visita['tarjetas_p'] = df_visita['tarjetas_local'].where(es_home_v, df_visita['tarjetas_visitante'])

    def calcular_racha_y_puntos(df_racha, alias_target):
        racha = []
        puntos = 0
        for _, row in df_racha.head(5).iterrows():
            es_home = any(a in row['loc_clean'] or row['loc_clean'] in a for a in alias_target)
            gf = row['goles_local'] if es_home else row['goles_visitante']
            gc = row['goles_visitante'] if es_home else row['goles_local']

            if gf > gc:
                racha.append("🟩")
                puntos += 3
            elif gf == gc:
                racha.append("⬜")
                puntos += 1
            else:
                racha.append("🟥")
        return ("".join(racha[::-1]) if racha else "Sin datos", f"{puntos}/15 pts")

    racha_local_str, pts_local = calcular_racha_y_puntos(df_local, alias_local_lower)
    racha_visita_str, pts_visita = calcular_racha_y_puntos(df_visita, alias_visita_lower)

    prom_goles_m = round(df_combinado['goles_totales'].mean(), 1) if total_partidos > 0 else 0
    prom_corners_m = round(df_combinado['corners_totales'].mean(), 1) if total_partidos > 0 else 0
    prom_tarjetas_m = round(df_combinado['tarjetas_totales'].mean(), 1) if total_partidos > 0 else 0

    prom_cor_contra_l = round(df_local['corners_contra'].mean(), 1) if not df_local.empty else 0
    prom_cor_contra_v = round(df_visita['corners_contra'].mean(), 1) if not df_visita.empty else 0

    cor_gana_l = len(df_combinado[df_combinado['corners_local'] > df_combinado['corners_visitante']])
    cor_empate = len(df_combinado[df_combinado['corners_local'] == df_combinado['corners_visitante']])
    cor_gana_v = len(df_combinado[df_combinado['corners_local'] < df_combinado['corners_visitante']])

    cor_1 = round(cor_gana_l / total_partidos * 100, 1) if total_partidos > 0 else 0
    cor_x = round(cor_empate / total_partidos * 100, 1) if total_partidos > 0 else 0
    cor_2 = round(cor_gana_v / total_partidos * 100, 1) if total_partidos > 0 else 0

    patrones_h2h = []
    if not df_h2h.empty:
        total_h2h = len(df_h2h)
        btts_count = len(df_h2h[(df_h2h['goles_local'] > 0) & (df_h2h['goles_visitante'] > 0)])
        over25_count = len(df_h2h[(df_h2h['goles_local'] + df_h2h['goles_visitante']) > 2.5])
        tarjetas_altas = len(df_h2h[(df_h2h['tarjetas_local'] + df_h2h['tarjetas_visitante']) > 4.5])

        if btts_count / total_h2h >= 0.8:
            patrones_h2h.append("🔥 Ambos Marcan se dio en el 80%+ de sus últimos cruces.")
        if over25_count / total_h2h >= 0.8:
            patrones_h2h.append("⚽ Suelen ser partidos de Más de 2.5 Goles (80%+).")
        if tarjetas_altas / total_h2h >= 0.8:
            patrones_h2h.append("🟨 Partido históricamente caliente: Más de 4.5 tarjetas (80%+).")

        if not patrones_h2h:
            patrones_h2h.append("📊 No hay un patrón aplastante en sus últimos cruces.")
    else:
        patrones_h2h.append("⚠️ Sin historial directo reciente en la base de datos.")

    def armar_texto(r):
        cl = int(r['corners_local'])
        cv = int(r['corners_visitante'])
        cor_tot = cl + cv
        tar_tot = int(r['tarjetas_local'] + r['tarjetas_visitante'])
        rl = int(r['rojas_local']) if 'rojas_local' in r and pd.notnull(r['rojas_local']) else 0
        rv = int(r['rojas_visitante']) if 'rojas_visitante' in r and pd.notnull(r['rojas_visitante']) else 0
        rojas_tot = rl + rv
        gl = int(r['goles_local'])
        gv = int(r['goles_visitante'])

        partes = str(r['fecha']).split('-')
        fecha_display = f"{partes[2]}-{partes[1]}-{partes[0]}" if len(partes) == 3 else str(r['fecha'])
        rojas_badge = f" | 🟥 {rojas_tot}" if rojas_tot > 0 else " | 🟥 0"
        return f"{fecha_display} | {r['equipo_local']} {gl}-{gv} {r['equipo_visitante']} (🚩 {cor_tot} [{cl}-{cv}] | 🟨 {tar_tot}{rojas_badge})"

    ultimos_local = [armar_texto(r) for _, r in df_local.head(5).iterrows()]
    ultimos_visita = [armar_texto(r) for _, r in df_visita.head(5).iterrows()]
    h2h_res = [armar_texto(r) for _, r in df_h2h.iterrows()]

    def pct(df_calc, condicion):
        return round(len(df_calc[condicion]) / len(df_calc) * 100, 1) if len(df_calc) > 0 else 0

    clean_sheet_l = pct(df_local, df_local.get('goles_contra', pd.Series(dtype=float)) == 0)
    sin_marcar_l = pct(df_local, df_local.get('goles_p', pd.Series(dtype=float)) == 0)
    clean_sheet_v = pct(df_visita, df_visita.get('goles_contra', pd.Series(dtype=float)) == 0)
    sin_marcar_v = pct(df_visita, df_visita.get('goles_p', pd.Series(dtype=float)) == 0)

    # --- 4. MOTOR ESTADÍSTICO ---
    datos_estadisticos = {
        'equipo_local': equipo_local,
        'equipo_visitante': equipo_visitante,
        'equipo': f"{equipo_local} vs {equipo_visitante}",
        'partidos_analizados': total_partidos,

        'arbitro_asignado': arbitro_vivo,
        'promedio_arbitro': promedio_arbitro,
        'stats_arbitro': stats_arbitro,
        'formacion_local': formacion_local,
        'formacion_visita': formacion_visita,

        'racha_local': racha_local_str,
        'racha_visita': racha_visita_str,
        'pts_local': pts_local,
        'pts_visita': pts_visita,
        'patrones_h2h': patrones_h2h,

        'prom_goles_m': prom_goles_m,
        'prom_corners_m': prom_corners_m,
        'prom_tarjetas_m': prom_tarjetas_m,
        'prom_cor_contra_l': prom_cor_contra_l,
        'prom_cor_contra_v': prom_cor_contra_v,

        'cor_1': cor_1,
        'cor_x': cor_x,
        'cor_2': cor_2,

        'clean_sheet_l': clean_sheet_l,
        'sin_marcar_l': sin_marcar_l,
        'clean_sheet_v': clean_sheet_v,
        'sin_marcar_v': sin_marcar_v,

        'over_0_5': pct(df_combinado, df_combinado['goles_totales'] > 0.5),
        'over_1_5': pct(df_combinado, df_combinado['goles_totales'] > 1.5),
        'over_2_5': pct(df_combinado, df_combinado['goles_totales'] > 2.5),
        'over_3_5': pct(df_combinado, df_combinado['goles_totales'] > 3.5),
        'over_4_5': pct(df_combinado, df_combinado['goles_totales'] > 4.5),
        'over_5_5': pct(df_combinado, df_combinado['goles_totales'] > 5.5),

        'under_0_5': pct(df_combinado, df_combinado['goles_totales'] < 0.5),
        'under_1_5': pct(df_combinado, df_combinado['goles_totales'] < 1.5),
        'under_2_5': pct(df_combinado, df_combinado['goles_totales'] < 2.5),
        'under_3_5': pct(df_combinado, df_combinado['goles_totales'] < 3.5),
        'under_4_5': pct(df_combinado, df_combinado['goles_totales'] < 4.5),
        'under_5_5': pct(df_combinado, df_combinado['goles_totales'] < 5.5),

        'over_4_5_c': pct(df_combinado, df_combinado['corners_totales'] > 4.5),
        'over_5_5_c': pct(df_combinado, df_combinado['corners_totales'] > 5.5),
        'over_6_5_c': pct(df_combinado, df_combinado['corners_totales'] > 6.5),
        'over_7_5_c': pct(df_combinado, df_combinado['corners_totales'] > 7.5),
        'over_8_5_c': pct(df_combinado, df_combinado['corners_totales'] > 8.5),
        'over_9_5_c': pct(df_combinado, df_combinado['corners_totales'] > 9.5),
        'over_10_5_c': pct(df_combinado, df_combinado['corners_totales'] > 10.5),
        'over_11_5_c': pct(df_combinado, df_combinado['corners_totales'] > 11.5),
        'over_12_5_c': pct(df_combinado, df_combinado['corners_totales'] > 12.5),
        'over_13_5_c': pct(df_combinado, df_combinado['corners_totales'] > 13.5),
        'over_14_5_c': pct(df_combinado, df_combinado['corners_totales'] > 14.5),

        'under_4_5_c': pct(df_combinado, df_combinado['corners_totales'] < 4.5),
        'under_5_5_c': pct(df_combinado, df_combinado['corners_totales'] < 5.5),
        'under_6_5_c': pct(df_combinado, df_combinado['corners_totales'] < 6.5),
        'under_7_5_c': pct(df_combinado, df_combinado['corners_totales'] < 7.5),
        'under_8_5_c': pct(df_combinado, df_combinado['corners_totales'] < 8.5),
        'under_9_5_c': pct(df_combinado, df_combinado['corners_totales'] < 9.5),
        'under_10_5_c': pct(df_combinado, df_combinado['corners_totales'] < 10.5),
        'under_11_5_c': pct(df_combinado, df_combinado['corners_totales'] < 11.5),
        'under_12_5_c': pct(df_combinado, df_combinado['corners_totales'] < 12.5),
        'under_13_5_c': pct(df_combinado, df_combinado['corners_totales'] < 13.5),
        'under_14_5_c': pct(df_combinado, df_combinado['corners_totales'] < 14.5),

        't_over_0_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 0.5),
        't_over_1_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 1.5),
        't_over_2_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 2.5),
        't_over_3_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 3.5),
        't_over_4_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 4.5),
        't_over_5_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 5.5),
        't_over_6_5': pct(df_combinado, df_combinado['tarjetas_totales'] > 6.5),

        'l_cor_0_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 0.5),
        'l_cor_1_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 1.5),
        'l_cor_2_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 2.5),
        'l_cor_3_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 3.5),
        'l_cor_4_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 4.5),
        'l_cor_5_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 5.5),
        'l_cor_6_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) > 6.5),

        'l_cor_u_0_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 0.5),
        'l_cor_u_1_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 1.5),
        'l_cor_u_2_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 2.5),
        'l_cor_u_3_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 3.5),
        'l_cor_u_4_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 4.5),
        'l_cor_u_5_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 5.5),
        'l_cor_u_6_5': pct(df_local, df_local.get('corners_p', pd.Series(dtype=float)) < 6.5),

        'v_cor_0_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 0.5),
        'v_cor_1_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 1.5),
        'v_cor_2_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 2.5),
        'v_cor_3_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 3.5),
        'v_cor_4_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 4.5),
        'v_cor_5_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 5.5),
        'v_cor_6_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) > 6.5),

        'v_cor_u_0_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 0.5),
        'v_cor_u_1_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 1.5),
        'v_cor_u_2_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 2.5),
        'v_cor_u_3_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 3.5),
        'v_cor_u_4_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 4.5),
        'v_cor_u_5_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 5.5),
        'v_cor_u_6_5': pct(df_visita, df_visita.get('corners_p', pd.Series(dtype=float)) < 6.5),

        'l_tar_0_5': pct(df_local, df_local.get('tarjetas_p', pd.Series(dtype=float)) > 0.5),
        'l_tar_1_5': pct(df_local, df_local.get('tarjetas_p', pd.Series(dtype=float)) > 1.5),
        'l_tar_2_5': pct(df_local, df_local.get('tarjetas_p', pd.Series(dtype=float)) > 2.5),
        'l_tar_3_5': pct(df_local, df_local.get('tarjetas_p', pd.Series(dtype=float)) > 3.5),

        'v_tar_0_5': pct(df_visita, df_visita.get('tarjetas_p', pd.Series(dtype=float)) > 0.5),
        'v_tar_1_5': pct(df_visita, df_visita.get('tarjetas_p', pd.Series(dtype=float)) > 1.5),
        'v_tar_2_5': pct(df_visita, df_visita.get('tarjetas_p', pd.Series(dtype=float)) > 2.5),
        'v_tar_3_5': pct(df_visita, df_visita.get('tarjetas_p', pd.Series(dtype=float)) > 3.5),

        'btts_si': pct(df_combinado, (df_combinado['goles_local'] > 0) & (df_combinado['goles_visitante'] > 0)),
        'victoria_local': pct(df_combinado, df_combinado['goles_local'] > df_combinado['goles_visitante']),
        'empate': pct(df_combinado, df_combinado['goles_local'] == df_combinado['goles_visitante']),
        'victoria_visita': pct(df_combinado, df_combinado['goles_local'] < df_combinado['goles_visitante']),
        'doble_1x': pct(df_combinado, df_combinado['goles_local'] >= df_combinado['goles_visitante']),
        'doble_x2': pct(df_combinado, df_combinado['goles_local'] <= df_combinado['goles_visitante']),

        'l_gol_0_5': pct(df_local, df_local.get('goles_p', pd.Series(dtype=float)) > 0.5),
        'l_gol_1_5': pct(df_local, df_local.get('goles_p', pd.Series(dtype=float)) > 1.5),
        'l_gol_2_5': pct(df_local, df_local.get('goles_p', pd.Series(dtype=float)) > 2.5),
        'l_gol_3_5': pct(df_local, df_local.get('goles_p', pd.Series(dtype=float)) > 3.5),
        'l_gol_4_5': pct(df_local, df_local.get('goles_p', pd.Series(dtype=float)) > 4.5),

        'v_gol_0_5': pct(df_visita, df_visita.get('goles_p', pd.Series(dtype=float)) > 0.5),
        'v_gol_1_5': pct(df_visita, df_visita.get('goles_p', pd.Series(dtype=float)) > 1.5),
        'v_gol_2_5': pct(df_visita, df_visita.get('goles_p', pd.Series(dtype=float)) > 2.5),
        'v_gol_3_5': pct(df_visita, df_visita.get('goles_p', pd.Series(dtype=float)) > 3.5),
        'v_gol_4_5': pct(df_visita, df_visita.get('goles_p', pd.Series(dtype=float)) > 4.5),

        'h2h_btts': pct(df_h2h, (df_h2h['goles_local'] > 0) & (df_h2h['goles_visitante'] > 0)) if not df_h2h.empty else 0,
        'h2h_resultados': h2h_res,
        'ultimos_local': ultimos_local,
        'ultimos_visita': ultimos_visita
    }

    # --- 5. GENERADOR DE COMBINADAS AUTOMÁTICAS (3 TICKETS) ---
    mercados = [
        ("Más de 1.5 Goles Totales", datos_estadisticos.get('over_1_5', 0), "goles_tot"),
        ("Más de 2.5 Goles Totales", datos_estadisticos.get('over_2_5', 0), "goles_tot"),
        ("Ambos Marcan (Sí)", datos_estadisticos.get('btts_si', 0), "btts"),
        (f"{equipo_local} o Empate (1X)", datos_estadisticos.get('doble_1x', 0), "resultado"),
        (f"{equipo_visitante} o Empate (X2)", datos_estadisticos.get('doble_x2', 0), "resultado"),
        (f"Anota +0.5 Goles {equipo_local}", datos_estadisticos.get('l_gol_0_5', 0), "gol_L"),
        (f"Anota +1.5 Goles {equipo_local}", datos_estadisticos.get('l_gol_1_5', 0), "gol_L"),
        (f"Anota +0.5 Goles {equipo_visitante}", datos_estadisticos.get('v_gol_0_5', 0), "gol_V"),
        (f"Anota +1.5 Goles {equipo_visitante}", datos_estadisticos.get('v_gol_1_5', 0), "gol_V"),

        ("+5.5 Córneres Totales", datos_estadisticos.get('over_5_5_c', 0), "cor_tot"),
        ("+6.5 Córneres Totales", datos_estadisticos.get('over_6_5_c', 0), "cor_tot"),
        ("+7.5 Córneres Totales", datos_estadisticos.get('over_7_5_c', 0), "cor_tot"),
        ("+8.5 Córneres Totales", datos_estadisticos.get('over_8_5_c', 0), "cor_tot"),
        ("+9.5 Córneres Totales", datos_estadisticos.get('over_9_5_c', 0), "cor_tot"),
        ("+10.5 Córneres Totales", datos_estadisticos.get('over_10_5_c', 0), "cor_tot"),
        ("+11.5 Córneres Totales", datos_estadisticos.get('over_11_5_c', 0), "cor_tot"),

        (f"+3.5 Córneres {equipo_local}", datos_estadisticos.get('l_cor_3_5', 0), "cor_L"),
        (f"+4.5 Córneres {equipo_local}", datos_estadisticos.get('l_cor_4_5', 0), "cor_L"),
        (f"+3.5 Córneres {equipo_visitante}", datos_estadisticos.get('v_cor_3_5', 0), "cor_V"),
        (f"+4.5 Córneres {equipo_visitante}", datos_estadisticos.get('v_cor_4_5', 0), "cor_V"),

        ("+2.5 Tarjetas Totales", datos_estadisticos.get('t_over_2_5', 0), "tar_tot"),
        ("+3.5 Tarjetas Totales", datos_estadisticos.get('t_over_3_5', 0), "tar_tot"),
        ("+4.5 Tarjetas Totales", datos_estadisticos.get('t_over_4_5', 0), "tar_tot"),
        (f"+1.5 Tarjetas {equipo_local}", datos_estadisticos.get('l_tar_1_5', 0), "tar_L"),
        (f"+1.5 Tarjetas {equipo_visitante}", datos_estadisticos.get('v_tar_1_5', 0), "tar_V")
    ]

    mercados_validos = [m for m in mercados if m[1] >= 50]
    mercados_validos.sort(key=lambda x: x[1], reverse=True)

    def armar_ticket(candidatos, max_picks=3, excluir_nombres=set()):
        ticket = []
        categorias_usadas = set()
        for nom, prob, cat in candidatos:
            if nom not in excluir_nombres and cat not in categorias_usadas:
                ticket.append((nom, prob))
                categorias_usadas.add(cat)
                if len(ticket) == max_picks:
                    break
        return ticket

    combinadas = []

    candidatos_t1 = [m for m in mercados_validos if m[1] >= 65]
    ticket_1 = armar_ticket(candidatos_t1, max_picks=3)
    if len(ticket_1) < 3:
        ticket_1 = armar_ticket(mercados_validos, max_picks=3)

    if len(ticket_1) >= 3:
        combinadas.append({
            "titulo": "🔥 Bet Builder Principal (+65% Certeza)",
            "picks": ticket_1
        })

    usados_t1 = {p[0] for p in ticket_1}

    candidatos_t2 = [m for m in mercados_validos if m[0] not in usados_t1 and m[1] >= 55]
    ticket_2 = armar_ticket(candidatos_t2, max_picks=3)
    if len(ticket_2) < 3:
        ticket_2 = armar_ticket([m for m in mercados_validos if m[0] not in usados_t1], max_picks=3)

    if len(ticket_2) >= 3:
        combinadas.append({
            "titulo": "💎 Picks de Valor (Equilibrada)",
            "picks": ticket_2
        })

    candidatos_sonadora = sorted(mercados_validos, key=lambda x: (abs(x[1] - 62), -x[1]))
    ticket_3 = armar_ticket(candidatos_sonadora, max_picks=4)
    if len(ticket_3) < 4:
        ticket_3 = armar_ticket(mercados_validos, max_picks=4)

    if len(ticket_3) >= 3:
        combinadas.append({
            "titulo": "🚀 La Soñadora (Cuota Alta / 4 Opciones)",
            "picks": ticket_3
        })

    datos_estadisticos['combinadas'] = combinadas

    return render_template('analisis.html', datos=datos_estadisticos)

# ==============================================================================
# ENDPOINT SEGURO: CHATBOT ASISTENTE DEPORTIVO CON LECTURA DE BD
# ==============================================================================
@app.route('/api/chat_ia', methods=['POST'])
def chat_ia():
    try:
        data = request.get_json(force=True) or {}
        pregunta = data.get('mensaje', '').strip()
        contexto_pantalla = data.get('contexto', 'general')
        partido_info = data.get('partido_data', {})
        cartelera_hoy = data.get('cartelera_hoy', [])

        if not pregunta:
            return jsonify({'respuesta': '¡Hola! Escríbeme cualquier consulta sobre los partidos de hoy.'})

        texto_partidos = ""
        if cartelera_hoy:
            texto_partidos = "\nPARTIDOS EN PANTALLA HOY:\n- " + "\n- ".join(cartelera_hoy)
        elif partido_info and partido_info.get('local'):
            texto_partidos = f"\nPARTIDO ACTUAL EN PANTALLA: {partido_info.get('local')} vs {partido_info.get('visitante')}"

        prompt_sistema = f"""
        Eres un Asistente y Analista Cuantitativo de apuestas deportivas. Hablas con el usuario de manera natural, humana, directa y relajada.

        {texto_partidos}

        REGLAS CLAVE DE COMPORTAMIENTO:
        1. RESPONDE ESTRICTAMENTE A LO QUE TE PREGUNTAN (NO TE ADELANTES):
           - Si el usuario solo SALUDA (ej: "Hola", "Buenas", "¿qué tal?"): Limítate a devolver el saludo en una sola línea amable y preguntar qué partido o mercado de hoy quiere revisar. PROHIBIDO dar listas de apuestas o combinadas si no te las han pedido.
           - Si pregunta por un PARTIDO O TEMA CONCRETO (ej: "¿cómo ves el Getafe vs Málaga?", "¿algún árbitro tarjetero?"): Responde únicamente a esa consulta de forma concisa.
           - Si y SOLO SI pide RECOMENDACIONES O COMBINADAS (ej: "¿a qué apuesto hoy?", "¿qué combinada me recomiendas?"): Proporciona 2 o 3 selecciones justificadas usando EXCLUSIVAMENTE los partidos en pantalla de hoy.
        2. TONO NATURAL Y CERO TEXTOS ROBÓTICOS:
           - No te presentes con frases cliché como "Como tu Asistente Cuantitativo analizo la cartelera...". Habla como un colega analista.
           - Sé breve y claro (respuestas concisas de 1 a 2 párrafos como máximo).
        3. FORMATO LIMPIO:
           - No uses símbolos como '###' o '---'.
           - Si mencionas apuestas o cuotas, usa negritas para que se vean destacadas.

        MENSAJE DEL USUARIO:
        {pregunta}
        """

        response = modelo_ia.generate_content(prompt_sistema)
        return jsonify({'respuesta': response.text})

    except Exception as err:
        print(f"Error en /api/chat_ia: {err}")
        return jsonify({'respuesta': f"Aviso del asistente: {str(err)}"})



# ==========================================
# ENDPOINT EN VIVO CON PROTECCIÓN DE CUOTA DIARIA
# ==========================================
import time
from datetime import datetime

cache_en_vivo = {
    'ultima_actualizacion': 0,
    'datos': []
}

@app.route('/api/en-vivo')
def api_en_vivo():
    ahora = time.time()
    
    # 1. Micro-caché de 120 segundos (Ahorro estricto)
    if ahora - cache_en_vivo['ultima_actualizacion'] < 120 and cache_en_vivo['datos']:
        return jsonify({'origen': 'cache', 'partidos': cache_en_vivo['datos']})

    try:
        # Verificar si hay partidos de hoy que puedan estar jugándose
        conn = sqlite3.connect('apuestas_master.db')
        cur = conn.cursor()
        
        # Si la base de datos no tiene partidos programados para hoy, no gastar API
        cur.execute("SELECT COUNT(*) FROM Partidos_Cache_Diario WHERE estado NOT IN ('FT', 'AET', 'PEN')")
        pendientes = cur.fetchone()[0]
        
        if pendientes == 0:
            conn.close()
            return jsonify({'origen': 'sin_partidos_activos', 'partidos': []})

        headers_api = {"x-apisports-key": "77f9132f21d5664ba6f556d8d42893dd"}
        url = "https://sportapi7.p.rapidapi.com/fixtures?live=all"
        res = requests.get(url, headers=headers_api, timeout=6).json()

        # Si la API reporta suspensión o error, responder sin romper
        if 'errors' in res and res['errors']:
            conn.close()
            return jsonify({'origen': 'error_api', 'partidos': cache_en_vivo['datos']})

        ligas_permitidas = {71, 39, 140, 135, 78, 61, 2}
        vivos = []

        for p in res.get('response', []):
            lid = p.get('league', {}).get('id')
            if lid in ligas_permitidas:
                fid = p['fixture']['id']
                gl = p['goals'].get('home', 0)
                gv = p['goals'].get('away', 0)
                minuto = p['fixture']['status'].get('elapsed', 0)
                estado = p['fixture']['status'].get('short', '1H')

                vivos.append({
                    'id': fid,
                    'minuto': minuto,
                    'estado': estado,
                    'goles_local': gl if gl is not None else 0,
                    'goles_visita': gv if gv is not None else 0
                })

                cur.execute("""
                    UPDATE Partidos_Cache_Diario
                    SET goles_local = ?, goles_visita = ?, estado = ?
                    WHERE fixture_id = ?
                """, (gl, gv, estado, fid))

        conn.commit()
        conn.close()

        cache_en_vivo['ultima_actualizacion'] = ahora
        cache_en_vivo['datos'] = vivos
        return jsonify({'origen': 'api', 'partidos': vivos})

    except Exception as e:
        return jsonify({'error': str(e), 'partidos': cache_en_vivo['datos']})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)