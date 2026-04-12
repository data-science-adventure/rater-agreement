import pandas as pd
import json
import os
from datetime import datetime
from util.uml_ontology import UMLOntology

# ==========================================
# 1. CONFIGURATION
# ==========================================
SHEET_ID = "1pNVXKtrbsLYJ6ROoflN8Wodxw_b7CMhsSbnYKNApdIc"
SHEET_NAME = "Labels"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

OUTPUT_DIR = "ontology"
ONTOLOGY_FILE = os.path.join(OUTPUT_DIR, "ontology.json")
DEFINITIONS_FILE = os.path.join(OUTPUT_DIR, "definitions.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "validation_log.txt")

def generate_strict_definitions():
    print(f"📥 Loading logic from {ONTOLOGY_FILE}...")
    
    try:
        # 2. Initialize your class for validation
        if not os.path.exists(ONTOLOGY_FILE):
            raise FileNotFoundError(f"Critical Error: {ONTOLOGY_FILE} is missing. Cannot validate.")
            
        ontology = UMLOntology.load_from_json(ONTOLOGY_FILE)
        allowed_entities = ontology.get_entities()
        allowed_relations = ontology.get_relations()

        # 3. Read Google Sheet
        df = pd.read_csv(GSHEET_URL)
        df.columns = [c.strip() for c in df.columns]

        entities, relations = [], []
        skipped_items = []

        # 4. Process and Filter
        for _, row in df.iterrows():
            item_id = str(row["Id"]).strip().upper()
            item_type = str(row["Type"]).strip().capitalize()
            
            get_val = lambda col: str(row[col]).strip() if col in df.columns and pd.notna(row[col]) else ""
            
            entry = {
                "id": item_id,
                "name": item_id.lower(),
                "desc": get_val("Description"),
                "oficial_definition": get_val("Official definition"),
                "alternative_definition": get_val("Alternative definition"),
                "question": get_val("Question")
            }

            if item_type == "Entity":
                if item_id in allowed_entities:
                    entities.append(entry)
                else:
                    skipped_items.append(f"ENTITY: {item_id} (Reason: Not found in ontology constraints)")
            
            elif item_type == "Relation":
                if item_id in allowed_relations:
                    relations.append(entry)
                else:
                    skipped_items.append(f"RELATION: {item_id} (Reason: Not found in ontology constraints)")

        # 5. Save ONLY validated items to definitions.json
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(DEFINITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({"entities": entities, "relations": relations}, f, indent=4, ensure_ascii=False)

        # 6. Write Log File for skipped items
        with open(LOG_FILE, "w", encoding="utf-8") as log:
            log.write(f"Strict Sync Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write("="*60 + "\n")
            if not skipped_items:
                log.write("✅ Perfect Sync: All items in Sheet are mapped in Ontology.\n")
            else:
                log.write(f"⚠️ SKIPPED {len(skipped_items)} items found in Sheet but NOT in Ontology:\n")
                for item in skipped_items:
                    log.write(f"❌ {item}\n")

        print(f"✨ Successfully created {DEFINITIONS_FILE}")
        print(f"✅ Included: {len(entities)} Entities, {len(relations)} Relations")
        
        if skipped_items:
            print(f"⚠️ Skipped {len(skipped_items)} items. See {LOG_FILE} for the list.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_strict_definitions()