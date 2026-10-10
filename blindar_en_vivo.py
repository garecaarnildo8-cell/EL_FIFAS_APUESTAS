with open('app.py', 'r', encoding='utf-8') as f:
    codigo = f.read()

# Reemplazamos la lógica de api_en_vivo por una versión con ahorro estricto
codigo_nuevo_en_vivo = '''
# ==========================================
# ENDPOINT EN VIVO CON PROTECCIÓN DE CUOTA DIARIA
# ==========================================
import time
from datetime import datetime

cache_en_vivo = {
    'ultima_actualizacion': 0,
    'datos': []
}

@app.route('/api/en-vivo')
def api_en_vivo():
    ahora = time.time()
    
    # 1. Micro-caché de 120 segundos (Ahorro estricto)
    if ahora - cache_en_vivo['ultima_actualizacion'] < 120 and cache_en_vivo['datos']:
        return jsonify({'origen': 'cache', 'partidos': cache_en_vivo['datos']})

    try:
        # Verificar si hay partidos de hoy que puedan estar jugándose
        conn = sqlite3.connect('apuestas_master.db')
        cur = conn.cursor()
        
        # Si la base de datos no tiene partidos programados para hoy, no gastar API
        cur.execute("SELECT COUNT(*) FROM Partidos_Cache_Diario WHERE estado NOT IN ('FT', 'AET', 'PEN')")
        pendientes = cur.fetchone()[0]
        
        if pendientes == 0:
            conn.close()
            return jsonify({'origen': 'sin_partidos_activos', 'partidos': []})

        headers_api = {"x-apisports-key": "493be22fc21770a4eecbd29cfdd934cc"}
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        res = requests.get(url, headers=headers_api, timeout=6).json()

        # Si la API reporta suspensión o error, responder sin romper
        if 'errors' in res and res['errors']:
            conn.close()
            return jsonify({'origen': 'error_api', 'partidos': cache_en_vivo['datos']})

        ligas_permitidas = {71, 39, 140, 135, 78, 61, 2}
        vivos = []

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

# Sustituir la sección anterior
import re
patron = r"# ==========================================\s*# ENDPOINT EN VIVO.*?return jsonify\({'error': str\(e\), 'partidos': cache_en_vivo\['datos'\]}\)"
if re.search(patron, codigo, re.DOTALL):
    codigo = re.sub(patron, codigo_nuevo_en_vivo.strip(), codigo, flags=re.DOTALL)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    print("✅ app.py blindado contra agotamiento de cuota diaria")
else:
    print("ℹ No se encontró el bloque anterior o ya fue modificado.")
