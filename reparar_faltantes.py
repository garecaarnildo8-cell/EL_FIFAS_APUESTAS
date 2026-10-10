import requests
import sqlite3
import time

API_KEY = "17dc7a0d544831508ca0fc9e42a4e95c"
HEADERS = {"x-apisports-key": API_KEY}
DB_PATH = "/home/Arnildo/app_apuestas/apuestas_master.db"

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Ligas a verificar para la última jornada
LIGAS = [
    {"id": 39, "nombre": "Premier League"},
    {"id": 140, "nombre": "La Liga"},
    {"id": 61, "nombre": "Ligue 1"},
    {"id": 135, "nombre": "Serie A"}
]

fecha_objetivo = "2026-09-20"
url_fixtures = "https://v3.football.api-sports.io/fixtures"

print(f"🔍 Buscando únicamente partidos faltantes o con ceros del {fecha_objetivo}...\n")

for liga in LIGAS:
    params = {"league": liga["id"], "date": fecha_objetivo, "status": "FT"}
    try:
        res = requests.get(url_fixtures, headers=HEADERS, params=params, timeout=10).json()
        partidos = res.get('response', [])
    except Exception as e:
        print(f"⚠️ Error de conexión en {liga['nombre']}: {e}")
        continue

    for p in partidos:
        fix_id = p['fixture']['id']
        local = p['teams']['home']['name']
        visita = p['teams']['away']['name']
        gl = p['goals']['home'] or 0
        gv = p['goals']['away'] or 0
        arbitro = p['fixture']['referee'] or "Por definir"

        # Verificar si ya existe en la base de datos
        # Comparamos con los primeros 5 caracteres para evitar problemas de tildes
        cur.execute("""
            SELECT rowid, corners_local, corners_visitante, tarjetas_local, tarjetas_visitante 
            FROM Partidos_Global 
            WHERE fecha = ? AND (equipo_local LIKE ? OR equipo_local LIKE ?)
        """, (fecha_objetivo, f"%{local[:5]}%", f"%{visita[:5]}%"))
        fila = cur.fetchone()

        # REGLA ESTRICTA: Si ya existe y tiene estadísticas reales, NO SE TOCA
        if fila:
            cl_bd, cv_bd, tl_bd, tv_bd = fila[1], fila[2], fila[3], fila[4]
            if (cl_bd or 0) > 0 or (cv_bd or 0) > 0 or (tl_bd or 0) > 0 or (tv_bd or 0) > 0:
                print(f"⏩ Intacto (no se toca): [{liga['nombre']}] {local} vs {visita}")
                continue
            else:
                print(f"🔄 Actualizando datos faltantes (estaba en 0s): [{liga['nombre']}] {local} vs {visita}")
        else:
            print(f"➕ Reinsertando partido faltante: [{liga['nombre']}] {local} vs {visita}")

        # Consultar estadísticas oficiales en la API
        url_stats = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fix_id}"
        cl, cv, yl, yv, rl, rv = 0, 0, 0, 0, 0, 0
        
        try:
            res_stats = requests.get(url_stats, headers=HEADERS, timeout=10).json().get('response', [])
            if len(res_stats) >= 2:
                for s in res_stats[0].get('statistics', []):
                    if s['type'] == 'Corner Kicks': cl = int(s['value'] or 0)
                    if s['type'] == 'Yellow Cards': yl = int(s['value'] or 0)
                    if s['type'] == 'Red Cards': rl = int(s['value'] or 0)
                for s in res_stats[1].get('statistics', []):
                    if s['type'] == 'Corner Kicks': cv = int(s['value'] or 0)
                    if s['type'] == 'Yellow Cards': yv = int(s['value'] or 0)
                    if s['type'] == 'Red Cards': rv = int(s['value'] or 0)
        except Exception as e:
            print(f"   ⚠️ Error al pedir estadísticas: {e}")

        tl = yl + rl
        tv = yv + rv

        if fila:
            # Actualizar la fila existente que tenía ceros
            cur.execute("""
                UPDATE Partidos_Global 
                SET goles_local = ?, goles_visitante = ?,
                    corners_local = ?, corners_visitante = ?,
                    tarjetas_local = ?, tarjetas_visitante = ?,
                    rojas_local = ?, rojas_visitante = ?,
                    arbitro = ?
                WHERE rowid = ?
            """, (gl, gv, cl, cv, tl, tv, rl, rv, arbitro, fila[0]))
        else:
            # Reinsertar el partido que se había borrado
            cur.execute("""
                INSERT INTO Partidos_Global 
                (fecha, competicion, equipo_local, equipo_visitante, 
                 goles_local, goles_visitante, 
                 corners_local, corners_visitante, 
                 tarjetas_local, tarjetas_visitante, 
                 rojas_local, rojas_visitante, arbitro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fecha_objetivo, liga["nombre"], local, visita, gl, gv, cl, cv, tl, tv, rl, rv, arbitro))

        con.commit()
        print(f"   ✅ Guardado exitoso: {local} {gl}-{gv} {visita} | 🚩 {cl+cv} [{cl}-{cv}] | 🟨 {yl+yv} | 🟥 {rl+rv}")
        time.sleep(0.3)

con.close()
print("\n🎯 Sincronización finalizada sin tocar partidos existentes.")
