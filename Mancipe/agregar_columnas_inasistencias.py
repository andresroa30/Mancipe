import sqlite3

DB = "database.db"

conn = sqlite3.connect(DB)
cursor = conn.cursor()

# Agregar columnas faltantes si no existen
columnas_a_agregar = ["dias", "horas", "observaciones", "empleado_id"]

for col in columnas_a_agregar:
    try:
        cursor.execute(f"ALTER TABLE inasistencias ADD COLUMN {col} INTEGER")
        print(f"✅ Columna {col} agregada correctamente")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"ℹ️ La columna {col} ya existe")
        else:
            raise

conn.commit()
conn.close()