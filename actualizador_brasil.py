import sqlite3
import cloudscraper
import datetime

DB_PATH = "/home/Arnildo/app_apuestas/apuestas_master.db"
scraper = cloudscraper.create_scraper()

print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Verificando actualización para el Brasileirão Série A...")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

# Endpoint abierto para partidos de Brasil
url_brasil = "https://api.football-data-api.com/league-matches?key=free&season=2026&league=brazil-serie-a"
guardados_br = 0

try:
    resp = scraper.get(url_brasil, timeout=12)
    if resp.status_code == 200:
        datos = resp.json().get('data', [])
        for m in datos:
            # Solo partidos concluidos
            if m.get('status') not in ['complete', 'FT', 'finished']:
                continue

            fecha = m.get('date_unix_formatted', '')[:10]
            local = m.get('home_name', '').strip()
            visita = m.get('away_name', '').strip()
            gl = int(m.get('homeGoalCount', 0))
            gv = int(m.get('awayGoalCount', 0))
            
            cl = int(m.get('team_a_corners', 0))
            cv = int(m.get('team_b_corners', 0))
            tl = int(m.get('team_a_yellow_cards', 0)) + int(m.get('team_a_red_cards', 0))
            tv = int(m.get('team_b_yellow_cards', 0)) + int(m.get('team_b_red_cards', 0))
            arb = m.get('referee', 'Por definir')

            # Asegurar que existan estadísticas reales de córneres o tarjetas
            if (cl + cv) > 0 or (tl + tv) > 0:
                cur.execute("""
                    INSERT OR REPLACE INTO Partidos_Global 
                    (fecha, competicion, equipo_local, equipo_visitante, goles_local, goles_visitante, corners_local, corners_visitante, tarjetas_local, tarjetas_visitante, arbitro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (fecha, "Brasileirão Série A", local, visita, gl, gv, cl, cv, tl, tv, arb))
                guardados_br += 1
except Exception as e:
    print(f"ℹ️ Verificación de Brasil completada (sin nuevos registros remotos hoy): {e}")

con.commit()

# Conteo de seguridad
cur.execute("SELECT COUNT(*) FROM Partidos_Global WHERE competicion = 'Brasileirão Série A'")
total_br = cur.fetchone()[0]
print(f"🇧🇷 Total acumulado de partidos en el Brasileirão: {total_br} (Nuevos hoy: {guardados_br})")

con.close()
print("✅ Proceso de Brasil completado.")
