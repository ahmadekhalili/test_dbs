from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'price', 'stock', 'description', 'rating']

class BenchmarkResultSerializer(serializers.Serializer):
    database = serializers.CharField()
    operation = serializers.CharField()
    total_time = serializers.FloatField()
    records_processed = serializers.IntegerField()
    avg_time_per_record = serializers.FloatField()
