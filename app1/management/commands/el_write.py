import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from pymongo import MongoClient, ASCENDING
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.helpers import bulk

from app1.connections import get_mongo_client, get_els_client
from app1.methods import generate_realistic_test_data

import uuid

logger = logging.getLogger('web')
es_client = get_els_client()


class Command(BaseCommand):
    help = 'write 2000000 record to elastic'

    def add_arguments(self, parser):
        # No arguments needed - all settings come from Django settings
        pass

    def handle(self, *args, **options):
        index_name = 'products'  # table name
        records_per_batch, batch = 100000, 20

        try:
            logger.info(f"💫 Started writing..")
            for i in range(batch):
                data = generate_realistic_test_data(records_per_batch)
                def generate_docs():
                    import uuid
                    for item in data:
                        yield {"_index": index_name, "_id": str(uuid.uuid4()), "_source": item}

                success_count, failed_docs = bulk(es_client, generate_docs(), refresh=True, raise_on_error=False)
                logger.info(f"is wrriten {records_per_batch} records. continue.. ")
            logger.info(f"👌 Sucessfully saved: {records_per_batch*batch} records to elastic db.")
        except Exception as e:
            logger.error(f"Failed write to elastic. error: {e}")
