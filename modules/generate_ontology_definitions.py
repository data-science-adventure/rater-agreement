import pandas as pd
import json
import os
from datetime import datetime
from util.uml_ontology import UMLOntology

# ==========================================
# 1. CONFIGURATION
# ==========================================
SHEET_ID = "1pNVXKtrbsLYJ6ROoflN8Wodxw_b7CMhsSbnYKNApdIc"
LABELS_SHEET = "Labels"
RULES_SHEET = "Indentification_rules"  # As requested

# URLs for CSV export per sheet
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"
LABELS_URL = f"{BASE_URL}&sheet={LABELS_SHEET}"
RULES_URL = f"{BASE_URL}&sheet={RULES_SHEET}"

OUTPUT_DIR = "ontology"
ONTOLOGY_FILE = os.path.join(OUTPUT_DIR, "ontology.json")
DEFINITIONS_FILE = os.path.join(OUTPUT_DIR, "definitions.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "validation_log.txt")

def generate_strict_definitions():
    print(f"📥 Loading logic from {ONTOLOGY_FILE}...")
    
    try:
        # 2. Load Logic Source of Truth
        if not os.path.exists(ONTOLOGY_FILE):
            raise FileNotFoundError(f"Critical Error: {ONTOLOGY_FILE} is missing.")
            
        ontology = UMLOntology.load_from_json(ONTOLOGY_FILE)
        allowed_entities = ontology.get_entities()
        allowed_relations = ontology.get_relations()

        # 3. Read Identification Rules Sheet First
        print(f"📥 Fetching Identification Rules...")
        df_rules = pd.read_csv(RULES_URL)
        df_rules.columns = [c.strip() for c in df_rules.columns]
        
        # Group rules by Label into a dictionary of lists
        # Result: {"ACTOR": ["rule 1", "rule 2"], "CLASS": ["rule A"]}
        rules_map = {}
        if "Label" in df_rules.columns and "Rule" in df_rules.columns:
            # We filter out empty rules and group by uppercase labels
            rules_grouped = df_rules.dropna(subset=['Rule']).groupby('Label')['Rule'].apply(list).to_dict()
            rules_map = {str(k).strip().upper(): v for k, v in rules_grouped.items()}

        # 4. Read Labels Sheet
        print(f"📥 Fetching Labels...")
        df_labels = pd.read_csv(LABELS_URL)
        df_labels.columns = [c.strip() for c in df_labels.columns]

        entities, relations = [], []
        skipped_items = []

        # 5. Process, Filter, and Map Rules
        for _, row in df_labels.iterrows():
            item_id = str(row["Id"]).strip().upper()
            item_type = str(row["Type"]).strip().capitalize()
            
            get_val = lambda col: str(row[col]).strip() if col in df_labels.columns and pd.notna(row[col]) else ""
            
            # Extract identification rules from our map (default to empty list if none found)
            id_rules = rules_map.get(item_id, [])

            entry = {
                "id": item_id,
                "name": item_id.lower(),
                "desc": get_val("Description"),
                "oficial_definition": get_val("Official definition"),
                "alternative_definition": get_val("Alternative definition"),
                "linguistic_definition": get_val("Linguistic definition"),
                "question": get_val("Question"),
                "identification_rules": id_rules
            }

            # Strict validation against ontology logic
            if item_type == "Entity":
                if item_id in allowed_entities:
                    entities.append(entry)
                else:
                    skipped_items.append(f"ENTITY: {item_id}")
            
            elif item_type == "Relation":
                if item_id in allowed_relations:
                    relations.append(entry)
                else:
                    skipped_items.append(f"RELATION: {item_id}")

        # 6. Save JSON
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_data = {"entities": entities, "relations": relations}
        
        with open(DEFINITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)

        # 7. Write Log
        with open(LOG_FILE, "w", encoding="utf-8") as log:
            log.write(f"Strict Sync Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write("="*60 + "\n")
            if not skipped_items:
                log.write("✅ All sheet items are valid per ontology.json\n")
            else:
                log.write(f"⚠️ SKIPPED items (Not in ontology constraints):\n")
                for item in skipped_items:
                    log.write(f"❌ {item}\n")

        print(f"✨ Successfully updated {DEFINITIONS_FILE} with Identification Rules.")
        print(f"📊 Processed {len(entities)} Entities and {len(relations)} Relations.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_strict_definitions()