import os
import re
import requests
from flask import Flask, render_template, request
from textblob import TextBlob
from googlesearch import search
from supabase import create_client, Client

# Vercel buscará estas variables en "Settings -> Environment Variables"
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://suaosskeoorwlaawyojq.supabase.co")
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1YW9zc2tlb29yd2xhYXd5b2pxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzNDI4NjksImV4cCI6MjA5MDkxODg2OX0.CgsO-NlQDpwusZplRXohbWhpNP4C4VQZBcQMhExRheI")

# Inicializamos el cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)


def guardar_en_supabase(url, texto, veredicto, subjetividad, fuentes):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "url": url,
        "texto_noticia": texto[:100],
        "veredicto": veredicto,
        "subjetividad": subjetividad,
        "fuentes": str(fuentes)
    }
    try:
        endpoint = f"{SUPABASE_URL}/rest/v1/consultas"
        r = requests.post(endpoint, json=data, headers=headers)
        print(f"Status de Supabase: {r.status_code}")
    except Exception as e:
        print(f"Error en base de datos: {e}")


def logica_forense(texto, url_ingresada):
    puntos = 100
    hallazgos = []

    # 1. ANÁLISIS DE MAYÚSCULAS
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
    fuentes_vivas = []
    try:
        query_verificacion = f'"{texto[:50]}" site:gob.pe OR site:elcomercio.pe OR site:rpp.pe'
        enlaces = list(search(query_verificacion, num_results=3, lang="es"))
        for link in enlaces:
            fuentes_vivas.append({"url": link, "status": "VERIFICADO"})
        if not fuentes_vivas:
            hallazgos.append(
                "⚠️ AISLAMIENTO: Ningún medio oficial peruano respalda esta información.")
    except:
        pass

    # --- MAPA DE CALOR ---
    texto_marcado = texto
    alertas_visuales = ["URGENTE", "BONO", "MINSA",
                        "MINEDU", "confirmado", "oportunidad única", "760"]
    for palabra in alertas_visuales:
        texto_marcado = re.sub(
            f"({palabra})",
            r'<mark style="background: #ef4444; color: white; border-radius: 4px; padding: 0 2px;">\1</mark>',
            texto_marcado,
            flags=re.IGNORECASE
        )

    # VEREDICTO FINAL
    if puntos >= 80:
        estado = "NIVEL DE CONFIANZA ALTO"
    elif puntos >= 50:
        estado = "SISTEMA EN ALERTA / SOSPECHOSO"
    else:
        estado = "AMENAZA CONFIRMADA: POSIBLE FAKE NEWS"

    return estado, hallazgos, subj, texto_marcado, fuentes_vivas


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    marcado = ""
    if request.method == "POST":
        url_input = request.form.get("url_input") or ""
        texto_input = request.form.get("texto_input") or ""

        # Obtenemos las 5 variables de la lógica
        estado, motivos, subjetividad, marcado, fuentes = logica_forense(
            texto_input, url_input)

        # Guardamos en Supabase
        guardar_en_supabase(url_input, texto_input,
                            estado, subjetividad, fuentes)

        resultado = {
            "estado": estado,
            "motivos": motivos,
            "subjetividad": subjetividad,
            "fuentes": fuentes
        }

    return render_template("index.html", resultado=resultado, texto_marcado=marcado)


# Esto es lo que Vercel necesita para encontrar la app
app = app

if __name__ == "__main__":
    app.run()
