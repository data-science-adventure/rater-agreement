import json
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CohenKappaConfig:
    report_output: str
    main_annotator: str
    second_annotator: str
    third_annotator: str

@dataclass
class ProjectConfig:
    # We use Optional in case "compute_cohens_kappa" is missing in some JSONs
    compute_cohens_kappa: Optional[CohenKappaConfig] = None
    validate_shema: dict = field(default_factory=dict)

class ConfigUtil:
    @staticmethod
    def get_config(config_path: str = "config.json") -> ProjectConfig:
        """Loads JSON and maps it into a ProjectConfig object."""
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Map the sub-dictionary to the CohenKappaConfig class
        kappa_data = data.get("compute_cohens_kappa")
        kappa_obj = CohenKappaConfig(**kappa_data) if kappa_data else None
        
        # Return the top-level object
        return ProjectConfig(
            compute_cohens_kappa=kappa_obj,
            validate_shema=data.get("validate_shema", {})
        )