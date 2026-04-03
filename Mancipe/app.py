from flask import Flask, render_template, request, redirect, url_for, session, send_file
from email.mime.text import MIMEText
import pandas as pd
import sqlite3
import smtplib
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import shutil
import os

app = Flask(__name__)
app.secret_key = "clave_super_ultra_segura_2026"
DB = "database.db"

def backup_db():

    if os.path.exists(DB):

        carpeta_backup = "backups"

        if not os.path.exists(carpeta_backup):
            os.makedirs(carpeta_backup)

        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")

        archivo_backup = f"{carpeta_backup}/backup_{fecha}.db"

        shutil.copy(DB, archivo_backup)

        print(f"Backup creado: {archivo_backup}")

# ----------------- BASE DE DATOS -----------------

def init_db():

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ---------------- TABLA EMPLEADOS ----------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empleados(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        edad INTEGER,
        fecha_nacimiento TEXT,
        puesto TEXT,
        salario REAL,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        eps TEXT,
        arl TEXT,
        celular TEXT,
        correo TEXT,
        estado_contrato TEXT
    )
    """)

    # ---------------- NUEVOS CAMPOS EMPLEADOS ----------------

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN cedula TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN fecha_expedicion TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN genero TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN tipo_contrato TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN afp TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN fecha_examen_medico TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN fecha_curso_alturas TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN estado_civil TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN direccion TEXT")
    except:
        pass
    
    # ---------------- CONTACTO DE EMERGENCIA ----------------

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN emergencia_nombre TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN emergencia_telefono TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN emergencia_direccion TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE empleados ADD COLUMN emergencia_parentesco TEXT")
    except:
        pass
    
    # ---------------- TABLA INASISTENCIAS ----------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inasistencias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        cedula TEXT,
        fecha_inicio TEXT,
        fecha_fin TEXT,
        tipo TEXT,  -- dias u horas
        total REAL,
        fecha_registro TEXT
    )
    """)

    # ---------------- TABLA USUARIOS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)

    # ---------------- TABLA PRESTAMOS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER,
            cargo TEXT,
            prestamo REAL,
            descuento REAL,
            tiempo_pago INTEGER,
            deuda_actual REAL,
            FOREIGN KEY(empleado_id) REFERENCES empleados(id)
        )
    """)

    try:
        cursor.execute("ALTER TABLE prestamos ADD COLUMN estado TEXT DEFAULT 'activo'")
    except:
        pass

    # ---------------- USUARIO ADMIN POR DEFECTO ----------------

    cursor.execute("SELECT * FROM usuarios WHERE username=?", ("ingmancipe",))

    if not cursor.fetchone():

        cursor.execute(
            "INSERT INTO usuarios (username,password,rol) VALUES (?,?,?)",
            ("ingmancipe", generate_password_hash("Casa-3025"), "superusuario")
        )

    # ---------------- PAGOS PRESTAMO ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos_prestamo(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER,
            fecha TEXT,
            monto REAL,
            FOREIGN KEY(prestamo_id) REFERENCES prestamos(id)
        )
    """)
    # ---------------- INASISTENCIAS ----------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inasistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            cedula TEXT,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            dias INTEGER,
            horas INTEGER,
            tipo TEXT,
            observaciones TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(empleado_id) REFERENCES empleados(id)
        )
    """)


init_db()
backup_db()

# ----------------- LOGIN -----------------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        cursor.execute("SELECT password,rol FROM usuarios WHERE username=?", (usuario,))
        result = cursor.fetchone()

        conn.close()

        if result and check_password_hash(result[0], password):

            session["usuario"] = usuario
            session["rol"] = result[1]

            # Si es anonimo entra directo a PQRS
            if result[1] == "anonimo":
                return redirect(url_for("pqrs"))

            return redirect(url_for("dashboard"))

        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos")

    return render_template("login.html")

# ----------------- DASHBOARD -----------------
@app.route("/dashboard")
def dashboard():

    if "usuario" not in session:
        return redirect(url_for("login"))

    # Si es anonimo no puede ver dashboard
    if session["rol"] == "anonimo":
        return redirect(url_for("pqrs"))

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 📊 CONTADORES
    cursor.execute("SELECT COUNT(*) FROM empleados")
    total_empleados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado='activo'")
    total_prestamos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pqrs")
    total_pqrs = cursor.fetchone()[0]

    # 🎂 CUMPLEAÑOS
    cursor.execute("SELECT nombre, apellido, fecha_nacimiento FROM empleados")
    empleados = cursor.fetchall()

    conn.close()

    hoy = datetime.today().date()
    alertas_cumple = []

    for e in empleados:

        if e["fecha_nacimiento"]:

            fecha = datetime.strptime(e["fecha_nacimiento"], "%Y-%m-%d").date()

            cumple = fecha.replace(year=hoy.year)

            if cumple < hoy:
                cumple = cumple.replace(year=hoy.year + 1)

            dias = (cumple - hoy).days

            if dias <= 3:
                nombre = e["nombre"] + " " + e["apellido"]

                if dias == 0:
                    alertas_cumple.append(f"🎉 Hoy cumple {nombre}")
                elif dias == 1:
                    alertas_cumple.append(f"🔥 {nombre} cumple mañana")
                else:
                    alertas_cumple.append(f"🎂 {nombre} cumple en {dias} días")

    return render_template(
        "dashboard.html",
        total_empleados=total_empleados,
        total_prestamos=total_prestamos,
        total_pqrs=total_pqrs,
        alertas_cumple=alertas_cumple
    )
# ----------------- EMPLEADOS -----------------

@app.route("/empleados", methods=["GET","POST"])
def empleados():

    if "usuario" not in session or session["rol"] not in ["gerencia","superusuario"]:
        return "Acceso denegado"

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ---------------- CREAR EMPLEADO ----------------

    if request.method == "POST" and "crear" in request.form:

        fecha_fin = request.form.get("fecha_fin")

        estado = "Activo"

        if fecha_fin and fecha_fin.strip() != "":
            estado = "Inactivo"

        emergencia_nombre = request.form.get("emergencia_nombre")
        emergencia_telefono = request.form.get("emergencia_telefono")
        emergencia_direccion = request.form.get("emergencia_direccion")
        emergencia_parentesco = request.form.get("emergencia_parentesco")

        cursor.execute("""
        INSERT INTO empleados
        (nombre,apellido,edad,fecha_nacimiento,puesto,salario,fecha_inicio,fecha_fin,eps,arl,celular,correo,estado_contrato,
        cedula,fecha_expedicion,genero,tipo_contrato,afp,fecha_examen_medico,fecha_curso_alturas,estado_civil,direccion,
        emergencia_nombre,emergencia_telefono,emergencia_direccion,emergencia_parentesco)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (

        request.form["nombre"],
        request.form["apellido"],
        request.form["edad"],
        request.form["fecha_nacimiento"],
        request.form["puesto"],
        request.form["salario"],
        request.form["fecha_inicio"],
        request.form["fecha_fin"],
        request.form["eps"],
        request.form["arl"],
        request.form["celular"],
        request.form["correo"],
        estado,

        request.form["cedula"],
        request.form.get("fecha_expedicion"),
        request.form["genero"],
        request.form["tipo_contrato"],
        request.form["afp"],
        request.form["fecha_examen_medico"],
        request.form["fecha_curso_alturas"],
        request.form["estado_civil"],
        request.form["direccion"],

        emergencia_nombre,
        emergencia_telefono,
        emergencia_direccion,
        emergencia_parentesco
        ))

        conn.commit()

    # ---------------- ELIMINAR EMPLEADO ----------------

    if request.method == "POST" and "eliminar" in request.form:

        cursor.execute(
            "DELETE FROM empleados WHERE id=?",
            (request.form["empleado_id"],)
        )

        conn.commit()

    # ---------------- LISTA EMPLEADOS ----------------

    cursor.execute("SELECT * FROM empleados")
    empleados = cursor.fetchall()

    conn.close()

    return render_template("empleados.html", empleados=empleados)

# ----------------- EXPORTAR EMPLEADOS -----------------

@app.route("/exportar_empleados")
def exportar_empleados():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB)

    df = pd.read_sql_query("SELECT * FROM empleados", conn)

    archivo = "empleados.xlsx"

    df.to_excel(archivo, index=False)

    conn.close()

    return send_file(archivo, as_attachment=True)


# ----------------- CUMPLEAÑOS -----------------

@app.route("/cumpleanos")
def cumpleanos():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT nombre, apellido, fecha_nacimiento FROM empleados")
    empleados = cursor.fetchall()

    conn.close()

    hoy = datetime.today().date()

    lista = []
    alertas = []

    for e in empleados:

        nombre = e["nombre"] + " " + e["apellido"]
        fecha_nacimiento = e["fecha_nacimiento"]

        if fecha_nacimiento:

            fecha = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()

            cumple = fecha.replace(year=hoy.year)

            if cumple < hoy:
                cumple = cumple.replace(year=hoy.year + 1)

            dias = (cumple - hoy).days

            # 🔥 AQUÍ ESTÁ LA CLAVE
            lista.append({
                "nombre": nombre,
                "fecha": fecha.strftime("%d-%m"),
                "dias": dias
            })

            if dias <= 7:
                alertas.append(f"🎂 {nombre} cumple en {dias} días")

    return render_template(
        "cumpleanos.html",
        lista=lista,
        alertas=alertas
    )
# ----------------- PRESTAMOS -----------------

@app.route("/prestamos", methods=["GET", "POST"])
def prestamos():

    if "usuario" not in session or session["rol"] not in ["superusuario", "gerencia"]:
        return "Acceso denegado"

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    if request.method == "POST":

        # REGISTRAR PAGO
        if "pagar" in request.form:

            prestamo_id = request.form["prestamo_id"]

            cursor.execute(
                "SELECT descuento,deuda_actual FROM prestamos WHERE id=?",
                (prestamo_id,)
            )

            datos = cursor.fetchone()

            descuento = datos[0]
            deuda_actual = datos[1]

            # registrar pago
            cursor.execute("""
            INSERT INTO pagos_prestamo(prestamo_id,fecha,monto)
            VALUES(?,?,?)
            """,(
                prestamo_id,
                datetime.today().strftime("%Y-%m-%d"),
                descuento
            ))

            # calcular nueva deuda
            nueva_deuda = deuda_actual - descuento

            if nueva_deuda < 0:
                nueva_deuda = 0

            # actualizar deuda
            cursor.execute("""
            UPDATE prestamos
            SET deuda_actual=?
            WHERE id=?
            """,(nueva_deuda,prestamo_id))

            # si se terminó de pagar
            if nueva_deuda == 0:

                cursor.execute("""
                UPDATE prestamos
                SET estado='pagado'
                WHERE id=?
                """,(prestamo_id,))


        # CREAR PRESTAMO
        elif "crear" in request.form:

            cursor.execute("""
            INSERT INTO prestamos
            (empleado_id,cargo,prestamo,descuento,tiempo_pago,deuda_actual,estado)
            VALUES (?,?,?,?,?,?,?)
            """, (
                request.form["empleado_id"],
                request.form["cargo"],
                request.form["prestamo"],
                request.form["descuento"],
                request.form["tiempo_pago"],
                request.form["prestamo"],
                "activo"
            ))

        conn.commit()

    cursor.execute("SELECT id,nombre FROM empleados")
    empleados = cursor.fetchall()

    # SOLO MOSTRAR PRESTAMOS ACTIVOS
    cursor.execute("""
    SELECT p.id,e.nombre,p.cargo,p.prestamo,p.descuento,p.tiempo_pago,p.deuda_actual
    FROM prestamos p
    JOIN empleados e ON e.id=p.empleado_id
    WHERE p.estado='activo'
    """)

    prestamos = cursor.fetchall()

    conn.close()

    return render_template(
        "prestamos.html",
        empleados=empleados,
        prestamos=prestamos
    )
  # Historial
# Historial
@app.route("/historial_prestamos")
def historial_prestamos():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.id,e.nombre,p.prestamo,p.tiempo_pago
    FROM prestamos p
    JOIN empleados e ON e.id=p.empleado_id
    WHERE p.estado='pagado'
    """)

    historial = cursor.fetchall()

    conn.close()

    return render_template("historial_prestamos.html",
                           historial=historial)

# ----------------- USUARIOS -----------------

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():

    if "usuario" not in session or session["rol"] != "superusuario":
        return "Acceso denegado"

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    if request.method == "POST":

        if "crear" in request.form:

            try:

                cursor.execute("""
                INSERT INTO usuarios (username,password,rol)
                VALUES (?,?,?)
                """, (
                    request.form["username"],
                    generate_password_hash(request.form["password"]),
                    request.form["rol"]
                ))

                conn.commit()

            except:
                pass

        if "eliminar" in request.form:

            cursor.execute("DELETE FROM usuarios WHERE id=?",
                           (request.form["user_id"],))

            conn.commit()

    cursor.execute("SELECT id,username,rol FROM usuarios")
    usuarios = cursor.fetchall()

    conn.close()

    return render_template("usuarios.html", usuarios=usuarios)

# ----------------- PQRS -----------------

@app.route("/pqrs", methods=["GET","POST"])
def pqrs():

    if "usuario" not in session or session["rol"] != "anonimo":
        return "Acceso denegado"

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # generar numero automatico
    cursor.execute("SELECT COUNT(*) FROM pqrs")
    total = cursor.fetchone()[0] + 1

    numero = f"PQRS-{total:04d}"

    if request.method == "POST":

        fecha = request.form["fecha"]
        tipo = request.form["tipo"]
        descripcion = request.form["descripcion"]

        cursor.execute("""
        INSERT INTO pqrs(numero,fecha,tipo,descripcion)
        VALUES(?,?,?,?)
        """,(numero,fecha,tipo,descripcion))

        conn.commit()

        mensaje = f"""
Nuevo PQRS recibido

Numero: {numero}
Fecha: {fecha}
Tipo: {tipo}

Descripcion:
{descripcion}
"""

        msg = MIMEText(mensaje)
        msg["Subject"] = f"PQRS Mancipe #{numero}"
        msg["From"] = "pqrmancipe@gmail.com"
        msg["To"] = "pqrmancipe@gmail.com"

        try:

            servidor = smtplib.SMTP("smtp.gmail.com",587)
            servidor.starttls()

            servidor.login("pqrmancipe@gmail.com","soxn xlaz zjnd vkkh")

            servidor.sendmail(
                "pqrmancipe@gmail.com",
                "pqrmancipe@gmail.com",
                msg.as_string()
            )

            servidor.quit()

        except:
            pass

        conn.close()

        return render_template("pqrs.html", numero=numero, enviado=True)

    conn.close()

    return render_template("pqrs.html", numero=numero)


# ----------------- hoja de  vida -----------------

@app.route("/empleado/<int:id>")
def ver_empleado(id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM empleados WHERE id=?", (id,))
    empleado = cursor.fetchone()

    conn.close()

    return render_template("perfil_empleado.html", empleado=empleado)

# ----------------- LOGOUT -----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# ----------------- qr -----------------
import qrcode

@app.route("/qr")
def generar_qr():

    url = "http://192.168.0.8:5000"  # tu app

    img = qrcode.make(url)

    ruta = "static/qr.png"
    img.save(ruta)

    return send_file(ruta, mimetype="image/png")
# ----------------- Seguimiento -----------------
@app.route('/seguimiento')
def seguimiento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('seguimiento.html')


# 👇👇 AQUÍ PEGAS EL CÓDIGO 👇👇

# ----------------- INASISTENCIAS -----------------
@app.route('/seguimiento/inasistencias', methods=["GET", "POST"])
def inasistencias():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            empleado_id = request.form.get("empleado_id")
            fecha_inicio = request.form.get("fecha_inicio")
            fecha_fin = request.form.get("fecha_fin")
            tipo = request.form.get("tipo")
            observaciones = request.form.get("observaciones", "")

            # Validar
            if not empleado_id or not fecha_inicio or not fecha_fin or not tipo:
                return "❌ Error: faltan datos"

            f1 = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            f2 = datetime.strptime(fecha_fin, "%Y-%m-%d")

            if f2 < f1:
                return "❌ Error: fecha fin inválida"

            dias = (f2 - f1).days + 1
            horas = dias * 8

            # Obtener cédula
            cursor.execute("SELECT cedula FROM empleados WHERE id=?", (empleado_id,))
            result = cursor.fetchone()

            if not result:
                return "❌ Empleado no encontrado"

            cedula = result["cedula"]

            # Insertar
            cursor.execute("""
                INSERT INTO inasistencias 
                (empleado_id, cedula, fecha_inicio, fecha_fin, dias, horas, tipo, observaciones)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                empleado_id, cedula, fecha_inicio, fecha_fin,
                dias, horas, tipo, observaciones
            ))

            conn.commit()

            # 🔥 IMPORTANTE: REDIRECCIÓN
            return redirect(url_for("inasistencias"))

        except Exception as e:
            conn.close()
            return f"❌ Error: {str(e)}"

    # 👇 EMPLEADOS
    cursor.execute("SELECT id, nombre, cedula FROM empleados")
    empleados = cursor.fetchall()

    # 👇 HISTORIAL
    cursor.execute("""
        SELECT i.id, i.empleado_id, i.cedula, i.fecha_inicio, i.fecha_fin, i.dias, i.horas, i.tipo, i.observaciones, i.fecha_registro, e.nombre
        FROM inasistencias i
        JOIN empleados e ON e.id = i.empleado_id
        ORDER BY i.id DESC
    """)
    historial = cursor.fetchall()


    conn.close()

    return render_template(
        "seguimiento/inasistencias.html",
        empleados=empleados,
        historial=historial
    )

# ----------------- DOTACION -----------------
@app.route('/seguimiento/dotacion')
def dotacion():

    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template("seguimiento/dotacion.html")

# ----------------- VACACIONES -----------------
@app.route('/seguimiento/vacaciones')
def vacaciones():

    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template("seguimiento/vacaciones.html")

# ----------------- RETIRADOS -----------------
@app.route('/seguimiento/retirados')
def retirados():

    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template("seguimiento/retirados.html")

# ----------------- BUSQUEDA -----------------
@app.route('/busqueda', methods=["GET", "POST"])
def busqueda():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    resultados = []
    tipo_busqueda = None

    if request.method == "POST":

        tipo_busqueda = request.form.get("tipo_busqueda")

        # BÚSQUEDA POR EMPLEADO
        if tipo_busqueda == "empleado":

            empleado_id = request.form.get("empleado_id")

            if empleado_id:
                cursor.execute("""
                    SELECT i.id, i.empleado_id, i.cedula, i.fecha_inicio, i.fecha_fin, i.dias, i.horas, i.tipo, i.observaciones, e.nombre, e.apellido
                    FROM inasistencias i
                    JOIN empleados e ON e.id = i.empleado_id
                    WHERE i.empleado_id = ?
                    ORDER BY i.fecha_inicio DESC
                """, (empleado_id,))

                resultados = cursor.fetchall()

        # BÚSQUEDA POR FECHA
        elif tipo_busqueda == "fecha":

            fecha_inicio = request.form.get("fecha_inicio")
            fecha_fin = request.form.get("fecha_fin")

            if fecha_inicio and fecha_fin:
                cursor.execute("""
                    SELECT i.id, i.empleado_id, i.cedula, i.fecha_inicio, i.fecha_fin, i.dias, i.horas, i.tipo, i.observaciones, e.nombre, e.apellido
                    FROM inasistencias i
                    JOIN empleados e ON e.id = i.empleado_id
                    WHERE i.fecha_inicio >= ? AND i.fecha_fin <= ?
                    ORDER BY i.fecha_inicio DESC
                """, (fecha_inicio, fecha_fin))

                resultados = cursor.fetchall()

    # OBTENER LISTA DE EMPLEADOS
    cursor.execute("SELECT id, nombre, apellido, cedula FROM empleados ORDER BY nombre")
    empleados = cursor.fetchall()

    conn.close()

    return render_template(
        "busqueda.html",
        empleados=empleados,
        resultados=resultados,
        tipo_busqueda=tipo_busqueda
    )

# ----------------- Editar eempleado -----------------
@app.route("/editar_empleado/<int:id>", methods=["GET","POST"])
def editar_empleado(id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":

        fecha_fin = request.form.get("fecha_fin")

        estado = "Activo"
        if fecha_fin and fecha_fin.strip() != "":
            estado = "Inactivo"

        cursor.execute("""
        UPDATE empleados SET
        nombre=?,
        apellido=?,
        edad=?,
        fecha_nacimiento=?,
        puesto=?,
        salario=?,
        fecha_inicio=?,
        fecha_fin=?,
        eps=?,
        arl=?,
        celular=?,
        correo=?,
        estado_contrato=?,
        cedula=?,
        fecha_expedicion=?,
        genero=?,
        tipo_contrato=?,
        afp=?,
        fecha_examen_medico=?,
        fecha_curso_alturas=?,
        estado_civil=?,
        direccion=?,
        emergencia_nombre=?,
        emergencia_telefono=?,
        emergencia_direccion=?,
        emergencia_parentesco=?
        WHERE id=?
        """, (

        request.form.get("nombre"),
        request.form.get("apellido"),
        request.form.get("edad"),
        request.form.get("fecha_nacimiento"),
        request.form.get("puesto"),
        request.form.get("salario"),
        request.form.get("fecha_inicio"),
        request.form.get("fecha_fin"),
        request.form.get("eps"),
        request.form.get("arl"),
        request.form.get("celular"),
        request.form.get("correo"),
        estado,
        request.form.get("cedula"),
        request.form.get("fecha_expedicion"),
        request.form.get("genero"),
        request.form.get("tipo_contrato"),
        request.form.get("afp"),
        request.form.get("fecha_examen_medico"),
        request.form.get("fecha_curso_alturas"),
        request.form.get("estado_civil"),
        request.form.get("direccion"),
        request.form.get("emergencia_nombre"),
        request.form.get("emergencia_telefono"),
        request.form.get("emergencia_direccion"),
        request.form.get("emergencia_parentesco"),
        id
        ))

        conn.commit()

        return redirect("/empleado/" + str(id))


    cursor.execute("SELECT * FROM empleados WHERE id=?", (id,))
    empleado = cursor.fetchone()

    conn.close()

    return render_template("editar_empleado.html",empleado=empleado)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
