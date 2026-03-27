import json
import csv
import os
from pathlib import Path

from util.uml_ontology import UMLOntology

from util.config_util import ConfigUtil

config = ConfigUtil.get_config()

ontology = UMLOntology()
# ==========================================
# 1. CONFIGURATION & TAXONOMY
# ==========================================
SOURCE_FILES = config.validate_schema.source_files
REPORT_DIR = config.main.report_dir

PERMITTED_LABELS = ontology.get_entities()

PERMITTED_RELATIONS = ontology.get_relations()


class UMLValidator:
    def __init__(self, input_path, error_path):
        self.input_path = input_path
        self.error_path = error_path
        self.stats = {"records_processed": 0, "errors_found": 0}
        self.error_log = []

    def log_error(self, record_id, error_type, description):
        self.stats["errors_found"] += 1
        self.error_log.append(
            {"id": record_id, "error_type": error_type, "description": description}
        )

    def validate_dataset(self):
        if not os.path.exists(self.input_path):
            print(f"❌ Error: Input file {self.input_path} not found.")
            return

        print(f"🔍 Starting validation on: {self.input_path}...")

        with open(self.input_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                self.stats["records_processed"] += 1
                try:
                    data = json.loads(line)
                    record_id = data.get("sent_id", f"line_{line_idx}")
                    self._validate_record(data, record_id)
                except json.JSONDecodeError:
                    self.log_error(
                        f"line_{line_idx}",
                        "INVALID_JSON",
                        "Line is not a valid JSON object.",
                    )

        self._write_error_report()
        self._print_summary()

    def _validate_record(self, data, record_id):
        # --- 1. Top-Level Validation (Updated) ---

        # Original core fields
        if not isinstance(data.get("sent_id"), int) or data["sent_id"] < 0:
            self.log_error(
                record_id,
                "TOP_LEVEL_ERROR",
                "ID must be a non-null, non-negative integer.",
            )

        text = data.get("text")
        if not text or not isinstance(text, str):
            self.log_error(
                record_id,
                "TOP_LEVEL_ERROR",
                "Text must be a non-null, non-empty string.",
            )
            return  # Critical failure: cannot check spans without text

        # NEW: Mandatory metadata fields
        metadata_fields = ["source", "project_id", "type"]
        for field in metadata_fields:
            val = data.get(field)
            if not val or not isinstance(val, str) or not val.strip():
                self.log_error(
                    record_id,
                    "METADATA_MISSING",
                    f"'{field}' must be a non-null, non-empty string.",
                )

        # Data structure presence
        entities = data.get("entities")
        relations = data.get("relations")
        if not isinstance(entities, list):
            self.log_error(record_id, "TOP_LEVEL_ERROR", "'entities' must be a list.")
            entities = []
        if not isinstance(relations, list):
            self.log_error(record_id, "TOP_LEVEL_ERROR", "'relations' must be a list.")
            relations = []

        # --- 2. Entity-Level Validation ---
        entity_ids = set()
        for ent in entities:
            ent_id = ent.get("id")
            if ent_id in entity_ids:
                self.log_error(
                    record_id, "ENTITY_ID_NOT_UNIQUE", f"Duplicate Entity ID: {ent_id}"
                )
            entity_ids.add(ent_id)

            if not isinstance(ent_id, int) or ent_id < 0:
                self.log_error(
                    record_id,
                    "ENTITY_FORMAT_ERROR",
                    f"Entity ID {ent_id} must be int >= 0",
                )

            label = ent.get("label")
            if label not in PERMITTED_LABELS:
                self.log_error(
                    record_id,
                    "INVALID_ENTITY_LABEL",
                    f"Label '{label}' not in taxonomy.",
                )

            start = ent.get("start_offset")
            end = ent.get("end_offset")
            if not (
                isinstance(start, int) and isinstance(end, int) and 0 <= start < end
            ):
                self.log_error(
                    record_id,
                    "OFFSET_LOGIC_ERROR",
                    f"Entity {ent_id} has invalid offsets.",
                )
                continue

            if ent.get("text") != None:
                expected_text = ent.get("text")
                actual_slice = text[start:end]
                if actual_slice != expected_text:
                    self.log_error(
                        record_id,
                        "SPAN_TEXT_MISMATCH",
                        f"Entity {ent_id}: Slice '{actual_slice}' != '{expected_text}'",
                    )

        # --- 3. Relation-Level Validation ---
        relation_ids = set()
        for rel in relations:
            rel_id = rel.get("id")
            if rel_id in relation_ids:
                self.log_error(
                    record_id,
                    "RELATION_ID_NOT_UNIQUE",
                    f"Duplicate Relation ID: {rel_id}",
                )
            relation_ids.add(rel_id)

            rel_type = rel.get("type")
            if rel_type not in PERMITTED_RELATIONS:
                self.log_error(
                    record_id,
                    "INVALID_RELATION_TYPE",
                    f"Relation type '{rel_type}' is invalid.",
                )

            from_id = rel.get("from_id")
            to_id = rel.get("to_id")
            if from_id not in entity_ids:
                self.log_error(
                    record_id,
                    "RELATION_TARGET_NOT_FOUND",
                    f"from_id {from_id} not in entities.",
                )
            if to_id not in entity_ids:
                self.log_error(
                    record_id,
                    "RELATION_TARGET_NOT_FOUND",
                    f"to_id {to_id} not in entities.",
                )

    def _write_error_report(self):
        with open(self.error_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "error_type", "description"])
            writer.writeheader()
            writer.writerows(self.error_log)

    def _print_summary(self):
        print("\n" + "=" * 50)
        print("📊 SCHEMA VALIDATION REPORT")
        print("=" * 50)
        print(f"✅ Total Records Scanned: {self.stats['records_processed']}")
        print(f"❌ Total Errors Flagged:   {self.stats['errors_found']}")
        if self.stats["errors_found"] > 0:
            print(f"📄 Details exported to:   {self.error_path}")
        print("=" * 50 + "\n")


if __name__ == "__main__":

    for input_path in SOURCE_FILES:
        file_name = Path(input_path).stem
        error_log_path = f"{REPORT_DIR}/schema_errors_{file_name}.csv"
        validator = UMLValidator(input_path, error_log_path)
        validator.validate_dataset()
