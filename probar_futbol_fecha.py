import requests
from datetime import datetime

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

hoy = datetime.now().strftime('%Y-%m-%d')
rutas_futbol = [
    f"/api/v1/sport/football/scheduled-events/date/{hoy}",
    f"/api/v1/sport/1/scheduled-events/date/{hoy}",
    f"/api/v1/football/events/date/{hoy}",
    f"/api/v1/sport/football/events/date/{hoy}"
]

for ruta in rutas_futbol:
    url = f"https://sportapi7.p.rapidapi.com{ruta}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"Ruta: {ruta} -> Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            eventos = data.get('events', [])
            print(f"   ¡ÉXITO! Encontrados {len(eventos)} partidos de fútbol.")
            if eventos:
                m = eventos[0]
                print(f"   Ejemplo: {m.get('homeTeam', {}).get('name')} vs {m.get('awayTeam', {}).get('name')}")
    except Exception as e:
        print(f"Error en {ruta}: {e}")
