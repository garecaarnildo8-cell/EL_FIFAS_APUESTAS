import requests
import time

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

url = "https://sportapi7.p.rapidapi.com/api/v1/event/newly-added-events"
print("🔄 Consultando eventos recientes...")
r = requests.get(url, headers=HEADERS, timeout=10)

if r.status_code == 200:
    eventos = r.json().get('events', [])
    print(f"📦 Total eventos disponibles: {len(eventos)}. Analizando una muestra con pausa...")
    
    for ev in eventos[:10]:
        eid = ev.get('eventId')
        try:
            r_det = requests.get(f"https://sportapi7.p.rapidapi.com/api/v1/event/{eid}", headers=HEADERS, timeout=5)
            if r_det.status_code == 200:
                ev_data = r_det.json().get('event', {})
                sport = ev_data.get('tournament', {}).get('category', {}).get('sport', {})
                print(f"ID {eid} -> Deporte: {sport.get('name')} | Slug: {sport.get('slug')} | ID: {sport.get('id')}")
            time.sleep(1) # Pausa de 1 segundo entre peticiones para cuidar el límite
        except Exception as e:
            print(f"Error en {eid}: {e}")
else:
    print(f"❌ Error principal: {r.status_code}. Espera unos segundos e inténtalo de nuevo.")
