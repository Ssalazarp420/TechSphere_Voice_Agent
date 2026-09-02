from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class PatientLookupService:
    """Join en memoria entre los dos datasets de perfil de paciente que ya trae
    el reto (`dataset/perfiles_pacientes_co.xlsx` para identidad y
    `dataset/perfiles_clinicos_pacientes_silver_contest.xlsx` para el
    procedimiento), unidos por `paciente_id`.

    Antes del punto 1.2 del plan, nadie usaba este dato en el flujo de llamada:
    el agente no sabía a quién llamaba ni de qué cirugía. Es exactamente el
    hueco que señaló el jurado en 3.2 ("no hay identidad de paciente ni de
    procedimiento en ninguna parte del flujo de llamada").

    Vive como catálogo de solo lectura (se carga una vez, no cambia por
    sesión) — igual que CorpusVectorStore, se cachea como singleton en
    main.py para no releer los .xlsx en cada request.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.dataset_dir = root_dir / "dataset"
        self._demographics: pd.DataFrame | None = None
        self._clinical: pd.DataFrame | None = None

    def _load(self) -> None:
        if self._demographics is not None and self._clinical is not None:
            return
        self._demographics = pd.read_excel(self.dataset_dir / "perfiles_pacientes_co.xlsx")
        self._clinical = pd.read_excel(self.dataset_dir / "perfiles_clinicos_pacientes_silver_contest.xlsx")

    def sample_patients(self, limit: int = 5) -> list[dict[str, object]]:
        """Unos cuantos pacientes de ejemplo (id + nombre + procedimiento) para
        poblar el selector del frontend en la demo — no expone el dataset
        completo, solo lo mínimo necesario para elegir a quién "llamar"."""
        self._load()
        merged = self._clinical.merge(self._demographics, on="paciente_id", how="inner")
        sample = merged.head(limit)
        return [
            {
                "paciente_id": str(row["paciente_id"]),
                "nombre_completo": str(row["nombre_completo"]),
                "procedimiento": str(row["procedimiento"]),
            }
            for _, row in sample.iterrows()
        ]

    def get_patient_context(self, paciente_id: str) -> dict[str, object] | None:
        """None si el paciente_id no existe en alguno de los dos datasets —
        el llamador decide si eso es un 404 o simplemente seguir sin contexto
        de paciente (comportamiento aditivo: la llamada sigue funcionando sin
        identidad si no se encuentra)."""
        self._load()
        demo_match = self._demographics[self._demographics["paciente_id"] == paciente_id]
        clinical_match = self._clinical[self._clinical["paciente_id"] == paciente_id]
        if demo_match.empty or clinical_match.empty:
            logger.warning("paciente_id '%s' no encontrado en ambos datasets, sigue sin contexto", paciente_id)
            return None

        demo = demo_match.iloc[0]
        clinical = clinical_match.iloc[0]

        try:
            comorbilidades = json.loads(clinical.get("comorbilidades") or "[]")
        except (TypeError, ValueError):
            comorbilidades = []

        fecha_cirugia_raw = clinical.get("fecha_cirugia")
        fecha_cirugia = str(fecha_cirugia_raw)[:10] if fecha_cirugia_raw is not None else ""

        edad_raw = clinical.get("edad")
        edad = int(edad_raw) if edad_raw is not None and not pd.isna(edad_raw) else None

        return {
            "paciente_id": paciente_id,
            "nombre_completo": str(demo.get("nombre_completo", "")),
            "procedimiento": str(clinical.get("procedimiento", "")),
            "fecha_cirugia": fecha_cirugia,
            "edad": edad,
            "genero": str(clinical.get("genero") or "") or None,
            "comorbilidades": comorbilidades,
            # Valor crudo de modulo_synthea (ej. "appendicitis"). Se pasa al
            # prompt como pista de categoría clínica, pero NO se usa para
            # filtrar duro la búsqueda RAG: los nombres de carpeta del corpus
            # (p.ej. "Appendicitis", "colorectal cancer" con espacio) no
            # coinciden 1:1 en formato con este valor, y un filtro mal
            # emparejado dejaría resultados vacíos en vez de degradar
            # gradualmente. Queda como mejora futura documentada, no como
            # riesgo asumido a días de la demo en vivo.
            "categoria_clinica": str(clinical.get("modulo_synthea", "")),
        }
