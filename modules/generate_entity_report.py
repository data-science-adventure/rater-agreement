import json
import csv
import os

def generate_entity_csv():
    input_file = "report/gold_standard.jsonl"
    output_file = "report/gold_standard_entities.csv"
    
    # Ensure the directory exists
    os.makedirs("report", exist_ok=True)

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f_in:
            # Prepare the CSV file
            with open(output_file, 'w', encoding='utf-8', newline='') as f_out:
                writer = csv.writer(f_out)
                
                # Write the header
                writer.writerow(["sent_id", "Entity label", "Entity text"])
                
                count = 0
                for line in f_in:
                    if not line.strip():
                        continue
                    
                    # Parse the JSON line
                    data = json.loads(line)
                    sent_id = data.get("sent_id")
                    entities = data.get("entities", [])
                    
                    # Extract each entity
                    for ent in entities:
                        label = ent.get("label")
                        text = ent.get("text")
                        writer.writerow([sent_id, label, text])
                        count += 1
                        
        print(f"Success: {count} entities exported to {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_entity_csv()