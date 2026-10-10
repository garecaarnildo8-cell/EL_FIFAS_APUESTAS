import requests

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

rutas_config = [
    "/api/v1/sports",
    "/api/v1/sport/football",
    "/api/v1/categories",
    "/api/v1/tournaments"
]

for ruta in rutas_config:
    url = f"https://sportapi7.p.rapidapi.com{ruta}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        print(f"Ruta: {ruta} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("   Respuesta:", r.text[:150])
    except Exception as e:
        print(f"Error en {ruta}: {e}")
