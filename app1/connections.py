from django.conf import settings
from elasticsearch import Elasticsearch
from pymongo import MongoClient

# Initialize connections with pooling
es_client = Elasticsearch(
    settings.ELASTICSEARCH_SETTINGS['hosts'],
    max_retries=settings.ELASTICSEARCH_SETTINGS['max_retries'],
    retry_on_timeout=settings.ELASTICSEARCH_SETTINGS['retry_on_timeout'],
)

mongo_client = MongoClient(
    settings.MONGODB_SETTINGS['host'],
    maxPoolSize=settings.MONGODB_SETTINGS['maxPoolSize'],
    minPoolSize=settings.MONGODB_SETTINGS['minPoolSize']
)
mongo_db = mongo_client[settings.MONGODB_SETTINGS['db']]
mongo_collection = mongo_db['products']

# Create indexes for MongoDB
mongo_collection.create_index('category')
mongo_collection.create_index('price')

# Create ElasticSearch index mapping - منصفانه با بقیه دیتابیس‌ها
es_mapping = {
    "mappings": {
        "properties": {
            "name": {"type": "text", "index": False},  # بدون index
            "category": {"type": "keyword"},  # با index (مثل بقیه)
            "price": {"type": "float"},  # با index (مثل بقیه)
            "stock": {"type": "integer", "index": False},  # بدون index
            "description": {"type": "text", "index": False},  # بدون index
            "rating": {"type": "float", "index": False}  # بدون index
        }
    }
}

