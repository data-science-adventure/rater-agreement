import json


class UMLOntology:
    def __init__(self, data: dict):
        self.attr_group = data.get("attribute_entities", [])
        self.raw_relations = data.get("relations", {})
        self.VALID_RELATIONS = self._build_ontology()

    @classmethod
    def load_from_json(cls, file_path: str = "ontology.json"):
        """Factory method to initialize the class directly from a file."""
        with open(file_path, "r") as f:
            return cls(json.load(f))

    def _build_ontology(self) -> dict:
        processed = {}
        for rel_name, structure in self.raw_relations.items():
            if isinstance(structure, dict):
                pairs = []
                for source, targets in structure.items():
                    for t in targets:
                        if t == "attribute_entities":
                            pairs.extend([(source, attr) for attr in self.attr_group])
                        else:
                            pairs.append((source, t))
                processed[rel_name] = pairs
            else:
                processed[rel_name] = [tuple(pair) for pair in structure]
        return processed

    def print_ontology(self):
        """Prints a formatted summary of all relations and their pairs."""
        print("\n" + "=" * 50)
        print(f"{'RELATION TYPE':<25} | {'VALID PAIRS'}")
        print("-" * 50)

        for rel, pairs in sorted(self.VALID_RELATIONS.items()):
            # Format pairs as (A -> B) for better readability
            pair_strings = [f"({a} → {b})" for a, b in pairs]

            # Print the first pair on the same line as the relation
            print(f"{rel:<25} | {pair_strings[0]}")

            # Print subsequent pairs indented for clarity
            for extra_pair in pair_strings[1:]:
                print(f"{' ':<25} | {extra_pair}")
            print("-" * 50)

        print(f"Total Entities: {len(self.get_entities())}")
        print(f"Total Relations: {len(self.get_relations())}")
        print("=" * 50 + "\n")

    def get_valid_relations(self):
        return self.VALID_RELATIONS

    def get_entities(self):
        entities = {
            e for pairs in self.VALID_RELATIONS.values() for pair in pairs for e in pair
        }
        return sorted(list(entities))

    def get_relations(self):
        return sorted(list(self.VALID_RELATIONS.keys()))
