with open('app.py', 'r', encoding='utf-8') as f:
    codigo = f.read()

endpoint_en_vivo = '''
# ==========================================
# ENDPOINT EN VIVO (ESTILO SOFASCORE / FLASHSCORE)
# ==========================================
import time

cache_en_vivo = {
    'ultima_actualizacion': 0,
    'datos': []
}

@app.route('/api/en-vivo')
def api_en_vivo():
    ahora = time.time()
    
    # 1. Micro-caché: Si pasaron menos de 60s, responder desde memoria (0 peticiones a la API)
    if ahora - cache_en_vivo['ultima_actualizacion'] < 60 and cache_en_vivo['datos']:
        return jsonify({'origen': 'cache', 'partidos': cache_en_vivo['datos']})

    try:
        headers_api = {"x-apisports-key": "493be22fc21770a4eecbd29cfdd934cc"}
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        res = requests.get(url, headers=headers_api, timeout=6).json()

        ligas_permitidas = {71, 39, 140, 135, 78, 61, 2}
        vivos = []

        conn = sqlite3.connect('apuestas_master.db')
        cur = conn.cursor()

        for p in res.get('response', []):
            lid = p.get('league', {}).get('id')
            if lid in ligas_permitidas:
                fid = p['fixture']['id']
                gl = p['goals'].get('home', 0)
                gv = p['goals'].get('away', 0)
                minuto = p['fixture']['status'].get('elapsed', 0)
                estado = p['fixture']['status'].get('short', '1H')

                vivos.append({
                    'id': fid,
                    'minuto': minuto,
                    'estado': estado,
                    'goles_local': gl if gl is not None else 0,
                    'goles_visita': gv if gv is not None else 0
                })

                # Actualizar también en la base de datos local
                cur.execute("""
                    UPDATE Partidos_Cache_Diario
                    SET goles_local = ?, goles_visita = ?, estado = ?
                    WHERE fixture_id = ?
                """, (gl, gv, estado, fid))

        conn.commit()
        conn.close()

        cache_en_vivo['ultima_actualizacion'] = ahora
        cache_en_vivo['datos'] = vivos
        return jsonify({'origen': 'api', 'partidos': vivos})

    except Exception as e:
        return jsonify({'error': str(e), 'partidos': cache_en_vivo['datos']})
'''

if '/api/en-vivo' not in codigo:
    # Insertar antes del bloque main
    if "if __name__ == '__main__':" in codigo:
        codigo = codigo.replace("if __name__ == '__main__':", endpoint_en_vivo + "\nif __name__ == '__main__':")
    else:
        codigo += "\n" + endpoint_en_vivo

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    print("✅ Endpoint /api/en-vivo inyectado con éxito en app.py")
else:
    print("ℹ El endpoint /api/en-vivo ya estaba presente.")
