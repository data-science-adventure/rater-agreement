class UMLOntology:
    VALID_RELATIONS = {
        "PERFORMS": [("ACTOR", "USE_CASE")],
        "CONTAINS": [("SYSTEM_BOUNDARY", "USE_CASE")],
        "INCLUDE": [("USE_CASE", "USE_CASE")],
        "EXTENDS": [("USE_CASE", "USE_CASE")],
        "IS_A": [("ACTOR", "ACTOR"), ("USE_CASE", "USE_CASE"), ("CLASS", "CLASS")],
        "OWNS": [
            ("CLASS", "METHOD"),
            ("CLASS", "ATTRIBUTE"),
            ("CLASS", "STRING_ATTRIBUTE"),
            ("CLASS", "DATE_ATTRIBUTE"),
            ("CLASS", "BLOB_ATTRIBUTE"),
            ("CLASS", "BOOLEAN_ATTRIBUTE"),
            ("CLASS", "LONG_ATTRIBUTE"),
            ("CLASS", "INTEGER_ATTRIBUTE"),
            ("CLASS", "FLOAT_ATTRIBUTE"),
            ("ACTOR", "ATTRIBUTE"),
            ("ACTOR", "STRING_ATTRIBUTE"),
            ("ACTOR", "DATE_ATTRIBUTE"),
            ("ACTOR", "BLOB_ATTRIBUTE"),
            ("ACTOR", "BOOLEAN_ATTRIBUTE"),
            ("ACTOR", "LONG_ATTRIBUTE"),
            ("ACTOR", "INTEGER_ATTRIBUTE"),
            ("ACTOR", "FLOAT_ATTRIBUTE"),
        ],
        "DEPENDS_ON": [("CLASS", "CLASS")],
        "ASSOCIATION": [("CLASS", "CLASS"), ("ACTOR", "CLASS")],
        "PART_OF": [("CLASS", "CLASS")],
        "ONE_TO_ONE_ASSOCIATION": [("CLASS", "CLASS"), ("ACTOR", "CLASS")],
        "ONE_TO_MANY_ASSOCIATION": [("CLASS", "CLASS"), ("ACTOR", "CLASS")],
        "MANY_TO_MANY_ASSOCIATION": [("CLASS", "CLASS"), ("ACTOR", "CLASS")],
    }

    def get_valid_relations(self):
        return self.VALID_RELATIONS

    def get_entities(self):
        """Returns a unique list of all entity types found in the values."""
        entities = set()
        for pairs_list in self.VALID_RELATIONS.values():
            for entity_a, entity_b in pairs_list:
                entities.add(entity_a)
                entities.add(entity_b)
        return sorted(list(entities))

    def get_relations(self):
        """Returns a unique list of all relation names (the keys)."""
        return sorted(list(self.VALID_RELATIONS.keys()))
