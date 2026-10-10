with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Respaldo
with open('templates/index.html.bak', 'w', encoding='utf-8') as f:
    f.write(html)

css = """
<style>
.pulso-rojo {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: #ff3344;
    border-radius: 50%;
    margin-right: 5px;
    box-shadow: 0 0 6px #ff3344;
    animation: palpitar 1.2s infinite ease-in-out;
}
@keyframes palpitar {
    0%, 100% { transform: scale(0.9); opacity: 0.7; }
    50% { transform: scale(1.4); opacity: 1; }
}
.copsula-hora.en-vivo {
    background: rgba(255, 51, 68, 0.15) !important;
    color: #ff3344 !important;
    border: 1px solid rgba(255, 51, 68, 0.4) !important;
    font-weight: 700;
}
.gol-flash {
    animation: animacion-gol 2s ease-out;
}
@keyframes animacion-gol {
    0% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.9); border-color: #ffd700; }
    100% { box-shadow: none; }
}
</style>
"""

if '.pulso-rojo' not in html:
    html = html.replace('</head>', css + '\n</head>')

# Añadir atributos dinámicos a las tarjetas
html = html.replace(
    '<div class="tarjeta-partido" data-liga="{{ p.liga }}">',
    '<div class="tarjeta-partido" data-liga="{{ p.liga }}" data-fixture-id="{{ p.fixture_id }}">'
)

html = html.replace(
    '<span class="copsula-hora">{{ p.hora }}</span>',
    '<span class="copsula-hora" id="hora-{{ p.fixture_id }}">{{ p.hora }}</span>'
)

bloque_antiguo = """{% if p.goles_local != '-' and p.goles_local is not none %}
                            <div class="marcador-en-vivo">{{ p.goles_local }} - {{ p.goles_visita }}</div>
                        {% else %}
                            <div class="vs-circulo">VS</div>
                        {% endif %}"""

bloque_nuevo = """<div id="marcador-box-{{ p.fixture_id }}">
                        {% if p.goles_local != '-' and p.goles_local is not none %}
                            <div class="marcador-en-vivo">{{ p.goles_local }} - {{ p.goles_visita }}</div>
                        {% else %}
                            <div class="vs-circulo">VS</div>
                        {% endif %}
                        </div>"""

if bloque_antiguo in html:
    html = html.replace(bloque_antiguo, bloque_nuevo)

js = """
<script>
async function actualizarMarcadoresEnVivo() {
    try {
        const res = await fetch('/api/en-vivo');
        const data = await res.json();
        if (!data || !data.partidos) return;

        data.partidos.forEach(p => {
            const card = document.querySelector(`[data-fixture-id="${p.id}"]`);
            if (!card) return;

            const elemHora = document.getElementById(`hora-${p.id}`);
            if (elemHora) {
                elemHora.className = 'copsula-hora en-vivo';
                let txt = p.minuto ? `${p.minuto}'` : p.estado;
                if (p.estado === 'HT') txt = 'Descanso';
                elemHora.innerHTML = `<span class="pulso-rojo"></span> ${txt}`;
            }

            const elemBox = document.getElementById(`marcador-box-${p.id}`);
            if (elemBox) {
                const nuevoScore = `${p.goles_local} - ${p.goles_visita}`;
                const prev = elemBox.innerText.trim();
                if (prev !== nuevoScore && prev !== 'VS' && prev !== '') {
                    card.classList.add('gol-flash');
                    setTimeout(() => card.classList.remove('gol-flash'), 2500);
                }
                elemBox.innerHTML = `<div class="marcador-en-vivo">${nuevoScore}</div>`;
            }
        });
    } catch (e) {
        console.log("Sync error:", e);
    }
}
document.addEventListener('DOMContentLoaded', () => {
    actualizarMarcadoresEnVivo();
    setInterval(actualizarMarcadoresEnVivo, 45000);
});
</script>
"""

if 'actualizarMarcadoresEnVivo' not in html:
    html = html.replace('</body>', js + '\n</body>')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Plantilla templates/index.html actualizada correctamente.")
