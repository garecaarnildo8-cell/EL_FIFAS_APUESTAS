import requests
import sqlite3
from datetime import datetime, timedelta

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

conn = sqlite3.connect('apuestas_master.db')
cur = conn.cursor()

# Asegurar que la tabla existe
cur.execute('''
    CREATE TABLE IF NOT EXISTS Partidos_Cache_Diario (
        fixture_id INTEGER PRIMARY KEY,
        league_id INTEGER,
        fecha TEXT,
        local TEXT,
        visitante TEXT,
        arbitro TEXT,
        estado TEXT,
        goles_local INTEGER,
        goles_visita INTEGER
    )
''')

# Limpiar cache anterior
cur.execute('DELETE FROM Partidos_Cache_Diario')

fechas = [
    (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
    datetime.now().strftime('%Y-%m-%d'),
    (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
]

total_partidos = 0
for f in fechas:
    url = f"https://sportapi7.p.rapidapi.com/api/v1/events/date/{f}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"📅 Fecha {f} -> Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            matches = data.get('events', [])
            print(f"   ⚽ Encontrados {len(matches)} partidos.")
            for m in matches:
                fid = m.get('eventId')
                fecha_partido = m.get('startTimestamp', '')
                estado = m.get('status', {}).get('type', 'notstarted')
                loc = m.get('homeTeam', {}).get('name', 'Local')
                vis = m.get('awayTeam', {}).get('name', 'Visitante')
                gl = m.get('homeScore', {}).get('current', 0) or 0
                gv = m.get('awayScore', {}).get('current', 0) or 0
                arbitro = m.get('referee', {}).get('name', 'Por designar')
                lid = m.get('tournament', {}).get('uniqueTournamentId', 0)
                
                cur.execute('''
                    INSERT OR REPLACE INTO Partidos_Cache_Diario 
                    (fixture_id, league_id, fecha, local, visitante, arbitro, estado, goles_local, goles_visita)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fid, lid, str(fecha_partido), loc, vis, arbitro, estado, gl, gv))
                total_partidos += 1
    except Exception as e:
        print(f"❌ Error en fecha {f}: {e}")

conn.commit()
conn.close()
print(f"🚀 ¡Listo! Sincronización finalizada. Total partidos guardados: {total_partidos}")
