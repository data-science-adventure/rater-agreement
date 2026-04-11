import pandas as pd
import json
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
SHEET_ID = "1pNVXKtrbsLYJ6ROoflN8Wodxw_b7CMhsSbnYKNApdIc"
SHEET_NAME = "Labels"
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# Column Mapping
DESC_COL = "Description"
OFFICIAL_COL = "Official definition"
ALT_COL = "Alternative definition"
QUESTION_COL = "Question"

# Target Files
OUTPUT_DIR = "ontology"
DEFINITIONS_FILE = os.path.join(OUTPUT_DIR, "definitions.json")

def generate_definitions():
    print(f"📥 Fetching labels from Google Sheets...")
    
    try:
        # 2. Read and Clean Data
        df = pd.read_csv(GSHEET_URL)
        df.columns = [c.strip() for c in df.columns]

        entities = []
        relations = []

        # 3. Process Rows
        for _, row in df.iterrows():
            item_id = str(row["Id"]).strip().upper()
            item_type = str(row["Type"]).strip().capitalize()
            
            # Helper to handle empty cells
            get_val = lambda col: str(row[col]).strip() if col in df.columns and pd.notna(row[col]) else ""

            entry = {
                "id": item_id,
                "name": item_id.lower(),
                "desc": get_val(DESC_COL),
                "oficial_definition": get_val(OFFICIAL_COL),
                "alternative_definition": get_val(ALT_COL),
                "question": get_val(QUESTION_COL)
            }

            if item_type == "Entity":
                entities.append(entry)
            elif item_type == "Relation":
                relations.append(entry)

        # 4. Construct the definitions structure
        definitions_data = {
            "entities": entities,
            "relations": relations
        }

        # 5. Save to definitions.json
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(DEFINITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(definitions_data, f, indent=4, ensure_ascii=False)

        print(f"✨ Successfully created {DEFINITIONS_FILE}")
        print(f"📦 Entities: {len(entities)} | Relations: {len(relations)}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_definitions()