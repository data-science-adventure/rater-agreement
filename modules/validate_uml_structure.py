import json
import os
import csv
from pathlib import Path
from util.uml_ontology import UMLOntology
from util.config_util import ConfigUtil

config = ConfigUtil.get_config()

ontology = UMLOntology()

SOURCE_FILES = config.validate_uml_structure.source_files
REPORT_DIR = config.main.report_dir


def audit_uml_dataset(input_path, error_log_path="sis_errors.csv", output_path=None):
    """
    Performs a structural audit with streaming writes and detailed CSV error logging,
    including the specific text of the entities involved.
    """
    stats = {
        "total_records": 0,
        "kept_records": 0,
        "dangling_relations": 0,
        "metamodel_violations": 0,
        "missing_keys": 0,
    }

    VALID_RELATIONS = ontology.get_valid_relations()

    # 1. Updated CSV headers with head_text and tail_text
    error_headers = [
        "id",
        "sent_id",
        "error_type",
        "rel_id",
        "head_label",
        "head_text",
        "tail_label",
        "tail_text",
        "relation_type",
        "text",
    ]

    with open(input_path, "r", encoding="utf-8") as f_in, open(
        error_log_path, "w", encoding="utf-8", newline=""
    ) as f_err:

        error_writer = csv.DictWriter(f_err, fieldnames=error_headers)
        error_writer.writeheader()

        f_out = open(output_path, "w", encoding="utf-8") if output_path else None

        for line_num, line in enumerate(f_in, 1):
            try:
                data = json.loads(line)
                stats["total_records"] += 1

                rec_id = data.get("id", "N/A")
                sent_id = data.get("sent_id", "N/A")
                text_content = data.get("text", "N/A")

                if "entities" not in data or "relations" not in data:
                    stats["missing_keys"] += 1
                    error_writer.writerow(
                        {
                            "id": rec_id,
                            "sent_id": sent_id,
                            "error_type": "Missing Keys",
                            "text": text_content,
                        }
                    )
                    continue

                # 2. Store both label and text for each entity ID
                entities = {
                    e["id"]: {
                        "label": e.get("label", "Unknown"),
                        "text": text_content[
                            e.get("start_offset") : e.get("end_offset")
                        ],
                    }
                    for e in data["entities"]
                }

                record_is_valid = True

                for rel in data["relations"]:
                    rel_id = rel.get("id", "N/A")
                    f_id, t_id = rel.get("from_id"), rel.get("to_id")
                    rel_type = rel.get("type")

                    # A. Check for Dangling Relations
                    if f_id not in entities or t_id not in entities:
                        stats["dangling_relations"] += 1
                        record_is_valid = False
                        error_writer.writerow(
                            {
                                "id": rec_id,
                                "sent_id": sent_id,
                                "rel_id": rel_id,
                                "error_type": "Dangling Relation",
                                "relation_type": rel_type,
                                "text": text_content,
                            }
                        )
                        continue

                    # B. Check for Metamodel Violations
                    head_info = entities[f_id]
                    tail_info = entities[t_id]

                    head_label, head_text = head_info["label"], head_info["text"]
                    tail_label, tail_text = tail_info["label"], tail_info["text"]

                    if rel_type in VALID_RELATIONS:
                        allowed_patterns = VALID_RELATIONS[rel_type]
                        if (head_label, tail_label) not in allowed_patterns:
                            stats["metamodel_violations"] += 1
                            record_is_valid = False
                            # 3. Log with specific entity text
                            error_writer.writerow(
                                {
                                    "id": rec_id,
                                    "sent_id": sent_id,
                                    "rel_id": rel_id,
                                    "error_type": "Metamodel Violation",
                                    "head_label": head_label,
                                    "head_text": head_text,
                                    "tail_label": tail_label,
                                    "tail_text": tail_text,
                                    "relation_type": rel_type,
                                    "text": text_content,
                                }
                            )

                if record_is_valid:
                    stats["kept_records"] += 1
                    if f_out:
                        f_out.write(json.dumps(data) + "\n")

            except json.JSONDecodeError:
                print(f"⚠️ Line {line_num}: Invalid JSON format. Skipping.")

        if f_out:
            f_out.close()

    # Calculate and Print Report
    total = stats["total_records"]
    violations = (
        stats["dangling_relations"]
        + stats["metamodel_violations"]
        + stats["missing_keys"]
    )
    sis_score = ((total - violations) / total * 100) if total > 0 else 0

    print_report(input_path, sis_score, stats, output_path, error_log_path)
    return stats


def print_report(input_path, sis_score, stats, output_path, error_log_path):
    print("\n" + "=" * 55)
    print(f"📊 DATASET AUDIT REPORT: {os.path.basename(input_path)}")
    print("=" * 55)
    print(f"Structural Integrity Score (SIS): {sis_score:.2f}%")
    print(f"Total Records Processed:         {stats['total_records']}")
    print(f"Valid Records Saved:             {stats['kept_records']}")
    print("-" * 55)
    print(f"❌ Dangling Relations:           {stats['dangling_relations']}")
    print(f"❌ Metamodel Violations:         {stats['metamodel_violations']}")
    print(f"❌ Missing Essential Keys:       {stats['missing_keys']}")
    print("-" * 55)
    print(f"📝 Detailed Error Log:           {error_log_path}")
    if output_path:
        print(f"💾 Clean records saved to:       {output_path}")
    print("=" * 55 + "\n")


for input_path in SOURCE_FILES:
    file_name = Path(input_path).stem
    error_log_path = f"{REPORT_DIR}/sis_errors_{file_name}.csv"
    audit_uml_dataset(input_path, error_log_path)
