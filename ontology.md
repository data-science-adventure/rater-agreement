
## Ontology definition:

The file `modules/util/uml_ontology.py` has the ontology definition.

## Taxonomy of UML Elements

The taxonomy categorizes your entities into a logical hierarchy, moving from general concepts to specific data types.

### **1. Structural Elements (Static)**

These represent the "nouns" or the data structure of the system.

- **Class**: The primary template for data and behavior.
- **Property/Feature**:
    - **Method**: A functional capability or operation.
    - **Attribute**: A piece of data, further specialized by type:
        - **String**: Textual data.
        - **Date**: Temporal data.
        - **Boolean**: True/False flags.
        - **Numeric**: Specialized into **Integer**, **Long**, and **Float**.
        - **Blob**: Binary large objects (images, files).
            
### **2. Behavioral Elements (Dynamic)**

These represent the "verbs" or how the system interacts with the world.

- **System Boundary**: The container or scope of the software.
- **Actor**: An external entity (person or system) that initiates action.
- **Use Case**: A discrete goal or functional requirement.

## Ontology of SRS Relationships

The ontology defines the set of rules and predicates that govern how the taxonomic elements are allowed to link together.

### **1. Functional Interaction Rules**

These rules define how users and goals interact.

- **`PERFORMS`**: Defines an agency relationship.    
    - _Axiom_: Only an **Actor** can perform a **Use Case**.
- **`CONTAINS`**: Defines a scoping relationship.
    - _Axiom_: A **System Boundary** encapsulates **Use Cases**.
- **`INCLUDE` / `EXTENDS`**: Define functional dependency.
    - _Axiom_: These are strictly peer-to-peer relationships between two **Use Cases**.

### **2. Structural Ownership Rules**

These define the internal composition of a class.

- **`OWNS`**: A strong composition relationship.
    - _Rule_: A **Class** or **Actor** "owns" its **Attributes** and **Methods**. If the Class is deleted, these properties cease to exist.
- **`IS_A`**: Represents inheritance.
    - _Rule_: A child entity inherits the properties of the parent. (e.g., a _Manager_ is an _Actor_).

### **3. Associative Connectivity Rules**

These define how independent objects "know" about each other.

- **`ASSOCIATION`**: A general connection between two entities.
- **`ONE_TO_ONE`, `ONE_TO_MANY`, `MANY_TO_MANY`**: Multiplicity constraints that define the volume of the relationship.
- **`PART_OF`**: An aggregation where one class is a component of another, but can exist independently.
- **`DEPENDS_ON`**: A weak relationship where a change in one class may affect another.



Formal Summary Table

| **Relationship Category** | **Predicate** | **Source** | **Target** | **Semantic Meaning**        |
| ------------------------- | ------------- | ---------- | ---------- | --------------------------- |
| **Behavioral**            | `PERFORMS`    | Actor      | Use Case   | Execution of a goal.        |
| **Structural**            | `OWNS`        | Class      | Attribute  | Property definition.        |
| **Hierarchical**          | `IS_A`        | Any        | Same Type  | Specialization/Inheritance. |
| **Architectural**         | `CONTAINS`    | Boundary   | Use Case   | Scope definition.           |
| **Relational**            | `PART_OF`     | Class      | Class      | Aggregation/Composition.    |
