import requests
import sqlite3
import time

API_KEY = "17dc7a0d544831508ca0fc9e42a4e95c"
HEADERS = {"x-apisports-key": API_KEY}

con = sqlite3.connect('apuestas_master.db')
cur = con.cursor()

# 1. Comprobar partidos de otras ligas
cur.execute("SELECT COUNT(*) FROM Partidos_Global WHERE competicion != 'Brasileirão Série A'")
europeos_antes = cur.fetchone()[0]
print(f"🔒 Partidos de otras ligas intactos en tu BD: {europeos_antes}")

# 2. Eliminar exclusivamente registros vacíos de Brasil
cur.execute("""
    DELETE FROM Partidos_Global 
    WHERE competicion = 'Brasileirão Série A' 
      AND corners_local = 0 
      AND corners_visitante = 0
""")
con.commit()

# 3. Consultar últimos partidos con temporada explícita
url_fixtures = "https://v3.football.api-sports.io/fixtures"
print("🔄 Consultando temporada 2026 de la Série A...")
res = requests.get(url_fixtures, headers=HEADERS, params={"league": 71, "season": 2026, "last": 15}).json()

partidos = res.get('response', [])

# Si la temporada actual aún no tiene suficientes jugados, complementa con la anterior
if len(partidos) < 10:
    print(f"ℹ️ Temporada 2026 devolvió {len(partidos)} partidos. Buscando también recientes de 2025...")
    res_2025 = requests.get(url_fixtures, headers=HEADERS, params={"league": 71, "season": 2025, "last": 15}).json()
    partidos.extend(res_2025.get('response', []))

if res.get('errors') and not partidos:
    print(f"⚠️ Mensaje de la API: {res.get('errors')}")

guardados = 0
for p in partidos:
    if p['fixture']['status']['short'] not in ['FT', 'AET', 'PEN']:
        continue

    fix_id = p['fixture']['id']
    fecha = p['fixture']['date'][:10]
    local = p['teams']['home']['name']
    visita = p['teams']['away']['name']
    gl = p['goals']['home'] or 0
    gv = p['goals']['away'] or 0
    arbitro = p['fixture']['referee'] or "Por definir"

    # Consultar estadísticas oficiales (córneres y tarjetas)
    url_stats = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fix_id}"
    res_stats = requests.get(url_stats, headers=HEADERS).json().get('response', [])

    cl, cv, tl, tv = 0, 0, 0, 0
    if len(res_stats) >= 2:
        for s in res_stats[0].get('statistics', []):
            if s['type'] == 'Corner Kicks': cl = int(s['value'] or 0)
            if s['type'] == 'Yellow Cards': tl += int(s['value'] or 0)
            if s['type'] == 'Red Cards': tl += int(s['value'] or 0)

        for s in res_stats[1].get('statistics', []):
            if s['type'] == 'Corner Kicks': cv = int(s['value'] or 0)
            if s['type'] == 'Yellow Cards': tv += int(s['value'] or 0)
            if s['type'] == 'Red Cards': tv += int(s['value'] or 0)

    cur.execute("""
        INSERT OR REPLACE INTO Partidos_Global 
        (fecha, competicion, equipo_local, equipo_visitante, goles_local, goles_visitante, corners_local, corners_visitante, tarjetas_local, tarjetas_visitante, arbitro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fecha, "Brasileirão Série A", local, visita, gl, gv, cl, cv, tl, tv, arbitro))
    
    guardados += 1
    print(f"⚽ {local} vs {visita} -> 🚩 {cl + cv} [{cl}-{cv}] | 🟨 {tl + tv}")
    time.sleep(0.3)

con.commit()

cur.execute("SELECT COUNT(*) FROM Partidos_Global WHERE competicion != 'Brasileirão Série A'")
europeos_despues = cur.fetchone()[0]
print(f"\n✅ Partidos de otras ligas intactos: {europeos_despues}")
print(f"🎉 Se insertaron {guardados} partidos brasileños con datos completos.")

con.close()
