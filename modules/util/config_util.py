import json
import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class MainConfig:
    report_dir: str
    annotators_dir: str
    project_id: int

@dataclass
class CohenKappaConfig:
    main_annotator: str
    second_annotator: str
    third_annotator: str

@dataclass
class UploadConfig:
    token_file: str
    credentials_file: str

@dataclass
class ValidateSchemaConfig:
    # Defaults to an empty list if not found
    source_files: List[str] = field(default_factory=list)

@dataclass
class ProjectConfig:
    main: MainConfig
    compute_cohens_kappa: Optional[CohenKappaConfig] = None
    upload_report: Optional[UploadConfig] = None
    validate_schema: Optional[ValidateSchemaConfig] = None
    # Flexible sections
    download_expert_report: dict = field(default_factory=dict)
    download_report: dict = field(default_factory=dict)
    notify_results: dict = field(default_factory=dict)
    validate_uml_structure: dict = field(default_factory=dict)

class ConfigUtil:
    @staticmethod
    def get_config(config_path: str = "config.json") -> ProjectConfig:
        """
        Maps the detailed JSON structure to the final ProjectConfig typed object.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Missing config file: {config_path}")

        with open(config_path, 'r') as f:
            data = json.load(f)

        # 1. Map 'main' (Required)
        main_data = data.get("main")
        if not main_data:
            raise KeyError("Critical error: 'main' section is missing.")
        main_obj = MainConfig(**main_data)

        # 2. Map 'compute_cohens_kappa'
        kappa_data = data.get("compute_cohens_kappa")
        kappa_obj = CohenKappaConfig(**kappa_data) if kappa_data else None

        # 3. Map 'upload_report'
        upload_data = data.get("upload_report")
        upload_obj = UploadConfig(**upload_data) if upload_data and "token_file" in upload_data else None

        # 4. Map 'validate_schema' (New List Logic)
        schema_data = data.get("validate_schema")
        schema_obj = ValidateSchemaConfig(**schema_data) if schema_data and "source_files" in schema_data else None

        # 5. Build final object
        return ProjectConfig(
            main=main_obj,
            compute_cohens_kappa=kappa_obj,
            upload_report=upload_obj,
            validate_schema=schema_obj,
            download_expert_report=data.get("download_expert_report", {}),
            download_report=data.get("download_report", {}),
            notify_results=data.get("notify_results", {}),
            validate_uml_structure=data.get("validate_uml_structure", {})
        )