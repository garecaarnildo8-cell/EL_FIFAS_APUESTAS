import requests

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

rutas = [
    "/api/v1/events/live",
    "/api/v1/football/events/live",
    "/api/v1/sport/1/events/live",
    "/api/v1/events/scheduled",
    "/api/v1/football/matches",
    "/api/v1/match/live"
]

for r in rutas:
    url = f"https://sportapi7.p.rapidapi.com{r}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        print(f"{r} -> Status: {res.status_code}")
        if res.status_code == 200:
            print("   ¡ÉXITO!", res.text[:100])
    except Exception as e:
        print(f"Error {r}: {e}")
