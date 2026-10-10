import requests

HEADERS = {
    "x-rapidapi-key": "506e1b0bc0mshe4b95bfa9730c57p1d599ajsn5664aa69bdd9",
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

# Usamos el eventId que nos devolvió el endpoint anterior
url_lista = "https://sportapi7.p.rapidapi.com/api/v1/event/newly-added-events"
r = requests.get(url_lista, headers=HEADERS, timeout=5)

if r.status_code == 200:
    eventos = r.status_code and r.json().get('events', [])
    if eventos:
        primer_id = eventos[0].get('eventId')
        print(f"🔍 Consultando detalles para el eventId: {primer_id}")
        
        url_detalle = f"https://sportapi7.p.rapidapi.com/api/v1/event/{primer_id}"
        r_det = requests.get(url_detalle, headers=HEADERS, timeout=5)
        print(f"Status detalle: {r_det.status_code}")
        print("Respuesta:", r_det.text[:300])
    else:
        print("No hay eventos en la lista en este momento.")
else:
    print("Error al obtener la lista de eventos.")
