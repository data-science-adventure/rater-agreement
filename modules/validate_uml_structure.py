import json
import os
from util.uml_ontology import UMLOntology

ontology = UMLOntology()

def audit_uml_dataset(input_path, output_path=None):
    """
    Performs a deep structural audit of a JSONL dataset.
    If output_path is provided, it saves only valid records.
    """
    stats = {
        "total_records": 0,
        "kept_records": 0,
        "dangling_relations": 0,
        "metamodel_violations": 0,
        "missing_keys": 0,
    }

    # 1. Flexible Metamodel: Map of Relation -> List of allowed (Head, Tail) pairs
    VALID_RELATIONS = ontology.get_valid_relations()

    clean_records = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                stats["total_records"] += 1

                # Check for required top-level keys
                if "entities" not in data or "relations" not in data:
                    stats["missing_keys"] += 1
                    continue

                # Map entity IDs for quick lookup
                entities = {e["id"]: e["label"] for e in data["entities"]}

                record_is_valid = True

                for rel in data["relations"]:
                    f_id, t_id = rel.get("from_id"), rel.get("to_id")
                    rel_type = rel.get("type")

                    # A. Check for Dangling Relations
                    if f_id not in entities or t_id not in entities:
                        stats["dangling_relations"] += 1
                        record_is_valid = False
                        continue

                    # B. Check for Metamodel Violations
                    head_label = entities[f_id]
                    tail_label = entities[t_id]

                    if rel_type in VALID_RELATIONS:
                        allowed_patterns = VALID_RELATIONS[rel_type]
                        if (head_label, tail_label) not in allowed_patterns:
                            stats["metamodel_violations"] += 1
                            record_is_valid = False

                if record_is_valid:
                    stats["kept_records"] += 1
                    if output_path:
                        clean_records.append(data)

            except json.JSONDecodeError:
                print(f"⚠️ Line {line_num}: Invalid JSON format. Skipping.")

    # 2. Calculate Structural Integrity Score (SIS)
    total = stats["total_records"]
    violations = (
        stats["dangling_relations"]
        + stats["metamodel_violations"]
        + stats["missing_keys"]
    )
    sis_score = ((total - violations) / total * 100) if total > 0 else 0

    # 3. Export Clean Data
    if output_path and clean_records:
        with open(output_path, "w", encoding="utf-8") as f_out:
            for rec in clean_records:
                f_out.write(json.dumps(rec) + "\n")

    # 4. Generate Report
    print("\n" + "=" * 40)
    print(f"📊 DATASET AUDIT REPORT: {os.path.basename(input_path)}")
    print("=" * 40)
    print(f"Structural Integrity Score (SIS): {sis_score:.2f}%")
    print(f"Total Records Processed:         {stats['total_records']}")
    print("-" * 40)
    print(f"❌ Dangling Relations:           {stats['dangling_relations']}")
    print(f"❌ Metamodel Violations:         {stats['metamodel_violations']}")
    print(f"❌ Missing Essential Keys:       {stats['missing_keys']}")
    print("-" * 40)
    if output_path:
        print(f"💾 Clean records saved to:     {output_path}")
    print("=" * 40 + "\n")

    return stats


# Usage
#audit_uml_dataset("datasets/srs-annotated.jsonl", "datasets/srs-clean.jsonl")
