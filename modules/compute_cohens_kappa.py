import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import cohen_kappa_score
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv
from util.config_util import ConfigUtil

## Load dotenv and configuration file

load_dotenv()
config = ConfigUtil.get_config()
ANNOTATORS_DIR = config.main.annotators_dir

MAIN_ANNOTATOR = ANNOTATORS_DIR + "/" + config.compute_cohens_kappa.main_annotator
SECOND_ANNOTATOR = ANNOTATORS_DIR + "/" + config.compute_cohens_kappa.second_annotator
THIRD_ANNOTATOR = ANNOTATORS_DIR + "/" + config.compute_cohens_kappa.third_annotator
REPORT_OUTPUT = config.main.report_dir


def load_jsonl(filepath):
    """Carga un archivo JSONL y devuelve una lista de diccionarios."""
    with open(filepath, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def extract_annotations(record):
    """
    Extrae entidades y relaciones mapeándolas a sus offsets espaciales
    para poder compararlas independientemente de sus IDs internos.
    """
    # Mapeo de IDs internos a offsets: id -> (start, end)
    ent_id_to_offset = {}
    entities_by_offset = {}

    for ent in record.get("entities", []):
        offset = (ent["start_offset"], ent["end_offset"])
        ent_id_to_offset[ent["id"]] = offset
        entities_by_offset[offset] = ent["label"]

    relations_by_offset = {}
    for rel in record.get("relations", []):
        # Mapeamos from_id y to_id a las coordenadas de los caracteres
        src_offset = ent_id_to_offset.get(rel["from_id"])
        dst_offset = ent_id_to_offset.get(rel["to_id"])

        if src_offset and dst_offset:
            rel_key = (src_offset[0], src_offset[1], dst_offset[0], dst_offset[1])
            relations_by_offset[rel_key] = rel["type"]

    return entities_by_offset, relations_by_offset


def get_consensus(l1, l2, l3):
    """
    Aplica las reglas de negocio para el consenso: Mayoría, Tie-break y Lone Wolf.
    Trata 'NONE' como una categoría válida.
    """
    labels = [l1, l2, l3]
    counts = Counter(labels)

    # Lobo Solitario (Lone Wolf): 2 NONE y 1 etiqueta válida
    if counts.get("NONE", 0) == 2 and len(set(labels)) == 2:
        valid_label = [l for l in labels if l != "NONE"][0]
        return "NONE", "Lone Wolf"

    # Unanimidad
    if len(set(labels)) == 1:
        return l1, "Unanimous"

    # Mayoría (2 de 3 coinciden)
    most_common = counts.most_common(2)
    if most_common[0][1] >= 2:
        return most_common[0][0], "Majority"

    # Desempate de 3 vías (Tie-Break) -> Gana el Experto 1
    return l1, "Tie-Broken"

def compute_fleiss_kappa(ratings_lists):
    """
    Calcula el coeficiente Kappa de Fleiss para múltiples anotadores.
    
    Args:
        ratings_lists: Una lista de listas, donde cada sublista contiene 
                       las anotaciones de un experto en el mismo orden.
                       Ejemplo: [experto1_labels, experto2_labels, experto3_labels]
    
    Returns:
        float: El valor del coeficiente Kappa de Fleiss.
    """
    # 1. Transponer las listas para agrupar las anotaciones por cada "sujeto" (item)
    items = list(zip(*ratings_lists))
    n_items = len(items)
    n_raters = len(ratings_lists)
    
    if n_items == 0:
        return 0.0
        
    # 2. Identificar todas las categorías únicas utilizadas en las anotaciones
    categories = set(label for item in items for label in item)
    category_to_idx = {cat: i for i, cat in enumerate(categories)}
    n_categories = len(categories)
    
    # 3. Construir la matriz de conteos (N items x K categorías)
    # count_matrix[i][j] = número de anotadores que asignaron la categoría j al item i
    count_matrix = np.zeros((n_items, n_categories))
    
    for i, item in enumerate(items):
        for label in item:
            j = category_to_idx[label]
            count_matrix[i, j] += 1
            
    # 4. Calcular el acuerdo observado (P_i) por cada item
    # Fórmula de la proporción de acuerdo: (sum(n_ij^2) - n) / (n * (n - 1))
    sum_squares = np.sum(count_matrix * count_matrix, axis=1)
    p_i = (sum_squares - n_raters) / (n_raters * (n_raters - 1))
    p_bar = np.mean(p_i)
    
    # 5. Calcular el acuerdo esperado por azar (P_e)
    # Proporción global de asignaciones a cada categoría (p_j)
    p_j = np.sum(count_matrix, axis=0) / (n_items * n_raters)
    p_bar_e = np.sum(p_j * p_j)
    
    # 6. Calcular el coeficiente Kappa de Fleiss
    if p_bar_e == 1.0:
        return 1.0 # Evitar la división por cero en casos de un acuerdo perfecto en una sola categoría
        
    kappa = (p_bar - p_bar_e) / (1 - p_bar_e)
    return kappa

def resolve_relation_offset(rec1, offset):
    return f"{rec1['text'][offset[0]:offset[1]]} -- {rec1['text'][offset[2]:offset[3]]}"


def process_annotations(file1, file2, file3):
    data1 = load_jsonl(file1)
    data2 = load_jsonl(file2)
    data3 = load_jsonl(file3)
    expert_1, expert_2, expert_3 = extract_expert_names_from_path(file1, file2, file3)

    gold_standard = []
    conflicts = []

    # Listas para calcular Cohen's Kappa
    kappa_data = {"e_1": [], "e_2": [], "e_3": [], "r_1": [], "r_2": [], "r_3": []}

    # Listas para la distribución de etiquetas
    label_dist = {"E1": [], "E2": [], "E3": []}

    # Contadores para el gráfico de pastel
    status_counts = {"Unanimous": 0, "Majority": 0, "Tie-Broken": 0, "Lone Wolf": 0}

    for idx, (rec1, rec2, rec3) in enumerate(zip(data1, data2, data3)):
        # 1. Alineación
        assert (
            rec1["sent_id"] == rec2["sent_id"] == rec3["sent_id"]
        ), f"IDs no coinciden en línea {idx}"
        assert (
            rec1["text"] == rec2["text"] == rec3["text"]
        ), f"Textos no coinciden en línea {idx}"

        e1, r1 = extract_annotations(rec1)
        e2, r2 = extract_annotations(rec2)
        e3, r3 = extract_annotations(rec3)

        all_ent_offsets = set(e1.keys()).union(set(e2.keys())).union(set(e3.keys()))
        all_rel_offsets = set(r1.keys()).union(set(r2.keys())).union(set(r3.keys()))

        gold_entities = []
        gold_relations = []
        gold_ent_offset_to_id = {}
        ent_counter = 1

        # 2. Procesar Entidades
        for offset in all_ent_offsets:
            lbl1 = e1.get(offset, "NONE")
            lbl2 = e2.get(offset, "NONE")
            lbl3 = e3.get(offset, "NONE")

            # Recolectar para Kappa y Distribución
            kappa_data["e_1"].append(lbl1)
            kappa_data["e_2"].append(lbl2)
            kappa_data["e_3"].append(lbl3)
            if lbl1 != "NONE":
                label_dist["E1"].append(lbl1)
            if lbl2 != "NONE":
                label_dist["E2"].append(lbl2)
            if lbl3 != "NONE":
                label_dist["E3"].append(lbl3)

            final_label, status = get_consensus(lbl1, lbl2, lbl3)
            status_counts[status] += 1

            if status != "Unanimous":
                span_text = rec1["text"][offset[0] : offset[1]]
                conflicts.append(
                    [
                        rec1["sent_id"],
                        span_text,
                        "Entity",
                        offset,
                        span_text != span_text.strip(),
                        lbl1,
                        lbl2,
                        lbl3,
                        final_label,
                        status,
                    ]
                )

            if final_label != "NONE":
                new_ent_id = ent_counter
                gold_ent_offset_to_id[offset] = new_ent_id
                gold_entities.append(
                    {
                        "id": new_ent_id,
                        "label": final_label,
                        "start_offset": offset[0],
                        "end_offset": offset[1],
                    }
                )
                ent_counter += 1

        # 3. Procesar Relaciones
        for offset in all_rel_offsets:
            lbl1 = r1.get(offset, "NONE")
            lbl2 = r2.get(offset, "NONE")
            lbl3 = r3.get(offset, "NONE")

            kappa_data["r_1"].append(lbl1)
            kappa_data["r_2"].append(lbl2)
            kappa_data["r_3"].append(lbl3)

            final_label, status = get_consensus(lbl1, lbl2, lbl3)

            # Registrar como conflicto de relaciones si no es unánime (no sumamos al status_counts para no duplicar el peso, o sí, según preferencia)
            if status != "Unanimous":
                conflicts.append(
                    [
                        rec1["sent_id"],
                        resolve_relation_offset(rec1, offset),
                        "Relation",
                        offset,
                        False,
                        lbl1,
                        lbl2,
                        lbl3,
                        final_label,
                        status,
                    ]
                )

            if final_label != "NONE":
                src_offset = (offset[0], offset[1])
                dst_offset = (offset[2], offset[3])
                # Solo crear la relación si ambas entidades sobrevivieron al Gold Standard

                if (
                    src_offset in gold_ent_offset_to_id
                    and dst_offset in gold_ent_offset_to_id
                ):
                    gold_relations.append(
                        {
                            "from_id": gold_ent_offset_to_id[src_offset],
                            "to_id": gold_ent_offset_to_id[dst_offset],
                            "type": final_label,
                        }
                    )

        # Construir registro de Gold Standard
        gold_standard.append(
            {
                "id": rec1.get("id"),
                "text": rec1.get("text"),
                "type": rec1.get("type"),
                "labels": rec1.get("labels", []),
                "source": rec1.get("source"),
                "tokens": rec1.get("tokens", []),
                "sent_id": rec1.get("sent_id"),
                "Comments": rec1.get("Comments", []),
                "project_id": rec1.get("project_id"),
                "entities": gold_entities,
                "relations": gold_relations,
            }
        )

    # Exportar Archivos
    pd.DataFrame(
        conflicts,
        columns=[
            "sentence_id",
            "text",
            "type",
            "offsets",
            "has_blanks",
            expert_1,
            expert_2,
            expert_3,
            "gold_label",
            "status",
        ],
    ).to_csv(f"{REPORT_OUTPUT}/conflict_report.csv", index=False)

    with open(f"{REPORT_OUTPUT}/gold_standard.jsonl", "w", encoding="utf-8") as f:
        for record in gold_standard:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --- Cálculo de Fleiss's Kappa ---
    fleiss_k_ent = compute_fleiss_kappa([kappa_data["e_1"], kappa_data["e_2"], kappa_data["e_3"]])
    fleiss_k_rel = compute_fleiss_kappa([kappa_data["r_1"], kappa_data["r_2"], kappa_data["r_3"]])
    
    print("\n" + "="*40)
    print("MÉTRICAS DE ACUERDO GLOBAL (FLEISS'S KAPPA)")
    print("="*40)
    print(f"Acuerdo global en Entidades:  {fleiss_k_ent:.4f}")
    print(f"Acuerdo global en Relaciones: {fleiss_k_rel:.4f}")
    print("="*40 + "\n")

    generate_visualizations(
        kappa_data, label_dist, status_counts, expert_1, expert_2, expert_3
    )


def generate_visualizations(
    kappa_data, label_dist, status_counts, expert_1, expert_2, expert_3
):
    """Genera las 3 visualizaciones solicitadas."""
    plt.figure(figsize=(18, 5))

    # 1. Mapa de Calor de Cohen's Kappa (Entidades)
    plt.subplot(1, 3, 1)
    k_12 = cohen_kappa_score(kappa_data["e_1"], kappa_data["e_2"])
    k_23 = cohen_kappa_score(kappa_data["e_2"], kappa_data["e_3"])
    k_13 = cohen_kappa_score(kappa_data["e_1"], kappa_data["e_3"])

    kappa_matrix = np.array([[1.0, k_12, k_13], [k_12, 1.0, k_23], [k_13, k_23, 1.0]])
    sns.heatmap(
        kappa_matrix,
        annot=True,
        cmap="Blues",
        xticklabels=[expert_1, expert_2, expert_3],
        yticklabels=[expert_1, expert_2, expert_3],
        vmin=0,
        vmax=1,
    )
    plt.title("Pairwise Cohen's Kappa (Entities)")

    # 2. Gráfico de Barras de Distribución de Etiquetas
    plt.subplot(1, 3, 2)
    df_labels = pd.DataFrame(
        [{"Expert": expert_1, "Label": l} for l in label_dist["E1"]]
        + [{"Expert": expert_2, "Label": l} for l in label_dist["E2"]]
        + [{"Expert": expert_3, "Label": l} for l in label_dist["E3"]]
    )

    if not df_labels.empty:
        sns.countplot(data=df_labels, x="Label", hue="Expert", palette="viridis")
        plt.title("Label Distribution by Expert")
        plt.xticks(rotation=45)

    # 3. Gráfico de Pastel de Acuerdos
    plt.subplot(1, 3, 3)
    labels = list(status_counts.keys())
    sizes = list(status_counts.values())
    # Filtrar ceros para el gráfico
    labels = [l for l, s in zip(labels, sizes) if s > 0]
    sizes = [s for s in sizes if s > 0]

    plt.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        colors=sns.color_palette("pastel"),
    )
    plt.title("Agreement Status Overview")

    plt.tight_layout()
    plt.savefig(f"{REPORT_OUTPUT}/annotation_report_visuals.png")
    plt.show()


def extract_expert_names_from_path(file1, file2, file3):
    return Path(file1).stem, Path(file2).stem, Path(file3).stem


# --- Ejecución ---
# Para usarlo, simplemente llama a la función principal con tus archivos:
# process_annotations('expert_annotation_1.jsonl', 'expert_annotation_2.jsonl', 'expert_annotation_3.jsonl')

# --- Ejecución ---
# Para usarlo, simplemente llama a la función principal con tus archivos:

process_annotations(MAIN_ANNOTATOR, SECOND_ANNOTATOR, THIRD_ANNOTATOR)
