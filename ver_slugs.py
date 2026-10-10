import requests

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

url = "https://sportapi7.p.rapidapi.com/api/v1/event/newly-added-events"
r = requests.get(url, headers=HEADERS, timeout=10)

if r.status_code == 200:
    eventos = r.json().get('events', [])
    deportes_encontrados = set()
    
    for ev in eventos[:40]:
        eid = ev.get('eventId')
        try:
            r_det = requests.get(f"https://sportapi7.p.rapidapi.com/api/v1/event/{eid}", headers=HEADERS, timeout=2)
            if r_det.status_code == 200:
                ev_data = r_det.json().get('event', {})
                sport = ev_data.get('tournament', {}).get('category', {}).get('sport', {})
                nombre = sport.get('name')
                slug = sport.get('slug')
                sid = sport.get('id')
                deportes_encontrados.add((nombre, slug, sid))
        except:
            continue
            
    print("📋 Deportes detectados en la API:", deportes_encontrados)
else:
    print("❌ Error al conectar:", r.status_code)
