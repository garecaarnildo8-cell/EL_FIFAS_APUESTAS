import requests

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

rutas_prueba = [
    "/api/v1/event/newly-added-events",
    "/api/v1/event/live",
    "/api/v1/event/scheduled",
    "/api/v1/category/to-get-events"
]

for ruta in rutas_prueba:
    url = f"https://sportapi7.p.rapidapi.com{ruta}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"Ruta: {ruta} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("   ¡ÉXITO!", r.text[:120])
    except Exception as e:
        print(f"Error en {ruta}: {e}")
