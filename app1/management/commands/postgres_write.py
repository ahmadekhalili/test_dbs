import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from pymongo import MongoClient, ASCENDING
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import bulk

from app1.models import Product
from app1.methods import generate_realistic_test_data

import uuid

logger = logging.getLogger('web')


class Command(BaseCommand):
    help = 'write 2000000 record to elastic'

    def add_arguments(self, parser):
        # No arguments needed - all settings come from Django settings
        pass

    def handle(self, *args, **options):
        products = []
        records_per_batch, batch = 100000, 20

        try:
            logger.info(f"💫 Started writing..")
            for i in range(batch):
                data = generate_realistic_test_data(records_per_batch)
                products = [Product(**dic) for dic in data]
                Product.objects.bulk_create(products)
                logger.info(f"is wrriten {records_per_batch} records. continue.. ")
            logger.info(f"👌 Sucessfully saved: {records_per_batch*batch} records to postgres db.")
        except Exception as e:
            logger.error(f"Failed write to db. error: {e}")
