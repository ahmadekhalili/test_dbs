import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from pymongo import MongoClient, ASCENDING
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import bulk

from setup_tables import ProductMongo
from app1.connections import get_mongo_client, get_els_client
from app1.methods import generate_realistic_test_data

import uuid

logger = logging.getLogger('web')
mongo_collection = get_mongo_client()[settings.MONGODB['NAME']][ProductMongo._meta['collection']]


class Command(BaseCommand):
    help = 'write 2000000 record to elastic'

    def add_arguments(self, parser):
        # No arguments needed - all settings come from Django settings
        pass

    def handle(self, *args, **options):
        records_per_batch, batch = 100000, 10

        try:
            logger.info(f"💫 Started writing..")
            for i in range(batch):
                data = generate_realistic_test_data(records_per_batch)
                mongo_collection.insert_many(data)
                logger.info(f"is written {records_per_batch} records. batch: {i}/{batch} continue.. ")
            logger.info(f"👌 Sucessfully saved: {records_per_batch*batch} records to mongo db.")
        except Exception as e:
            logger.error(f"Failed write to db. error: {e}")
