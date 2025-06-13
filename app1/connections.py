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
    host = MONGODB['HOST']
    port = MONGODB['PORT']
    db_name = MONGODB['NAME']
    user = MONGODB.get('USER')
    password = MONGODB.get('PASSWORD')

    if user and password:
        uri = f"mongodb://{user}:{password}@{host}:{port}/{db_name}"
    else:
        uri = f"mongodb://{host}:{port}/{db_name}"
    return MongoClient(uri)

def get_els_client():
    host = ELASTICSEARCH['HOST']
    port = ELASTICSEARCH['PORT']
    use_ssl = ELASTICSEARCH['USE_SSL']
    user = ELASTICSEARCH.get('USER')
    password = ELASTICSEARCH.get('PASSWORD')

    if user and password:
        client = Elasticsearch(
            [{'host': host, 'port': port}],
            http_auth=(user, password),
            use_ssl=use_ssl
        )
    else:
        client = Elasticsearch(
            [{'host': host, 'port': port}],
            use_ssl=use_ssl
        )
    return client
