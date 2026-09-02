"""Eval formal de la lógica de decisión (classify_report) contra el gold-set
oficial del reto: dataset/dataset_final.xlsx.

Antes de este script, el único eval existente era smoke_test.py — un único
caso de humo ad hoc, no un set fijo de casos corridos de forma reproducible.
El reto entrega 3.991 turnos ya etiquetados con label_ground_truth sobre
160 casos (40 pacientes × 4 días postoperatorios), en dos capas de dificultad
(capa1_limpia / capa2_ruidosa) — un gold-set real, no hay que inventar los
guiones de prueba a mano.

Metodología: label_ground_truth es constante por caso_id (una decisión para
toda la conversación, no por turno). Este script recorre, en orden, cada
turno del PACIENTE dentro de un caso (los turnos del agente son preguntas,
no reportes de síntomas — classify_report() no tiene nada que clasificar
ahí) y toma como predicción del caso la etiqueta más severa vista en
cualquiera de esos turnos (rojo > amarillo > verde). Esto refleja la
asimetría clínica que exige la rúbrica: si en algún punto de la
conversación aparece una señal de alarma, el caso debía escalar, sin
importar que turnos posteriores suenen tranquilos.

Uso:
    python backend/scripts/eval_gold_set.py
    python backend/scripts/eval_gold_set.py --capa capa2_ruidosa
    python backend/scripts/eval_gold_set.py --dataset ruta/a/otro_dataset.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SEVERITY = {"verde": 0, "amarillo": 1, "rojo": 2}
LABELS = ["verde", "amarillo", "rojo"]


def _worst_label(labels: list[str]) -> str:
    if not labels:
        return "verde"
    return max(labels, key=lambda label: SEVERITY.get(label, 0))


def run_eval(dataset_path: Path, capa: str, classify_report) -> dict[str, object]:
    import pandas as pd

    df = pd.read_excel(dataset_path, sheet_name="result")
    df = df[df["capa"] == capa]
    if df.empty:
        raise ValueError(f"No hay filas para capa='{capa}' en {dataset_path}")

    confusion: Counter[tuple[str, str]] = Counter()
    false_negatives: list[dict[str, object]] = []  # ground truth rojo, predicho otra cosa: la falla catastrófica
    per_case_detail: list[dict[str, object]] = []

    for caso_id, group in df.groupby("caso_id"):
        ground_truth = group["label_ground_truth"].iloc[0]
        patient_turns = group[group["hablante"] == "paciente"].sort_values("turno_idx")

        turn_labels: list[str] = []
        for _, row in patient_turns.iterrows():
            decision = classify_report(str(row["texto"]))
            turn_labels.append(decision["label"])

        predicted = _worst_label(turn_labels)
        confusion[(ground_truth, predicted)] += 1

        case_record = {
            "caso_id": caso_id,
            "paciente_id": group["paciente_id"].iloc[0],
            "ground_truth": ground_truth,
            "predicted": predicted,
            "correct": ground_truth == predicted,
            "patient_turn_count": len(patient_turns),
        }
        per_case_detail.append(case_record)

        # El falso negativo -no alertar cuando había que alertar- es la falla
        # catastrófica según la rúbrica: se listan aparte con el texto exacto
        # que debió disparar la alarma, para que sea depurable de un vistazo,
        # no solo un número en la matriz de confusión.
        if ground_truth == "rojo" and predicted != "rojo":
            false_negatives.append(
                {
                    **case_record,
                    "patient_turns": patient_turns[["turno_idx", "texto"]].to_dict("records"),
                }
            )

    total = len(per_case_detail)
    correct = sum(1 for c in per_case_detail if c["correct"])
    accuracy = round(correct / total, 4) if total else None

    # Recall de rojo = de todos los casos que SÍ debían escalar, cuántos el
    # sistema efectivamente escaló. Es la métrica que más le importa a la
    # rúbrica (asimetría clínica), más que el accuracy general — un sistema
    # que acierta 95% pero falla justo en rojo es peor que uno con menos
    # accuracy que nunca deja pasar un rojo.
    rojo_cases = [c for c in per_case_detail if c["ground_truth"] == "rojo"]
    rojo_recall = (
        round(sum(1 for c in rojo_cases if c["predicted"] == "rojo") / len(rojo_cases), 4) if rojo_cases else None
    )

    return {
        "dataset": str(dataset_path),
        "capa": capa,
        "total_casos": total,
        "accuracy": accuracy,
        "rojo_recall": rojo_recall,
        "confusion_matrix": {f"{gt}->{pred}": count for (gt, pred), count in sorted(confusion.items())},
        "false_negatives_rojo": false_negatives,
        "per_case": per_case_detail,
    }


def print_report(result: dict[str, object]) -> None:
    print(f"\n{'=' * 60}")
    print(f"Eval gold-set — capa: {result['capa']}")
    print(f"{'=' * 60}")
    print(f"Dataset:        {result['dataset']}")
    print(f"Casos evaluados: {result['total_casos']}")
    print(f"Accuracy:        {result['accuracy']}")
    print(f"Recall de rojo:  {result['rojo_recall']}  (de los casos que SÍ debían escalar, cuántos escaló)")
    print()
    print("Matriz de confusión (ground_truth -> predicho : cantidad):")
    for key, count in result["confusion_matrix"].items():
        marker = "  ⚠️  FALSO NEGATIVO" if key.startswith("rojo->") and not key.startswith("rojo->rojo") else ""
        print(f"  {key:20} {count}{marker}")

    fns = result["false_negatives_rojo"]
    if fns:
        print(f"\n⚠️  {len(fns)} caso(s) rojo NO detectados como rojo (falla catastrófica):")
        for case in fns:
            print(f"  - {case['caso_id']} (predicho: {case['predicted']})")
            for turn in case["patient_turns"]:
                print(f"      turno {turn['turno_idx']}: {turn['texto']}")
    else:
        print("\n✅ Ningún falso negativo en rojo para esta capa.")


def main() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.decision.rules import classify_report

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=root_dir / "dataset" / "dataset_final.xlsx",
        help="Ruta al dataset_final.xlsx (por defecto, dataset/dataset_final.xlsx)",
    )
    parser.add_argument(
        "--capa",
        choices=["capa1_limpia", "capa2_ruidosa", "both"],
        default="both",
        help="Qué capa de dificultad evaluar (por defecto, ambas)",
    )
    args = parser.parse_args()

    capas = ["capa1_limpia", "capa2_ruidosa"] if args.capa == "both" else [args.capa]
    results = [run_eval(args.dataset, capa, classify_report) for capa in capas]

    for result in results:
        print_report(result)

    output_dir = root_dir / "backend" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "eval_gold_set_report.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nReporte completo (con detalle por caso) guardado en: {output_path}")


if __name__ == "__main__":
    main()
