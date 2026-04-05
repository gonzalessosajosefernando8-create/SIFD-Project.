from flask import Flask, render_template, request
from textblob import TextBlob
import re
import requests
from googlesearch import search

app = Flask(__name__)

# --- CONFIGURACIÓN DE SUPABASE ---
SUPABASE_URL = "https://suaosskeoorwlaawyojq.supabase.co"
SUPABASE_KEY = "tu_key_aqui"


def guardar_en_supabase(url, texto, veredicto, subjetividad):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "url": url,
        "texto_noticia": texto[:100],
        "veredicto": veredicto,
        "subjetividad": subjetividad
    }
    try:
        endpoint = f"{SUPABASE_URL}/rest/v1/consultas"
        r = requests.post(endpoint, json=data, headers=headers)
        print(f"Status de Supabase: {r.status_code}")
    except Exception as e:
        print(f"Error silencioso en DB: {e}")


def logica_forense(texto, url_ingresada):
    puntos = 100
    hallazgos = []

    # 1. ANALISIS DE MAYÚSCULAS
    mayus = len(re.findall(r'[A-Z]', texto))
    total = len(re.findall(r'[a-zA-Z]', texto))
    if total > 0 and (mayus/total) > 0.3:
        puntos -= 30
        hallazgos.append(
            f"🚩 ALTA INTENSIDAD: {int((mayus/total)*100)}% en mayúsculas.")

    # 2. DETECTOR DE IA
    muletillas_ia = ["es importante destacar", "en conclusión",
                     "por otro lado", "además de esto", "cabe resaltar"]
    conteo_ia = sum(1 for frase in muletillas_ia if frase in texto.lower())
    if conteo_ia >= 2:
        puntos -= 15
        hallazgos.append("🤖 PATRÓN SINTÉTICO: Estructura gramatical de IA.")

    # 3. SUBJETIVIDAD
    analisis = TextBlob(texto)
    subj = int(analisis.sentiment.subjectivity * 100)
    if subj > 50:
        puntos -= 20
        hallazgos.append("🚩 SESGO DETECTADO: Lenguaje subjetivo.")

    # 4. ENTIDADES PERUANAS
    entidades_peru = ["MINEDU", "MINSA", "ONPE",
                      "GOBIERNO", "DINA BOLUARTE", "CONGRESO"]
    if any(e in texto.upper() for e in entidades_peru) and ".gob.pe" not in url_ingresada.lower():
        puntos -= 40
        hallazgos.append(
            "⚠️ SUPLANTACIÓN: Usa nombres oficiales en link no gubernamental.")

    # 5. BÚSQUEDA GOOGLE
    try:
        # Buscamos la noticia + palabras clave de verificación en Perú
        query_verificacion = f'"{texto[:50]}" site:gob.pe OR site:elcomercio.pe OR site:rpp.pe'
        enlaces = list(search(query_verificacion, num_results=3, lang="es"))

        fuentes_vivas = []
        for link in enlaces:
            # Solo agregamos fuentes que sabemos que son de alta confianza en Perú
            fuentes_vivas.append({"url": link, "status": "VERIFICADO"})

        if not fuentes_vivas:
            hallazgos.append(
                "⚠️ AISLAMIENTO: Ningún medio oficial peruano respalda esta información.")
    except:
        fuentes_vivas = []  # Esto debe estar alineado con el código anterior

    # --- MAPA DE CALOR ---
    # Todo esto debe tener el mismo nivel de espacios que el "except"
    texto_marcado = texto
    alertas_visuales = ["URGENTE", "BONO", "MINSA",
                        "MINEDU", "confirmado", "oportunidad única", "760"]

    for palabra in alertas_visuales:
        # Este bloque debe estar alineado con el 'texto_marcado' de arriba
        texto_marcado = re.sub(
            f"({palabra})",
            r'<mark style="background: #ef4444; color: white; border-radius: 4px; padding: 0 2px;">\1</mark>',
            texto_marcado,
            flags=re.IGNORECASE
        )
    # VEREDICTO
    if puntos >= 80:
        estado = "NIVEL DE CONFIANZA ALTO"
    elif puntos >= 50:
        estado = "SISTEMA EN ALERTA / SOSPECHOSO"
    else:
        estado = "AMENAZA CONFIRMADA: POSIBLE FAKE NEWS"

    # Al final de logica_forense devuelve las 5 cosas:
    return estado, hallazgos, subj, texto_marcado, fuentes_vivas


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    marcado = ""
    if request.method == "POST":
        url = request.form.get("url_input")
        texto = request.form.get("texto_input")

        # Capturamos las 4 variables
        estado, motivos, subjetividad, marcado = logica_forense(texto, url)

        guardar_en_supabase(url, texto, estado, subjetividad)

        resultado = {
            "estado": estado,
            "motivos": motivos,
            "subjetividad": subjetividad
        }

    # Enviamos 'texto_marcado' al HTML por separado
    return render_template("index.html", resultado=resultado, texto_marcado=marcado)


if __name__ == "__main__":
    app.run(debug=True)
