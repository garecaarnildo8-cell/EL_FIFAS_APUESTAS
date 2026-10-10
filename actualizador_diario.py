import requests
import sqlite3
import datetime
import time

API_KEY = "17dc7a0d544831508ca0fc9e42a4e95c"
HEADERS = {"x-apisports-key": API_KEY}
DB_PATH = "/home/Arnildo/app_apuestas/apuestas_master.db"

# Ligas europeas oficiales en la API
LIGAS_EUROPA = [
    {"id": 39, "nombre": "Premier League"},
    {"id": 140, "nombre": "La Liga"},
    {"id": 61, "nombre": "Ligue 1"}
]

ayer = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando actualización de Europa para la fecha: {ayer}")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

url_fixtures = "https://v3.football.api-sports.io/fixtures"
total_guardados = 0

for liga in LIGAS_EUROPA:
    params = {
        "league": liga["id"],
        "date": ayer,
        "status": "FT"
    }
    
    try:
        res = requests.get(url_fixtures, headers=HEADERS, params=params, timeout=10).json()
        partidos = res.get('response', [])
    except Exception as e:
        print(f"⚠️ Error de conexión en {liga['nombre']}: {e}")
        continue

    for p in partidos:
        fix_id = p['fixture']['id']
        fecha = p['fixture']['date'][:10]
        local = p['teams']['home']['name']
        visita = p['teams']['away']['name']
        gl = p['goals']['home'] or 0
        gv = p['goals']['away'] or 0
        arbitro = p['fixture']['referee'] or "Por definir"

        # Estadísticas oficiales: Córneres y Tarjetas
        url_stats = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fix_id}"
        cl, cv, tl, tv = 0, 0, 0, 0
        
        try:
            res_stats = requests.get(url_stats, headers=HEADERS, timeout=10).json().get('response', [])
            if len(res_stats) >= 2:
                for s in res_stats[0].get('statistics', []):
                    if s['type'] == 'Corner Kicks': cl = int(s['value'] or 0)
                    if s['type'] == 'Yellow Cards': tl += int(s['value'] or 0)
                    if s['type'] == 'Red Cards': tl += int(s['value'] or 0)

                for s in res_stats[1].get('statistics', []):
                    if s['type'] == 'Corner Kicks': cv = int(s['value'] or 0)
                    if s['type'] == 'Yellow Cards': tv += int(s['value'] or 0)
                    if s['type'] == 'Red Cards': tv += int(s['value'] or 0)
        except Exception:
            pass

        cur.execute("""
            INSERT OR REPLACE INTO Partidos_Global 
            (fecha, competicion, equipo_local, equipo_visitante, goles_local, goles_visitante, corners_local, corners_visitante, tarjetas_local, tarjetas_visitante, arbitro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fecha, liga["nombre"], local, visita, gl, gv, cl, cv, tl, tv, arbitro))
        
        total_guardados += 1
        print(f"  -> Guardado [{liga['nombre']}]: {local} {gl}-{gv} {visita} | 🚩 {cl+cv} [{cl}-{cv}] | 🟨 {tl+tv}")
        time.sleep(0.3)

con.commit()
con.close()
print(f"✅ Sincronización europea finalizada. Total partidos registrados: {total_guardados}")
