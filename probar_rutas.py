import requests
from datetime import datetime

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

hoy = datetime.now().strftime('%Y-%m-%d')
rutas_prueba = [
    f"/api/v1/events/date/{hoy}",
    f"/api/v1/sport/football/scheduled-events/date/{hoy}",
    f"/api/v1/scheduled-events/date/{hoy}",
    f"/api/v1/matches/date/{hoy}",
    f"/api/v1/events/live"
]

for ruta in rutas_prueba:
    url = f"https://sportapi7.p.rapidapi.com{ruta}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"Ruta: {ruta} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("   ¡ÉXITO! Esta es la ruta correcta.")
    except Exception as e:
        print(f"Error en {ruta}: {e}")
