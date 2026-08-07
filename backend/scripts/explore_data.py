print("### SCRIPT INICIADO ###")

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import json
from pathlib import Path

print("### IMPORTS OK ###")

DATA_DIR = Path("dataset")
print(f"### Buscando en: {DATA_DIR.resolve()} ###")
print(f"### Existe la carpeta?: {DATA_DIR.exists()} ###")

# Cargar los 4 xlsx (todos con hoja "result")
conversaciones = pd.read_excel(DATA_DIR / "dataset_final.xlsx", sheet_name="result")
trayectorias = pd.read_excel(DATA_DIR / "trayectorias_postop_silver.xlsx", sheet_name="result")
perfiles_clinicos = pd.read_excel(DATA_DIR / "perfiles_clinicos_pacientes_silver_contest.xlsx", sheet_name="result")
perfiles_demo = pd.read_excel(DATA_DIR / "perfiles_pacientes_co.xlsx", sheet_name="result")

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