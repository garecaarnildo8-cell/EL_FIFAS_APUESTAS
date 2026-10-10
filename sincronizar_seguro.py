import requests
import sqlite3
import time

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

conn = sqlite3.connect('apuestas_master.db')
cur = conn.cursor()

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
cur.execute('DELETE FROM Partidos_Cache_Diario')

print("🔄 Conectando a SportAPI (modo ultra-seguro anti-429)...")
url = "https://sportapi7.p.rapidapi.com/api/v1/event/newly-added-events"
r = requests.get(url, headers=HEADERS, timeout=10)

guardados = 0
if r.status_code == 200:
    eventos = r.json().get('events', [])
    print(f"📦 Analizando los primeros 15 eventos con pausa de seguridad...")
    
    for ev in eventos[:15]:
        eid = ev.get('eventId')
        try:
            r_det = requests.get(f"https://sportapi7.p.rapidapi.com/api/v1/event/{eid}", headers=HEADERS, timeout=5)
            
            if r_det.status_code == 429:
                print("⚠️ Límite alcanzado temporalmente. Esperando 5 segundos...")
                time.sleep(5)
                continue
                
            if r_det.status_code == 200:
                ev_data = r_det.json().get('event', {})
                sport = ev_data.get('tournament', {}).get('category', {}).get('sport', {}).get('slug', '')
                
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
                    print(f"⚽ Fútbol guardado: {loc} vs {vis}")
                    
            time.sleep(3) # Pausa estricta de 3 segundos para proteger el límite
        except Exception as e:
            continue

    conn.commit()
    print(f"\n🚀 Sincronización exitosa. Partidos de fútbol guardados: {guardados}")
else:
    print(f"❌ Error HTTP {r.status_code}. Espera un momento más e inténtalo de nuevo.")

conn.close()
