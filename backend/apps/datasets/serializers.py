from rest_framework import serializers

from apps.datasets.models import DatasetVersion


class DatasetVersionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="dataset.name", read_only=True)
    description = serializers.CharField(source="dataset.description", read_only=True)
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = DatasetVersion
        fields = [
            "id",
            "name",
            "description",
            "source",
            "source_type",
            "version",
            "record_count",
            "status",
            "uploaded_by_username",
            "uploaded_at",
        ]


class DatasetUploadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    source = serializers.CharField(max_length=200)
    source_type = serializers.ChoiceField(choices=["REAL", "SYNTHETIC", "EXTERNAL"])
    version = serializers.CharField(max_length=40)
    file = serializers.FileField()

    def validate_file(self, upload):
        name = upload.name.lower()
        if not name.endswith((".csv", ".xlsx")):
            raise serializers.ValidationError("Upload a .csv or .xlsx file.")
        if upload.size and upload.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File must be 10 MB or smaller.")
        return upload
