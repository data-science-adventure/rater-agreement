import os
import sys
from modules.util.uml_ontology import UMLOntology
# Import your generator script (assuming it's named sync_ontology.py)
# import sync_ontology 

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_menu():
    # Load the ontology
    try:
        ontology = UMLOntology.load_from_json("ontology/ontology.json")
    except Exception as e:
        print(f"❌ Error loading ontology: {e}")
        return

    while True:
        print("\n" + "═"*40)
        print(" 🏛️  UML ONTOLOGY INTERACTIVE MANAGER")
        print("═"*40)
        print("1. 📋 Print Full Ontology Table")
        print("2. 🔗 List All Relation Types")
        print("3. 🧩 List All Valid Entities")
        print("4. ✅ Validate a Triplet (S-R-T)")
        print("5. 🔍 Search by Entity Name")
        print("6. 🔄 Sync from Google Sheets (Definitions)")
        print("0. 🚪 Exit")
        print("═"*40)

        choice = input("\nSelect an option: ").strip()

        if choice == '1':
            clear_screen()
            ontology.print_ontology()
        
        elif choice == '2':
            print("\nAvailable Relations:")
            for rel in ontology.get_relations():
                print(f"  • {rel}")
        
        elif choice == '3':
            print("\nAvailable Entities:")
            for ent in ontology.get_entities():
                print(f"  • {ent}")

        elif choice == '4':
            print("\n--- Triplet Validation ---")
            s = input("Source Entity: ").strip()
            r = input("Relation Type: ").strip()
            t = input("Target Entity: ").strip()
            if ontology.validate_triplet(s, r, t):
                print(f"\n✅ VALID: ({s}) --[{r}]--> ({t})")
            else:
                print(f"\n❌ INVALID: This relationship is not allowed.")

        elif choice == '5':
            name = input("\nEnter Entity name to search: ").strip()
            ontology.search_by_entity(name)

        elif choice == '6':
            print("\n🔄 Running Sync Script...")
            # If you want to trigger your sync script:
            # sync_ontology.generate_strict_definitions()
            # Then reload the ontology
            # ontology = UMLOntology.load_from_json("ontology/ontology.json")
            print("Done! (Ensure sync logic is imported in main.py)")

        elif choice == '0':
            print("Goodbye!")
            break
        
        else:
            print("⚠️ Invalid selection. Try again.")
        
        input("\nPress Enter to return to menu...")
        clear_screen()

if __name__ == "__main__":
    main_menu()