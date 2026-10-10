import requests
import sqlite3

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

conn = sqlite3.connect('apuestas_master.db')
cur = conn.cursor()

# Asegurar que la tabla existe con la estructura correcta
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

# Limpiar caché anterior
cur.execute('DELETE FROM Partidos_Cache_Diario')

url = "https://sportapi7.p.rapidapi.com/api/v1/event/newly-added-events"
print("🔄 Consultando eventos recientes en SportAPI...")
r = requests.get(url, headers=HEADERS, timeout=10)

guardados = 0
if r.status_code == 200:
    eventos = r.json().get('events', [])
    print(f"📦 Total de eventos analizados: {len(eventos)}")
    
    for ev in eventos:
        eid = ev.get('eventId')
        # Consultar el detalle individual del evento para verificar el deporte
        try:
            r_det = requests.get(f"https://sportapi7.p.rapidapi.com/api/v1/event/{eid}", headers=HEADERS, timeout=2)
            if r_det.status_code == 200:
                ev_data = r_det.json().get('event', {})
                sport = ev_data.get('tournament', {}).get('category', {}).get('sport', {}).get('slug', '')
                
                # Filtrar estrictamente fútbol
                if sport in ['football', 'soccer']:
                    loc = ev_data.get('homeTeam', {}).get('name', 'Local')
                    vis = ev_data.get('awayTeam', {}).get('name', 'Visitante')
                    estado = ev_data.get('status', {}).get('type', 'notstarted')
                    gl = ev_data.get('homeScore', {}).get('current', 0) or 0
                    gv = ev_data.get('awayScore', {}).get('current', 0) or 0
                    arbitro = ev_data.get('referee', {}).get('name', 'Por designar')
                    lid = ev_data.get('tournament', {}).get('uniqueTournamentId', 0)
                    fecha_p = str(ev_data.get('startTimestamp', ''))
                    
                    cur.execute('''
                        INSERT OR REPLACE INTO Partidos_Cache_Diario 
                        (fixture_id, league_id, fecha, local, visitante, arbitro, estado, goles_local, goles_visita)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (eid, lid, fecha_p, loc, vis, arbitro, estado, gl, gv))
                    guardados += 1
                    print(f"⚽ Partido de Fútbol guardado: {loc} vs {vis}")
        except Exception as e:
            continue

    conn.commit()
    print(f"\n🚀 ¡Sincronización finalizada con éxito! Partidos de fútbol guardados: {guardados}")
else:
    print(f"❌ Error al conectar con la API: {r.status_code}")

conn.close()
