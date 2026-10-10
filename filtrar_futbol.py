import requests

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

url = "https://sportapi7.p.rapidapi.com/api/v1/event/newly-added-events"
r = requests.get(url, headers=HEADERS, timeout=5)

if r.status_code == 200:
    data = r.json()
    eventos = data.get('events', [])
    print(f"Total eventos generales: {len(eventos)}")
    
    # Vamos a revisar los primeros 3 eventos detallados para ver su deporte
    for ev in eventos[:5]:
        eid = ev.get('eventId')
        # Consultar detalle del evento
        r_det = requests.get(f"https://sportapi7.p.rapidapi.com/api/v1/event/{eid}", headers=HEADERS, timeout=3)
        if r_det.status_code == 200:
            ev_data = r_det.json().get('event', {})
            deporte = ev_data.get('tournament', {}).get('category', {}).get('sport', {}).get('slug')
            nombre_torneo = ev_data.get('tournament', {}).get('name')
            loc = ev_data.get('homeTeam', {}).get('name')
            vis = ev_data.get('awayTeam', {}).get('name')
            print(f"ID: {eid} | Deporte: {deporte} | Torneo: {nombre_torneo} | {loc} vs {vis}")
else:
    print("Error al conectar con la API.")
