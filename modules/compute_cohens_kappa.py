import os
import csv
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

            span_text = rec1["text"][offset[0] : offset[1]]
            if status != "Unanimous":
                conflicts.append(
                    [
                        rec1["sent_id"],
                        rec1["text"],
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
                        "text": span_text,
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
                        rec1["text"],
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
                "sent_id": rec1.get("sent_id"),
                "text": rec1.get("text"),
                "type": rec1.get("type"),
                "labels": rec1.get("labels", []),
                "source": rec1.get("source"),
                "tokens": rec1.get("tokens", []),
                "Comments": rec1.get("Comments", []),
                "project_id": rec1.get("project_id"),
                "entities": gold_entities,
                "relations": gold_relations,
                "id": rec1.get("id"),
            }
        )

    # Exportar Archivos
    pd.DataFrame(
        conflicts,
        columns=[
            "sentence_id",
            "sentence_text",
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
    
    with open(f"{REPORT_OUTPUT}/fleiss_kappa.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["type", "value"])
        writer.writeheader()
        writer.writerow({"type":"Entities", "value": fleiss_k_ent})
        writer.writerow({"type":"Relations", "value": fleiss_k_rel})

    print("\n" + "="*40)
    print("MÉTRICAS DE ACUERDO GLOBAL (FLEISS'S KAPPA)")
    print("="*40)
    print(f"Acuerdo global en Entidades:  {fleiss_k_ent:.4f}")
    print(f"Acuerdo global en Relaciones: {fleiss_k_rel:.4f}")
    print("="*40 + "\n")

    generate_visualizations(
        kappa_data, label_dist, status_counts, expert_1, expert_2, expert_3
    )

def export_visualizations_to_csv(kappa_data, label_dist, status_counts, expert_1, expert_2, expert_3):
    """Exporta los datos de las métricas a archivos CSV con conteos agregados."""
    
    # Asegurar que el directorio existe
    csv_path = f"{REPORT_OUTPUT}/kappa_csv"
    os.makedirs(csv_path, exist_ok=True)
    
    experts = [expert_1, expert_2, expert_3]

    # 1. Exportar Matrices de Kappa (Entidades y Relaciones)
    # Entidades
    k_12_e = cohen_kappa_score(kappa_data["e_1"], kappa_data["e_2"])
    k_23_e = cohen_kappa_score(kappa_data["e_2"], kappa_data["e_3"])
    k_13_e = cohen_kappa_score(kappa_data["e_1"], kappa_data["e_3"])
    pd.DataFrame({
        expert_1: [1.0, k_12_e, k_13_e],
        expert_2: [k_12_e, 1.0, k_23_e],
        expert_3: [k_13_e, k_23_e, 1.0]
    }, index=experts).to_csv(f"{csv_path}/kappa_entities.csv")

    # Relaciones
    k_12_r = cohen_kappa_score(kappa_data["r_1"], kappa_data["r_2"])
    k_23_r = cohen_kappa_score(kappa_data["r_2"], kappa_data["r_3"])
    k_13_r = cohen_kappa_score(kappa_data["r_1"], kappa_data["r_3"])
    pd.DataFrame({
        expert_1: [1.0, k_12_r, k_13_r],
        expert_2: [k_12_r, 1.0, k_23_r],
        expert_3: [k_13_r, k_23_r, 1.0]
    }, index=experts).to_csv(f"{csv_path}/kappa_relations.csv")

    # 2. Exportar Distribución de Etiquetas (Entidades) - CONTEO AGREGADO
    df_labels_e_raw = pd.DataFrame(
        [{"Expert": expert_1, "Label": l} for l in label_dist.get("E1", [])]
        + [{"Expert": expert_2, "Label": l} for l in label_dist.get("E2", [])]
        + [{"Expert": expert_3, "Label": l} for l in label_dist.get("E3", [])]
    )
    
    if not df_labels_e_raw.empty:
        # Agrupamos por Expert y Label y contamos las ocurrencias
        df_labels_e_counts = df_labels_e_raw.groupby(["Expert", "Label"]).size().reset_index(name="Count")
        df_labels_e_counts.to_csv(f"{csv_path}/labels_distribution_entities.csv", index=False)

    # 3. Exportar Distribución de Etiquetas (Relaciones) - CONTEO AGREGADO
    rel_l1 = [l for l in kappa_data["r_1"] if l != "NONE"]
    rel_l2 = [l for l in kappa_data["r_2"] if l != "NONE"]
    rel_l3 = [l for l in kappa_data["r_3"] if l != "NONE"]
    
    df_labels_r_raw = pd.DataFrame(
        [{"Expert": expert_1, "Label": l} for l in rel_l1]
        + [{"Expert": expert_2, "Label": l} for l in rel_l2]
        + [{"Expert": expert_3, "Label": l} for l in rel_l3]
    )

    if not df_labels_r_raw.empty:
        # Agrupamos por Expert y Label y contamos las ocurrencias
        df_labels_r_counts = df_labels_r_raw.groupby(["Expert", "Label"]).size().reset_index(name="Count")
        df_labels_r_counts.to_csv(f"{csv_path}/labels_distribution_relations.csv", index=False)

    # 4. Exportar Resumen de Acuerdos
    df_status = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Count'])
    df_status.to_csv(f"{csv_path}/agreement_status_summary.csv", index=False)

    print(f"✅ CSVs generados con conteos totales en: {csv_path}")

def export_kappa_to_latex(kappa_data, expert_1, expert_2, expert_3):
    """
    Genera un archivo .tex con heatmaps compactos.
    Se corrigió el error de PGF Math usando \rawvalue para la comparación de color.
    """
    output_path = f"{REPORT_OUTPUT}/kappa_csv"
    os.makedirs(output_path, exist_ok=True)
    
    # Escapar nombres para LaTeX
    experts_tex = [e.replace("_", "\\_") for e in [expert_1, expert_2, expert_3]]
    
    def get_kappas(prefix):
        return {
            (0, 1): cohen_kappa_score(kappa_data[f"{prefix}_1"], kappa_data[f"{prefix}_2"]),
            (1, 2): cohen_kappa_score(kappa_data[f"{prefix}_2"], kappa_data[f"{prefix}_3"]),
            (0, 2): cohen_kappa_score(kappa_data[f"{prefix}_1"], kappa_data[f"{prefix}_3"]),
        }

    k_e = get_kappas("e")
    k_r = get_kappas("r")

    def generate_table_data(k_dict):
        lines = ["    X                  Y              C"]
        for i in range(3):
            for j in range(3):
                val = 1.0 if i == j else k_dict[tuple(sorted((i, j)))]
                lines.append(f"    {{{experts_tex[i]}}}   {{{experts_tex[j]}}}        {val:.4f}")
        return "\n".join(lines)

    latex_template = r"""
\pgfplotsset{
    compact_heatmap/.style={
        scale only axis,
        width=2.5cm, 
        height=2.5cm,
        axis on top,
        shader=flat corner,
        enlargelimits=false,
        tick style={draw=none},
        axis line style={draw=none},
        colormap={invertedviridis}{rgb255=(253,231,37) rgb255=(33,145,140) rgb255=(68,1,84)},
        symbolic x coords={""" + f"{{{experts_tex[0]}}}, {{{experts_tex[1]}}}, {{{experts_tex[2]}}}" + r"""},
        symbolic y coords={""" + f"{{{experts_tex[0]}}}, {{{experts_tex[1]}}}, {{{experts_tex[2]}}}" + r"""},
        xtick=data, 
        ytick=data,
        xticklabel style={
            rotate=60, 
            anchor=east, 
            font=\small,
        },
        yticklabel style={
            font=\small,
            xshift=-0.8cm
        },
        point meta min=0, point meta max=1,
    }
}

\begin{tikzpicture}
% --- ENTITIES ---
\begin{axis}[
    compact_heatmap,
    title={\small Entities},
    y dir=reverse,
    clip=false,
    name=left_plot
]
\addplot [
    matrix plot*, 
    draw=white, 
    line width=0.2pt, 
    point meta=explicit,
    mesh/cols=3,
    visualization depends on=\thisrow{C} \as \rawvalue,
    nodes near coords={\pgfmathprintnumber[fixed,precision=2]{\rawvalue}},
    nodes near coords style={
        anchor=center,
        font=\footnotesize\bfseries,
        execute at begin node={
            \pgfmathparse{\rawvalue < 0.5 ? 1 : 0}
            \ifnum\pgfmathresult=1 \pgfkeysalso{/tikz/text=black} \else \pgfkeysalso{/tikz/text=white} \fi
        }
    }
] table [header=has colnames, meta=C] {
""" + generate_table_data(k_e) + r"""
};
\end{axis}

% --- RELATIONS ---
\begin{axis}[
    compact_heatmap,
    title={\small Relations},
    at={(left_plot.north east)},
    anchor=north west,
    xshift=2cm,
    clip=false,
    y dir=reverse,
    yticklabels={,,},
    yticklabel style={opacity=0},
    colorbar,
    colorbar style={
        height=2.3cm,
        width=0.25cm,
        yticklabel style={font=\tiny},
    }
]
\addplot [
    matrix plot*, 
    draw=white, 
    line width=0.2pt, 
    point meta=explicit, 
    mesh/cols=3,
    visualization depends on=\thisrow{C} \as \rawvalue,
    nodes near coords={\pgfmathprintnumber[fixed,precision=2]{\rawvalue}},
    nodes near coords style={
        anchor=center,
        font=\footnotesize\bfseries,
        execute at begin node={
            \pgfmathparse{\rawvalue < 0.5 ? 1 : 0}
            \ifnum\pgfmathresult=1 \pgfkeysalso{/tikz/text=black} \else \pgfkeysalso{/tikz/text=white} \fi
        }
    }
] table [header=has colnames, meta=C] {
""" + generate_table_data(k_r) + r"""
};
\end{axis}
\end{tikzpicture}
"""

    with open(f"{output_path}/kappa_entities_relations.tex", "w", encoding="utf-8") as f:
        f.write(latex_template)
    print(f"✅ Archivo LaTeX corregido en: {output_path}")

def generate_visualizations(
    kappa_data, label_dist, status_counts, expert_1, expert_2, expert_3
):
    """Genera visualizaciones de acuerdo y distribución para Entidades y Relaciones."""
    plt.figure(figsize=(18, 10)) # Aumentamos el alto de la figura para 2 filas

    # ==========================================
    # FILA 1: ENTIDADES
    # ==========================================
    
    # 1. Mapa de Calor de Cohen's Kappa (Entidades)
    plt.subplot(2, 3, 1)
    k_12_e = cohen_kappa_score(kappa_data["e_1"], kappa_data["e_2"])
    k_23_e = cohen_kappa_score(kappa_data["e_2"], kappa_data["e_3"])
    k_13_e = cohen_kappa_score(kappa_data["e_1"], kappa_data["e_3"])

    kappa_matrix_e = np.array([[1.0, k_12_e, k_13_e], [k_12_e, 1.0, k_23_e], [k_13_e, k_23_e, 1.0]])
    sns.heatmap(
        kappa_matrix_e, annot=True, cmap="Blues",
        xticklabels=[expert_1, expert_2, expert_3],
        yticklabels=[expert_1, expert_2, expert_3], vmin=0, vmax=1
    )
    plt.title("Pairwise Cohen's Kappa (Entities)")

    # 2. Gráfico de Barras de Distribución de Etiquetas (Entidades)
    plt.subplot(2, 3, 2)
    df_labels_e = pd.DataFrame(
        [{"Expert": expert_1, "Label": l} for l in label_dist.get("E1", [])]
        + [{"Expert": expert_2, "Label": l} for l in label_dist.get("E2", [])]
        + [{"Expert": expert_3, "Label": l} for l in label_dist.get("E3", [])]
    )

    if not df_labels_e.empty:
        sns.countplot(data=df_labels_e, x="Label", hue="Expert", palette="viridis")
        plt.title("Label Distribution by Expert (Entities)")
        plt.xticks(rotation=45)

    # 3. Gráfico de Pastel de Acuerdos (General)
    plt.subplot(2, 3, 3)
    labels = list(status_counts.keys())
    sizes = list(status_counts.values())
    labels = [l for l, s in zip(labels, sizes) if s > 0]
    sizes = [s for s in sizes if s > 0]

    if sizes:
        plt.pie(
            sizes, labels=labels, autopct="%1.1f%%", 
            startangle=140, colors=sns.color_palette("pastel")
        )
        plt.title("Agreement Status Overview (Overall)")

    # ==========================================
    # FILA 2: RELACIONES
    # ==========================================
    
    # 4. Mapa de Calor de Cohen's Kappa (Relaciones)
    plt.subplot(2, 3, 4)
    k_12_r = cohen_kappa_score(kappa_data["r_1"], kappa_data["r_2"])
    k_23_r = cohen_kappa_score(kappa_data["r_2"], kappa_data["r_3"])
    k_13_r = cohen_kappa_score(kappa_data["r_1"], kappa_data["r_3"])

    kappa_matrix_r = np.array([[1.0, k_12_r, k_13_r], [k_12_r, 1.0, k_23_r], [k_13_r, k_23_r, 1.0]])
    sns.heatmap(
        kappa_matrix_r, annot=True, cmap="Greens", # Usamos verde para diferenciar de entidades
        xticklabels=[expert_1, expert_2, expert_3],
        yticklabels=[expert_1, expert_2, expert_3], vmin=0, vmax=1
    )
    plt.title("Pairwise Cohen's Kappa (Relations)")

    # 5. Gráfico de Barras de Distribución de Etiquetas (Relaciones)
    plt.subplot(2, 3, 5)
    # Extraemos etiquetas válidas directamente de kappa_data para no modificar process_annotations
    rel_l1 = [l for l in kappa_data["r_1"] if l != "NONE"]
    rel_l2 = [l for l in kappa_data["r_2"] if l != "NONE"]
    rel_l3 = [l for l in kappa_data["r_3"] if l != "NONE"]
    
    df_labels_r = pd.DataFrame(
        [{"Expert": expert_1, "Label": l} for l in rel_l1]
        + [{"Expert": expert_2, "Label": l} for l in rel_l2]
        + [{"Expert": expert_3, "Label": l} for l in rel_l3]
    )

    if not df_labels_r.empty:
        sns.countplot(data=df_labels_r, x="Label", hue="Expert", palette="magma")
        plt.title("Label Distribution by Expert (Relations)")
        plt.xticks(rotation=45)

    # 6. Ocultamos el último subplot (esquina inferior derecha) para que quede limpio
    plt.subplot(2, 3, 6).axis('off')

    plt.tight_layout()
    plt.savefig(f"{REPORT_OUTPUT}/annotation_report_visuals.png")
    export_visualizations_to_csv(kappa_data, label_dist, status_counts, expert_1, expert_2, expert_3)
    export_kappa_to_latex(kappa_data, expert_1, expert_2, expert_3)


def extract_expert_names_from_path(file1, file2, file3):
    return Path(file1).stem, Path(file2).stem, Path(file3).stem


# --- Ejecución ---
# Para usarlo, simplemente llama a la función principal con tus archivos:
# process_annotations('expert_annotation_1.jsonl', 'expert_annotation_2.jsonl', 'expert_annotation_3.jsonl')

# --- Ejecución ---
# Para usarlo, simplemente llama a la función principal con tus archivos:

process_annotations(MAIN_ANNOTATOR, SECOND_ANNOTATOR, THIRD_ANNOTATOR)
