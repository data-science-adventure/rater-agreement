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
    files_to_upload: List[str] = field(default_factory=list)


@dataclass
class ValidateSchemaConfig:
    source_files: List[str] = field(default_factory=list)


@dataclass
class ValidateUmlConfig:
    source_files: List[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    main: MainConfig
    compute_cohens_kappa: Optional[CohenKappaConfig] = None
    upload_report: Optional[UploadConfig] = None
    validate_schema: Optional[ValidateSchemaConfig] = None
    validate_uml_structure: Optional[ValidateUmlConfig] = None
    # Flexible placeholders for empty JSON objects
    download_expert_report: dict = field(default_factory=dict)
    download_report: dict = field(default_factory=dict)
    notify_results: dict = field(default_factory=dict)


class ConfigUtil:
    @staticmethod
    def get_config(config_path: str = "config.json") -> ProjectConfig:
        """
        Loads the config JSON and maps it to a strictly typed ProjectConfig object.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            data = json.load(f)

        # 1. Map 'main' (Required)
        main_obj = MainConfig(**data["main"])

        # 2. Map 'compute_cohens_kappa'
        kappa_data = data.get("compute_cohens_kappa")
        kappa_obj = CohenKappaConfig(**kappa_data) if kappa_data else None

        # 3. Map 'upload_report' (Updated with list)
        upload_data = data.get("upload_report")
        upload_obj = None
        if upload_data and "token_file" in upload_data:
            upload_obj = UploadConfig(**upload_data)

        # 4. Map 'validate_schema'
        schema_data = data.get("validate_schema")
        schema_obj = (
            ValidateSchemaConfig(**schema_data)
            if schema_data and "source_files" in schema_data
            else None
        )

        # 5. Map 'validate_uml_structure'
        uml_data = data.get("validate_uml_structure")
        uml_obj = (
            ValidateUmlConfig(**uml_data)
            if uml_data and "source_files" in uml_data
            else None
        )

        # 6. Return the composite object
        return ProjectConfig(
            main=main_obj,
            compute_cohens_kappa=kappa_obj,
            upload_report=upload_obj,
            validate_schema=schema_obj,
            validate_uml_structure=uml_obj,
            download_expert_report=data.get("download_expert_report", {}),
            download_report=data.get("download_report", {}),
            notify_results=data.get("notify_results", {}),
        )
