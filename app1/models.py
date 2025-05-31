from django.db import models
from djongo import models as djongo_models
from elasticsearch import Elasticsearch
from pymongo import MongoClient
import json


class Product(models.Model):
    """PostgreSQL model"""
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    description = models.TextField()
    rating = models.FloatField()

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['price']),
        ]
