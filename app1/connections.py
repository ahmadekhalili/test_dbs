import time
import logging
from django.conf import settings
from elasticsearch import Elasticsearch
from pymongo import MongoClient, errors as mongo_errors

logger = logging.getLogger(__name__)
ELASTICSEARCH = settings.ELASTICSEARCH
MONGODB = settings.MONGODB

# MongoDB and Elasticsearch clients in one line each
def get_mongo_client():
    return MongoClient(f"mongodb://{MONGODB['USER']}:{MONGODB['PASSWORD']}@{MONGODB['HOST']}:{MONGODB['PORT']}/{MONGODB['NAME']}")

def get_els_client():
    return Elasticsearch([{'host': ELASTICSEARCH['HOST'], 'port': ELASTICSEARCH['PORT']}], http_auth=(ELASTICSEARCH['USER'], ELASTICSEARCH['PASSWORD']), use_ssl=ELASTICSEARCH['USE_SSL'])
