from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    errors = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))
