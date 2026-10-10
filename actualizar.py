import re

with open('app.py', 'r', encoding='utf-8') as f:
    codigo = f.read()

# 1. Asegurar importación de timezone
if 'from datetime import datetime, timezone, timedelta' not in codigo:
    codigo = codigo.replace(
        'from datetime import datetime, timedelta',
        'from datetime import datetime, timezone, timedelta'
    )

# 2. Ajuste del corte operativo a las 4:00 AM (Hora de Bolivia)
patron_fechas = r"(\s+)(f_hoy\s*=\s*ahora\.strftime\('%Y-%m-%d'\)[\s\S]*?f_manana\s*=\s*\(ahora\s*\+\s*timedelta\(days=1\)\)\.strftime\('%Y-%m-%d'\))"
reemplazo_fechas = r"""\1# --- CORTE OPERATIVO 4:00 AM (Hora de Bolivia UTC-4) ---
\1ahora_utc = datetime.now(timezone.utc)
\1ahora_op = ahora_utc - timedelta(hours=8) # Resta 4h de zona horaria y 4h de corte operativo
\1f_hoy = ahora_op.strftime('%Y-%m-%d')
\1f_ayer = (ahora_op - timedelta(days=1)).strftime('%Y-%m-%d')
\1f_manana = (ahora_op + timedelta(days=1)).strftime('%Y-%m-%d')"""

codigo = re.sub(patron_fechas, reemplazo_fechas, codigo)

# 3. Reemplazar consultar_api por la versión con persistencia en SQLite
nuevo_consultar_api = '''    # Función para consultar API con Lazy Cache en SQLite (1 sola llamada al día)
    def consultar_api(f_str):
        ligas_permitidas = {
            71: 'Brasileirão',
            39: 'Premier League',
            140: 'La Liga',
            135: 'Serie A',
            78: 'Bundesliga',
            61: 'Ligue 1',
            2: 'Champions League',
            13: 'Copa Libertadores',
            11: 'Copa Sudamericana'
        }
        partidos_db = []
        try:
            conn = sqlite3.connect('apuestas_master.db')
            cur = conn.cursor()
            cur.execute("""
                SELECT fixture_id, fecha, hora, liga, local, visitante,
                       escudo_local, escudo_visita, goles_local, goles_visita, estado, arbitro
                FROM Partidos_Cache_Diario
                WHERE fecha = ?
                ORDER BY hora ASC
            """, (f_str,))
            filas = cur.fetchall()
            for r in filas:
                partidos_db.append({
                    'id': r[0],
                    'fecha': r[1],
                    'hora': r[2],
                    'liga': r[3],
                    'local': r[4],
                    'visitante': r[5],
                    'escudo_local': r[6],
                    'escudo_visita': r[7],
                    'goles_local': r[8] if r[8] is not None else '-',
                    'goles_visita': r[9] if r[9] is not None else '-',
                    'estado': r[10] if r[10] else 'NS',
                    'arbitro': r[11] if r[11] else 'Por definir'
                })
            conn.close()
        except Exception as e:
            print(f"Error leyendo Partidos_Cache_Diario: {e}")

        if partidos_db:
            return partidos_db

        filtrados = []
        try:
            headers_api = {"x-apisports-key": "493be22fc21770a4eecbd29cfdd934cc"}
            url = "https://v3.football.api-sports.io/fixtures"
            params = {"date": f_str, "timezone": "America/La_Paz"}
            res = requests.get(url, headers=headers_api, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json().get('response', [])
                conn = sqlite3.connect('apuestas_master.db')
                cur = conn.cursor()
                for p in data:
                    lid = p.get('league', {}).get('id')
                    if lid in ligas_permitidas:
                        fid = p['fixture']['id']
                        fch = p['fixture']['date'][:10]
                        hra = p['fixture']['date'][11:16]
                        lga = ligas_permitidas[lid]
                        loc = p['teams']['home']['name']
                        vis = p['teams']['away']['name']
                        esc_l = p['teams']['home'].get('logo', '')
                        esc_v = p['teams']['away'].get('logo', '')
                        gol_l = p['goals'].get('home')
                        gol_v = p['goals'].get('away')
                        est = p['fixture']['status'].get('short', 'NS')
                        arb = p['fixture'].get('referee') or 'Por definir'

                        cur.execute("""
                            INSERT OR REPLACE INTO Partidos_Cache_Diario (
                                fixture_id, fecha, hora, liga, local, visitante,
                                escudo_local, escudo_visita, goles_local, goles_visita, estado, arbitro
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fid, fch, hra, lga, loc, vis, esc_l, esc_v, gol_l, gol_v, est, arb))

                        filtrados.append({
                            'id': fid,
                            'fecha': fch,
                            'hora': hra,
                            'liga': lga,
                            'local': loc,
                            'visitante': vis,
                            'escudo_local': esc_l,
                            'escudo_visita': esc_v,
                            'goles_local': gol_l if gol_l is not None else '-',
                            'goles_visita': gol_v if gol_v is not None else '-',
                            'estado': est,
                            'arbitro': arb
                        })
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Error API {f_str}: {e}")

        return filtrados'''

patron_api = r"    # Función para consultar API con caché[\s\S]*?(?=    # Ruteo según el botón pulsado)"
codigo = re.sub(patron_api, nuevo_consultar_api + '\n\n', codigo)

# 4. Modificar la llamada en vivo de analizar_partido para usar SQLite y ventana de 40 min
patron_llamada_vivo = r"(    # --- 1\. LLAMADA EN VIVO A LA API ---[\s\S]*?formacion_visita = \"Aún no disponible\"\n)"
reemplazo_llamada_vivo = r'''    # --- 1. CAPTURA COMBINADA DE ÁRBITRO Y ALINEACIONES (CON CACHÉ SQLITE) ---
    arbitro_vivo = "Por definir"
    formacion_local = "Aún no disponible"
    formacion_visita = "Aún no disponible"

    if fixture_id:
        try:
            conn_cache = sqlite3.connect('apuestas_master.db')
            cur_cache = conn_cache.cursor()
            
            # Revisar si ya están en Alineaciones_Cache
            cur_cache.execute("SELECT datos_json, arbitro FROM Alineaciones_Cache WHERE fixture_id = ?", (fixture_id,))
            row_ali = cur_cache.fetchone()
            
            # Revisar si el árbitro ya está en Partidos_Cache_Diario
            cur_cache.execute("SELECT hora, arbitro FROM Partidos_Cache_Diario WHERE fixture_id = ?", (fixture_id,))
            row_par = cur_cache.fetchone()
            hora_partido = row_par[0] if row_par else None
            if row_par and row_par[1] and row_par[1] != 'Por definir':
                arbitro_vivo = row_par[1]

            if row_ali and row_ali[0]:
                import json
                datos_ali = json.loads(row_ali[0])
                if len(datos_ali) == 2:
                    formacion_local = datos_ali[0].get('formation', 'Confirmada')
                    formacion_visita = datos_ali[1].get('formation', 'Confirmada')
                if row_ali[1] and row_ali[1] != 'Por definir':
                    arbitro_vivo = row_ali[1]
            else:
                # Comprobar ventana de 40 minutos
                consultar_api_ahora = True
                if hora_partido and ':' in hora_partido:
                    try:
                        ahora_bo = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime('%H:%M')
                        hp, mp = map(int, hora_partido.split(':'))
                        ha, ma = map(int, ahora_bo.split(':'))
                        diff_min = (hp * 60 + mp) - (ha * 60 + ma)
                        if diff_min > 40:
                            consultar_api_ahora = False
                    except Exception:
                        pass

                if consultar_api_ahora:
                    url_vivo = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
                    headers_api = {"x-apisports-key": "493be22fc21770a4eecbd29cfdd934cc"}
                    res_api = requests.get(url_vivo, headers=headers_api, timeout=6).json()
                    if res_api.get('response'):
                        datos_partido = res_api['response'][0]
                        ref = datos_partido.get('fixture', {}).get('referee')
                        if ref:
                            arbitro_vivo = ref
                            cur_cache.execute("UPDATE Partidos_Cache_Diario SET arbitro = ? WHERE fixture_id = ?", (arbitro_vivo, fixture_id))
                        lineups = datos_partido.get('lineups', [])
                        if len(lineups) == 2:
                            formacion_local = lineups[0].get('formation', '4-3-3')
                            formacion_visita = lineups[1].get('formation', '4-3-3')
                            import json
                            cur_cache.execute("""
                                INSERT OR REPLACE INTO Alineaciones_Cache (fixture_id, fecha, datos_json, arbitro)
                                VALUES (?, date('now'), ?, ?)
                            """, (fixture_id, json.dumps(lineups), arbitro_vivo))
                        conn_cache.commit()
            conn_cache.close()
        except Exception as e:
            print(f"Error procesando caché de partido: {e}")
'''

codigo = re.sub(patron_llamada_vivo, reemplazo_llamada_vivo, codigo)

# 5. Reemplazar el scraper externo por el respaldo de la media general de la liga
patron_scraping = r"# 3\. AUTO-APRENDIZAJE: Si no existe en la BD, lo busca en internet y lo guarda[\s\S]*?promedio_arbitro = f\"Promedio: \{datos_web\['promedio'\]\} \(\{datos_web\['perfil'\]\}\) \[Auto-detectado Web\]\""
reemplazo_respaldo = """# 3. RESPALDO: Si no tiene historial, usar la media general de tarjetas de la liga
                    try:
                        cur_arb.execute("SELECT ROUND(AVG(tarjetas_local + tarjetas_visitante), 1) FROM Partidos_Global WHERE tarjetas_local IS NOT NULL")
                        media_liga = cur_arb.fetchone()[0] or 4.3
                    except Exception:
                        media_liga = 4.3
                    perfil_liga = "🟡 Rigor Medio" if media_liga >= 4.2 else ("🔴 Muy Tarjetero" if media_liga >= 5.3 else "🟢 Permisivo")
                    stats_arbitro['partidos'] = "Liga"
                    stats_arbitro['promedio'] = media_liga
                    stats_arbitro['perfil'] = perfil_liga
                    stats_arbitro['over_3_5_pct'] = 65.0
                    stats_arbitro['over_4_5_pct'] = 45.0
                    stats_arbitro['over_5_5_pct'] = 25.0
                    promedio_arbitro = f"Media de la Liga: {media_liga} tarj ({perfil_liga}) [Respaldo General]" """

codigo = re.sub(patron_scraping, reemplazo_respaldo, codigo)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(codigo)

print("🚀 ¡app.py actualizado exitosamente!")
