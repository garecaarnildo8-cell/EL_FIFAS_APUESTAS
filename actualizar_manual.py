# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = "apuestas_master.db"

def pedir_num(label, default=0):
    val = input(f"{label} [{default}]: ").strip()
    return int(val) if val else default

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("\n" + "=" * 50)
    print(" ACTUALIZADOR MANUAL DE PARTIDOS")
    print("=" * 50)

    termino = input("\nIntroduce equipo o fecha a buscar (ej: Real Madrid / City / 2026-09-20): ").strip()
    if not termino:
        print("Operacion cancelada.")
        return

    c.execute("""
        SELECT rowid, fecha, competicion, equipo_local, goles_local, goles_visitante, equipo_visitante,
               corners_local, corners_visitante, tarjetas_local, tarjetas_visitante, rojas_local, rojas_visitante
        FROM Partidos_Global
        WHERE equipo_local LIKE ? OR equipo_visitante LIKE ? OR fecha LIKE ?
        ORDER BY fecha DESC LIMIT 10
    """, (f"%{termino}%", f"%{termino}%", f"%{termino}%"))

    filas = c.fetchall()

    print("\nResultados encontrados:")
    print(" [0] -> Crear un partido NUEVO (si no aparece en la lista)")
    for i, f in enumerate(filas, 1):
        print(f" [{i}] ID {f[0]}: [{f[1]}] {f[3]} {f[4]}-{f[5]} {f[6]} | Corners: {f[7]}-{f[8]} | Amarillas: {f[9]}-{f[10]} | Rojas: {f[11]}-{f[12]}")

    opcion = input("\nElige el numero a editar (0 para nuevo, o Enter para salir): ").strip()
    if not opcion:
        return

    opc = int(opcion)

    if opc == 0:
        print("\n--- NUEVO PARTIDO ---")
        fecha = input("Fecha (YYYY-MM-DD): ").strip()
        comp = input("Competicion (ej: La Liga, Premier League, Brasileirao): ").strip()
        local = input("Equipo Local: ").strip()
        visita = input("Equipo Visitante: ").strip()
        gl = pedir_num("Goles Local", 0)
        gv = pedir_num("Goles Visitante", 0)
        cl = pedir_num("Corners Local", 0)
        cv = pedir_num("Corners Visitante", 0)
        tl = pedir_num("Tarjetas Amarillas Local", 0)
        tv = pedir_num("Tarjetas Amarillas Visitante", 0)
        rl = pedir_num("Tarjetas Rojas Local", 0)
        rv = pedir_num("Tarjetas Rojas Visitante", 0)
        arbitro = input("Arbitro (Enter si no sabes): ").strip() or "Por definir"

        c.execute("""
            INSERT INTO Partidos_Global (
                fecha, competicion, equipo_local, equipo_visitante,
                goles_local, goles_visitante, corners_local, corners_visitante,
                tarjetas_local, tarjetas_visitante, rojas_local, rojas_visitante, arbitro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fecha, comp, local, visita, gl, gv, cl, cv, tl, tv, rl, rv, arbitro))
        conn.commit()
        print("\nPartido guardado exitosamente.")

    elif 1 <= opc <= len(filas):
        elegido = filas[opc - 1]
        rowid = elegido[0]
        print(f"\n--- EDITANDO: {elegido[3]} vs {elegido[6]} ({elegido[1]}) ---")
        print("Presiona Enter para mantener el valor entre corchetes, o escribe el nuevo numero:")

        gl = pedir_num("Goles Local", elegido[4])
        gv = pedir_num("Goles Visitante", elegido[5])
        cl = pedir_num("Corners Local", elegido[7])
        cv = pedir_num("Corners Visitante", elegido[8])
        tl = pedir_num("Tarjetas Amarillas Local", elegido[9])
        tv = pedir_num("Tarjetas Amarillas Visitante", elegido[10])
        rl = pedir_num("Tarjetas Rojas Local", elegido[11])
        rv = pedir_num("Tarjetas Rojas Visitante", elegido[12])

        c.execute("""
            UPDATE Partidos_Global
            SET goles_local = ?, goles_visitante = ?,
                corners_local = ?, corners_visitante = ?,
                tarjetas_local = ?, tarjetas_visitante = ?,
                rojas_local = ?, rojas_visitante = ?
            WHERE rowid = ?
        """, (gl, gv, cl, cv, tl, tv, rl, rv, rowid))
        conn.commit()
        print(f"\nPartido ID {rowid} actualizado con exito.")

    conn.close()

if __name__ == "__main__":
    main()