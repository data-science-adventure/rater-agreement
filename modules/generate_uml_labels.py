import pandas as pd
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Replace with your actual Google Sheet ID
SHEET_ID = "1pNVXKtrbsLYJ6ROoflN8Wodxw_b7CMhsSbnYKNApdIc"
SHEET_NAME = "Labels" # Change if your sheet has a different tab name

# The export URL for Google Sheets as CSV
GSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# CONFIGURABLE: Choose which column to map to the "desc" field
# Options: "Official definition", "Alternative definition", "Questions", "Other names"
DESC_SOURCE_COLUMN = "Description"
OFFICIAL_DEFINITION_SOURCE_COLUMN = "Official definition"
ALTERNATIVE_DEFINITION_SOURCE_COLUMN = "Alternative definition"
QUESTION_SOURCE_COLUMN = "Question"

OUTPUT_FILE = "ontology/uml_labels.py"

def generate_uml_labels():
    print(f"📥 Fetching data from Google Sheets...")
    
    try:
        # 2. Read the Google Sheet
        df = pd.read_csv(GSHEET_URL)
        
        # Clean column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]

        entities = []
        relations = []

        # 3. Process Rows
        for _, row in df.iterrows():
            item_id = str(row["Id"]).strip()
            item_type = str(row["Type"]).strip().capitalize()
            # Handle potential empty cells in the description column
            description = str(row[DESC_SOURCE_COLUMN]).strip() if pd.notna(row[DESC_SOURCE_COLUMN]) else item_id.lower()
            oficial_definition = str(row[OFFICIAL_DEFINITION_SOURCE_COLUMN]).strip() if pd.notna(row[OFFICIAL_DEFINITION_SOURCE_COLUMN]) else item_id.lower()
            alternative_definition = str(row[ALTERNATIVE_DEFINITION_SOURCE_COLUMN]).strip() if pd.notna(row[ALTERNATIVE_DEFINITION_SOURCE_COLUMN]) else item_id.lower()
            question = str(row[QUESTION_SOURCE_COLUMN]).strip() if pd.notna(row[QUESTION_SOURCE_COLUMN]) else item_id.lower()

            entry = {
                "id": item_id,
                "name": item_id.lower(),
                "desc": description,
                "oficial_definition": oficial_definition,
                "alternative_definition": alternative_definition,
                "question": question,
            }

            if item_type == "Entity":
                entities.append(entry)
            elif item_type == "Relation":
                relations.append(entry)

        # 4. Generate the .py file content
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("# This file is auto-generated from Google Sheets\n\n")
            
            f.write("ENTITY_LABELS = [\n")
            for ent in entities:
                f.write(f"    {{\n")
                f.write(f"        'id': '{ent['id']}',\n")
                f.write(f"        'name': '{ent['name']}',\n")
                f.write(f"        'desc': \"{ent['desc']}\"\n")
                f.write(f"    }},\n")
            f.write("]\n\n")

            f.write("RELATION_LABELS = [\n")
            for rel in relations:
                f.write(f"    {{\n")
                f.write(f"        'id': '{rel['id']}',\n")
                f.write(f"        'name': '{rel['name']}',\n")
                f.write(f"        'desc': \"{rel['desc']}\"\n")
                f.write(f"    }},\n")
            f.write("]\n")

        print(f"✨ Successfully created {OUTPUT_FILE} with {len(entities)} entities and {len(relations)} relations.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_uml_labels()