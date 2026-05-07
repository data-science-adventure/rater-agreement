import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def generate_gold_standard_report():
    """Reads gold_standard.jsonl and generates a statistical report image."""
    input_file = "report/gold_standard.jsonl"
    output_file = "report/gold_standard_stats.png"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # 1. Load the JSONL data
    data = []
    entities_list = []
    relations_list = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            data.append(item)
            for ent in item.get("entities", []):
                entities_list.append(ent["label"])
            for rel in item.get("relations", []):
                relations_list.append(rel["type"])

    df = pd.DataFrame(data)
    
    # 2. Setup Figure
    # Using 'seaborn-v0_8' to avoid further warnings
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Gold Standard Dataset Analysis', fontsize=20, fontweight='bold')

    # Plot A: Entity Label Distribution
    if entities_list:
        ent_counts = pd.Series(entities_list).value_counts().reset_index()
        ent_counts.columns = ['Entity', 'Count']
        # FIX: Assign y to hue and set legend=False
        sns.barplot(
            data=ent_counts, 
            x='Count', 
            y='Entity', 
            ax=axes[0,0], 
            hue='Entity', 
            palette="viridis", 
            legend=False
        )
        axes[0,0].set_title("Entity Distribution", fontsize=14)

    # Plot B: Relation Type Distribution
    if relations_list:
        rel_counts = pd.Series(relations_list).value_counts().reset_index()
        rel_counts.columns = ['Relation', 'Count']
        # FIX: Assign y to hue and set legend=False
        sns.barplot(
            data=rel_counts, 
            x='Count', 
            y='Relation', 
            ax=axes[0,1], 
            hue='Relation', 
            palette="magma", 
            legend=False
        )
        axes[0,1].set_title("Relation Distribution", fontsize=14)

    # Plot C: Requirements by Source
    if 'source' in df.columns:
        source_counts = df['source'].value_counts()
        axes[1,0].pie(source_counts, labels=source_counts.index, autopct='%1.1f%%', 
                      colors=sns.color_palette("pastel"), startangle=140)
        axes[1,0].set_title("Data Sources", fontsize=14)

    # Plot D: Sentence Length (Words)
    if 'text' in df.columns:
        df['word_count'] = df['text'].apply(lambda x: len(x.split()))
        sns.histplot(df['word_count'], bins=20, ax=axes[1,1], kde=True, color="skyblue")
        axes[1,1].set_title("Requirement Length (Word Count)", fontsize=14)
        axes[1,1].set_xlabel("Number of Words")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # 3. Save the report
    os.makedirs("report", exist_ok=True)
    plt.savefig(output_file, dpi=300)
    plt.close()
    
    print(f"Success: Statistical report saved in {output_file}")

def generate_gold_standard_latex_report():
    """Reads gold_standard.jsonl and generates a .tex file with native TikZ plots."""
    import json
    import os
    from collections import Counter

    input_file = "report/gold_standard.jsonl"
    output_file = "report/gold_standard_stats.tex"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # 1. Aggregate Data
    entities = []
    relations = []
    sources = []
    word_counts = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            entities.extend([e["label"].replace("_", r"\_") for e in item.get("entities", [])])
            relations.extend([r["type"].replace("_", r"\_") for r in item.get("relations", [])])
            sources.append(item.get("source", "Unknown").replace("_", r"\_"))
            word_counts.append(len(item.get("text", "").split()))

    # Process distributions
    ent_data = Counter(entities).most_common()
    rel_data = Counter(relations).most_common()
    src_data = Counter(sources).most_common()
    
    # Bin word counts (e.g., bins of 10)
    bins = [0] * 7 # 0-10, 10-20, ..., 60+
    for wc in word_counts:
        idx = min(wc // 10, 6)
        bins[idx] += 1
    bin_labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "51-60", "60+"]

    # 2. Helper to generate PGFPlots bar chart code
    def get_bar_chart(title, data, color, height="4.5cm"):
        coords = " ".join([f"({{{label}}},{count})" for label, count in data])
        labels = ", ".join([f"{{{label}}}" for label, count in data])
        return rf"""
    \begin{{axis}}[
        title={{{title}}},
        symbolic x coords={{{labels}}}, xtick=data,
        compact_plot
    ]
        \addplot [fill=barBlue, draw=none] coordinates {{{coords}}};
    \end{{axis}}"""

    # 3. Assemble LaTeX
    tex_content = [
        r"\definecolor{barBlue}{RGB}{53, 133, 151}",
        r"\pgfplotsset{",
        r"    compact_plot/.style={",
        r"        ybar, ",
        r"        width=0.48\textwidth, ",
        r"        height=4.5cm,",
        r"        bar width=7pt,",
        r"        xtick=data,",
        r"        xticklabel style={rotate=45, anchor=east, font=\tiny},",
        r"        ylabel={}, ymin=0,",
        r"        axis x line*=bottom,",
        r"        axis y line*=left,",
        r"        ymajorgrids=true,",
        r"        grid style={dashed, gray!30},",
        r"        nodes near coords, every node near coord/.append style={font=\tiny},",
        r"        bar width=12pt, fill={rgb:red,1;green,2;blue,3}, draw=none",
        r"    }",
        r"}",
        r"\begin{tikzpicture}",
        get_bar_chart("Entity Distribution", ent_data, "{rgb:red,1;green,2;blue,3}"),
        rf"\begin{{scope}}[shift={{(0.52\textwidth,0)}}]",
        get_bar_chart("Relation Distribution", rel_data, "{rgb:red,3;green,1;blue,2}"),
        r"\end{scope}",
        rf"\begin{{scope}}[shift={{(0,-6cm)}}]",
        get_bar_chart("Data Sources", src_data, "{rgb:red,2;green,3;blue,1}"),
        r"\end{scope}",
        rf"\begin{{scope}}[shift={{(0.52\textwidth,-6cm)}}]",
        get_bar_chart("Word Count Distribution", list(zip(bin_labels, bins)), "gray!50"),
        r"\end{scope}",
        r"\end{tikzpicture}"
    ]

    os.makedirs("report", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(tex_content))
    print(f"Success: Gold standard LaTeX stats generated in {output_file}")


if __name__ == "__main__":
    generate_gold_standard_report()       # Generates the PNG
    generate_gold_standard_latex_report() # Generates the .tex for your main document