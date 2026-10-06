import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.datasets.models import Dataset, DatasetVersion
from apps.models_registry.models import ModelVersion


class Command(BaseCommand):
    help = "Create development users, register the saved maize model, and attach the clean synthetic dataset."

    def handle(self, *args, **options):
        password = os.environ.get("SMARTCROP_DEMO_PASSWORD", "password")
        accounts = [
            ("admin", "admin@smartcrop.local", User.Role.ADMIN, True),
            ("researcher", "researcher@smartcrop.local", User.Role.RESEARCHER, False),
            ("analyst", "analyst@smartcrop.local", User.Role.ANALYST, False),
            ("farmer", "farmer@smartcrop.local", User.Role.FARMER, False),
        ]
        for username, email, role, superuser in accounts:
            user, created = User.objects.get_or_create(username=username, defaults={"email": email, "role": role})
            user.email = email
            user.role = role
            user.is_superuser = superuser
            user.is_staff = superuser or role == User.Role.ADMIN
            user.set_password(password)
            user.save()
            self.stdout.write(f"{'created' if created else 'updated'} {username} ({role})")

        metadata_path = Path(settings.ML_METADATA_PATH)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
        training_date = None
        if metadata.get("training_date"):
            training_date = datetime.fromisoformat(metadata["training_date"])
            if timezone.is_naive(training_date):
                training_date = timezone.make_aware(training_date)
        model, _created = ModelVersion.objects.update_or_create(
            version=metadata.get("version", "1.0.0"),
            defaults={
                "name": metadata.get("model_name", "smartcrop_maize_yield"),
                "algorithm": metadata.get("algorithm", "unknown"),
                "target_variable": metadata.get("target", "yield_t_ha"),
                "features": metadata.get("raw_features") or metadata.get("features") or [],
                "metrics": metadata.get("metrics") or {},
                "artifact_path": str(settings.ML_MODEL_PATH),
                "dataset_version": metadata.get("dataset_version", ""),
                "training_date": training_date,
                "is_active": True,
            },
        )
        self.stdout.write(f"active model {model.version}")

        clean = Path(
            os.environ.get(
                "SMARTCROP_CLEAN_DATASET",
                settings.BASE_DIR.parent / "data-science" / "data" / "processed" / "clean_dataset.csv",
            )
        )
        if clean.is_file():
            admin = User.objects.get(username="admin")
            dataset, _created = Dataset.objects.get_or_create(
                name="Macheke maize synthetic",
                defaults={
                    "description": "Synthetic development file produced by the SmartCrop generator. Not a farm survey.",
                    "created_by": admin,
                },
            )
            version, created = DatasetVersion.objects.get_or_create(
                dataset=dataset,
                version="synthetic-1.0.0",
                defaults={
                    "source": "smartcrop_synthetic_generator_v1",
                    "source_type": DatasetVersion.SourceType.SYNTHETIC,
                    "record_count": 0,
                    "status": DatasetVersion.Status.UPLOADED,
                    "uploaded_by": admin,
                },
            )
            if created or not version.file:
                destination = settings.MEDIA_ROOT / "datasets" / "clean_dataset.csv"
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(clean, destination)
                with destination.open("rb") as handle:
                    version.file.save("clean_dataset.csv", File(handle), save=False)
                import pandas as pd

                version.record_count = int(len(pd.read_csv(clean)))
                version.status = DatasetVersion.Status.VALIDATED
                version.source_type = DatasetVersion.SourceType.SYNTHETIC
                version.save()
            self.stdout.write(f"dataset {dataset.name} {version.version} ({version.record_count} rows)")
        self.stdout.write("Demo password is the SMARTCROP_DEMO_PASSWORD value, or password when unset.")
