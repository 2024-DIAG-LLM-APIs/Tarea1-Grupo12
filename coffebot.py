from flask import Flask, render_template, request, session, redirect, url_for
import pandas as pd
from openai import OpenAI
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de OpenAI
client = OpenAI(api_key="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")

# Archivos CSV
usuarios_file = "usuarios.csv"
menu_file = "menu.csv"
historial_file = "historial_pedidos.csv"
consideraciones_file = "consideraciones.txt"

# Crear archivos si no existen
if not os.path.exists(usuarios_file):
    pd.DataFrame(columns=["Usuario", "Clave", "Nombre", "Gustos", "Preferencias"]).to_csv(usuarios_file, index=False)
if not os.path.exists(historial_file):
    pd.DataFrame(columns=["Usuario", "FechaHora", "Pedido"]).to_csv(historial_file, index=False)

menu_df = pd.read_csv(menu_file, encoding="utf-8")
with open(consideraciones_file, "r", encoding="utf-8") as file:
    consideraciones = file.read()
menu = menu_df.to_string(index=False)

# Función para guardar historial
def guardar_historial_pedido(usuario, pedido):
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    historial_df = pd.read_csv(historial_file)
    nuevo_registro = pd.DataFrame([{"Usuario": usuario, "FechaHora": fecha_hora, "Pedido": pedido}])
    historial_df = pd.concat([historial_df, nuevo_registro], ignore_index=True)
    historial_df.to_csv(historial_file, index=False)

# Interacción con CoffeBot
def coffebot_ai(nombre, gustos, preferencias, user_input):
    hora_actual = datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    mensajes = session.get("mensajes", [])

    if not mensajes:
        mensajes.append({
            "role": "system",
            "content": f"Eres CoffeBot, un asistente IA. Cliente: {nombre}, Gustos: {gustos}, "
                       f"Preferencias: {preferencias}, Menú: {menu}, Consideraciones: {consideraciones}"
        })

    if user_input.lower() == "finalizar pedido":
        user_input = "Quiero finalizar mi pedido, confírmalo."

    mensajes.append({"role": "user", "content": f"{hora_actual} - {user_input}"})
    response = client.chat.completions.create(model="gpt-4o", messages=mensajes, max_tokens=500)
    respuesta_asistente = response.choices[0].message.content

    if "***FINAL***" in respuesta_asistente:
        guardar_historial_pedido(session["nombre"], respuesta_asistente)
        session.clear()

    mensajes.append({"role": "assistant", "content": respuesta_asistente})
    session["mensajes"] = mensajes
    return respuesta_asistente

# Rutas
@app.route("/", methods=["GET", "POST"])
def index():
    if "nombre" not in session:  # Redirigir al login si no está autenticado
        return redirect(url_for("login"))

    historial_df = pd.read_csv(historial_file)
    historial_usuario = historial_df[historial_df["Usuario"] == session["nombre"]]

    if request.method == "POST":
        accion = request.form.get("accion")
        user_input = "finalizar pedido" if accion == "finalizar" else request.form["mensaje"]
        respuesta = coffebot_ai(session["nombre"], session.get("gustos", ""), session.get("preferencias", ""), user_input)
        return render_template("index.html", respuesta=respuesta, historial=historial_usuario.to_dict(orient="records"))

    return render_template("index.html", respuesta="", historial=historial_usuario.to_dict(orient="records"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario, clave = request.form["usuario"], request.form["clave"]
        usuarios_df = pd.read_csv(usuarios_file)
        user = usuarios_df[(usuarios_df["Usuario"] == usuario) & (usuarios_df["Clave"] == clave)]

        if not user.empty:
            session["nombre"] = user.iloc[0]["Nombre"]
            session["gustos"] = user.iloc[0]["Gustos"]
            session["preferencias"] = user.iloc[0]["Preferencias"]
            return redirect(url_for("index"))
        return render_template("login.html", error="Usuario o clave incorrectos")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        usuario, clave, nombre = request.form["usuario"], request.form["clave"], request.form["nombre"]
        gustos, preferencias = request.form.get("gustos", ""), request.form.get("preferencias", "")
        usuarios_df = pd.read_csv(usuarios_file)

        if not usuarios_df[usuarios_df["Usuario"] == usuario].empty:
            return render_template("register.html", error="El usuario ya existe")

        nuevo_usuario = pd.DataFrame([{"Usuario": usuario, "Clave": clave, "Nombre": nombre,
                                       "Gustos": gustos, "Preferencias": preferencias}])
        pd.concat([usuarios_df, nuevo_usuario]).to_csv(usuarios_file, index=False)
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
