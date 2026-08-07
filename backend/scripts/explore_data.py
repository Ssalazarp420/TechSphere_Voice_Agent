print("### SCRIPT INICIADO ###")

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
from pathlib import Path

print("### IMPORTS OK ###")

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "dataset"
print(f"### Buscando en: {DATA_DIR.resolve()} ###")
print(f"### Existe la carpeta?: {DATA_DIR.exists()} ###")


def leer_excel_seguro(nombre_archivo: str) -> pd.DataFrame:
    ruta = DATA_DIR / nombre_archivo
    print(f"### Leyendo: {ruta.name} ###")
    return pd.read_excel(ruta, sheet_name="result", dtype=str, engine="openpyxl")


print("### Probando archivo pequeño ###")
perfiles_clinicos = leer_excel_seguro("perfiles_clinicos_pacientes_silver_contest.xlsx")
print("### Archivo pequeño OK ###")
print(perfiles_clinicos.shape)

# Cargar los 4 xlsx (todos con hoja "result")
conversaciones = leer_excel_seguro("dataset_final.xlsx")
trayectorias = leer_excel_seguro("trayectorias_postop_silver.xlsx")
perfiles_clinicos = leer_excel_seguro("perfiles_clinicos_pacientes_silver_contest.xlsx")
perfiles_demo = leer_excel_seguro("perfiles_pacientes_co.xlsx")

print("=== SHAPES ===")
for name, df in [("conversaciones", conversaciones), ("trayectorias", trayectorias),
                  ("perfiles_clinicos", perfiles_clinicos), ("perfiles_demo", perfiles_demo)]:
    print(f"{name}: {df.shape} | columnas: {list(df.columns)}")

print("\n=== VALORES ÚNICOS CLAVE ===")
print("capas en conversaciones:", conversaciones["capa"].unique())
print("labels ground truth:", conversaciones["label_ground_truth"].unique())
print("distribución de labels:", conversaciones.drop_duplicates("caso_id")["label_ground_truth"].value_counts())

print("\n=== EJEMPLO DE JOIN ===")
# caso_id = "caso_" + trayectoria_id
trayectorias["caso_id_derivado"] = "caso_" + trayectorias["trayectoria_id"].astype(str)
caso_ejemplo = trayectorias["caso_id_derivado"].iloc[0]
print(f"Caso ejemplo: {caso_ejemplo}")
turnos_caso = conversaciones[conversaciones["caso_id"] == caso_ejemplo]
print(f"Turnos encontrados para ese caso: {len(turnos_caso)}")
print(turnos_caso[["capa", "dialogo_id"]].head(10))

print("\n=== COMORBILIDADES (JSON en celda) ===")
print(perfiles_clinicos["comorbilidades"].iloc[0])