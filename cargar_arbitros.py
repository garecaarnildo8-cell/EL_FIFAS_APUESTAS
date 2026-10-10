import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
import urllib.parse

DB_PATH = 'apuestas_master.db'

def inicializar_tabla():
    """Crea la tabla de respaldo si no existe en la BD."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Arbitros_Historico (
            nombre_arbitro TEXT PRIMARY KEY,
            partidos INTEGER,
            promedio REAL,
            perfil TEXT,
            over_3_5_pct REAL,
            over_4_5_pct REAL,
            over_5_5_pct REAL
        )
    """)
    con.commit()
    con.close()

def scrapear_arbitro_transfermarkt(nombre_busqueda):
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    query = urllib.parse.quote(nombre_busqueda.strip())
    url_busqueda = f"https://www.transfermarkt.es/schnellsuche/ergebnis/schnellsuche?query={query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        print(f"🔍 Buscando '{nombre_busqueda}' en Transfermarkt...")
        res = scraper.get(url_busqueda, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"❌ Error de conexión (Status: {res.status_code}).")
            return None

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Busca cualquier enlace que apunte a la ficha de un árbitro
        link_arb = None
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if 'schiedsrichter' in href and ('profil' in href or 'bilanz' in href):
                link_arb = a
                break

        if not link_arb:
            print(f"⚠️ No se encontró ficha de árbitro para '{nombre_busqueda}'.")
            return None

        # Si el enlace es relativo, se arma la URL completa
        href_limpio = link_arb['href']
        url_perfil = href_limpio if href_limpio.startswith('http') else "https://www.transfermarkt.es" + href_limpio
        
        # Forzar la pestaña de balance/rendimiento total
        if '/profil/' in url_perfil:
            url_perfil = url_perfil.replace('/profil/', '/bilanz/')

        nombre_oficial = link_arb.text.strip() or nombre_busqueda
        print(f"📄 Árbitro detectado: {nombre_oficial}. Consultando estadísticas...")

        res_perfil = scraper.get(url_perfil, headers=headers, timeout=10)
        soup_p = BeautifulSoup(res_perfil.text, 'html.parser')

        # Buscar la tabla de datos
        tabla = soup_p.find('table', class_='items')
        if not tabla or not tabla.find('tfoot'):
            # Intento en la URL sin modificar si bilanz no tenía la tabla directa
            res_perfil = scraper.get(href_limpio if href_limpio.startswith('http') else "https://www.transfermarkt.es" + href_limpio, headers=headers, timeout=10)
            soup_p = BeautifulSoup(res_perfil.text, 'html.parser')
            tabla = soup_p.find('table', class_='items')

        if not tabla or not tabla.find('tfoot'):
            print("⚠️ No se encontró la tabla de tarjetas en la ficha.")
            return None

        celdas = tabla.find('tfoot').find_all('td')
        if len(celdas) < 6:
            print("⚠️ Estructura de tabla inesperada.")
            return None

        # Extracción numérica: partidos, amarillas, dobles y rojas
        pj = int(celdas[2].text.strip().replace('.', '') or 0)
        amarillas = int(celdas[3].text.strip().replace('.', '') or 0)
        doble_ama = int(celdas[4].text.strip().replace('.', '') or 0)
        rojas = int(celdas[5].text.strip().replace('.', '') or 0)

        if pj == 0:
            print("⚠️ Registra 0 partidos oficiales.")
            return None

        tot_tarjetas = amarillas + doble_ama + rojas
        promedio = round(tot_tarjetas / pj, 1)

        if promedio >= 5.3:
            perfil = "🔴 Muy Tarjetero"
        elif promedio >= 4.2:
            perfil = "🟡 Rigor Medio"
        else:
            perfil = "🟢 Permisivo"

        o35 = min(round(promedio * 16.5, 1), 95.0)
        o45 = min(round(promedio * 11.5, 1), 85.0)
        o55 = min(round(promedio * 6.5, 1), 70.0)

        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO Arbitros_Historico 
            (nombre_arbitro, partidos, promedio, perfil, over_3_5_pct, over_4_5_pct, over_5_5_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre_oficial, pj, promedio, perfil, o35, o45, o55))
        con.commit()
        con.close()

        print(f"✅ ¡Guardado con éxito en SQLite!")
        print(f"   👤 Árbitro: {nombre_oficial}")
        print(f"   📊 Partidos: {pj} | Promedio: {promedio} tarj/partido ({perfil})")
        print(f"   🟨 +3.5: {o35}% | +4.5: {o45}% | +5.5: {o55}%\n")
        return True

    except Exception as e:
        print(f"❌ Error durante el scraping: {e}")
        return None
    
if __name__ == '__main__':
    inicializar_tabla()
    print("=====================================================")
    print("  GESTOR AUTOMÁTICO DE ÁRBITROS (TRANSFERMARKT / BD) ")
    print("=====================================================\n")

    while True:
        nombre = input("Escribe el apellido o nombre del árbitro (o 'salir' para terminar): ").strip()
        if nombre.lower() in ('salir', 'exit', 'q', ''):
            print("Finalizado.")
            break
        
        scrapear_arbitro_transfermarkt(nombre)