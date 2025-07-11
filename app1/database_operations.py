from abc import ABC, abstractmethod
import time
import random
import logging
from typing import Dict, List, Tuple, Any, Callable
from django.db.models import Q, Avg, Count
from django.db import transaction
from django.apps import apps
from django.conf import settings
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from decimal import Decimal

from .models import *

logger = logging.getLogger('web')

es_logger = logging.getLogger('elasticsearch')
original_level = es_logger.level
es_logger.setLevel(logging.WARNING)
logging.getLogger('pymongo').setLevel(logging.WARNING)

postgres_table_name = settings.DATABASES['default']['TABLE']
POSTGRES_MODEL = apps.get_model('app1', postgres_table_name)

# separated here from methods.py because of circular imports from settings.py
class BenchmarkStrategy(ABC):
    """Enhanced Strategy interface with full-text search capabilities"""
    def __init__(self, client):  # 'client for circular import error
        self.client = client

    @abstractmethod
    def write(self, data) -> Tuple[float, str]:
        pass

    @abstractmethod
    def read(self, query_count, field_name=None) -> Tuple[float, str]:
        pass

    @abstractmethod
    def aggregate(self, data=None) -> Tuple[float, str]:
        pass

    @abstractmethod
    def full_text_search_simple(self, query_count) -> Tuple[float, str]:
        """Simple full-text search - basic text matching"""
        pass

    @abstractmethod
    def full_text_search_complex(self, query_count) -> Tuple[float, str]:
        """Complex full-text search - advanced features like fuzzy, boosting, etc."""
        pass


class FieldValue:
    '''
    field methods must named in structure: fieldname_value()
    '''
    def __init__(self, db: BenchmarkStrategy):
        self.db = db

    def category_value(self):
        return "Electronics"

    def name_value(self):
        return f"Product {random.randint(0, self.db._get_max_records())}"

    def get_field_value(self, field_name):
        method = getattr(self, f"{field_name}_value")
        return method()


class PostgresBenchmarkStrategy(BenchmarkStrategy):
    """PostgreSQL implementation with full-text search using PostgreSQL's built-in capabilities"""
    def _get_max_records(self):
        return Product.objects.count()

    def write(self, data):
        logger.info(f'postgres write data: {len(data)} records like: {data[:2]}')
        try:
            start_time = time.time()
            with transaction.atomic():
                products = []
                for item in data:
                    products.append(POSTGRES_MODEL(
                        name=item['name'],
                        category=item['category'],
                        price=Decimal(str(item['price'])),
                        stock=item['stock'],
                        description=item['description'],
                        rating=item['rating']
                    ))
                POSTGRES_MODEL.objects.bulk_create(products)
            end_time = time.time()
            return end_time - start_time, 'Write'
        except Exception as e:
            logger.error(f"PostgreSQL write benchmark failed: {e}")
            raise

    def read(self, query_count, field_name=None):
        field_value = FieldValue(self)
        try:
            start_time = time.time()
            for _ in range(query_count):
                if not field_name:
                    if random.choice([True, False]):
                        list(POSTGRES_MODEL.objects.filter(category='Electronics'))
                    else:
                        list(POSTGRES_MODEL.objects.filter(price__gte=100, price__lte=500))
                else:
                    query = {f"{field_name}": field_value.get_field_value(field_name)}
                    list(POSTGRES_MODEL.objects.filter(**query))
            end_time = time.time()
            return end_time - start_time, 'Read'
        except Exception as e:
            logger.error(f"PostgreSQL read benchmark failed: {e}")
            raise

    def aggregate(self, data=None):
        try:
            # returns like: {'category': 'Electronics', 'avg_price': 245.75, 'count': 12}
            start_time = time.time()
            result = (POSTGRES_MODEL.objects
                      .values('category')
                      .annotate(avg_price=Avg('price'), count=Count('id'))
                      .order_by('-avg_price'))
            list(result)  # Force evaluation
            end_time = time.time()
            return end_time - start_time, 'Aggregate'
        except Exception as e:
            logger.error(f"PostgreSQL aggregate benchmark failed: {e}")
            raise

    def full_text_search_simple(self, query_count):
        """
        IDENTICAL TASK: Simple single-word text search across name and description fields
        PostgreSQL implementation using basic text search capabilities
        """
        try:
            # IDENTICAL search terms across all databases
            search_terms = ['Product', 'Electronics', 'Book', 'quality', 'premium', 'gaming', 'wireless']
            start_time = time.time()

            for _ in range(query_count):
                term = random.choice(search_terms)
                # Basic full-text search - single word lookup
                list(POSTGRES_MODEL.objects.extra(
                    where=["to_tsvector('english', name || ' ' || description) @@ plainto_tsquery('english', %s)"],
                    params=[term]
                )[:20])

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchSimple'
        except Exception as e:
            logger.error(f"PostgreSQL simple full-text search failed: {e}")
            raise

    def full_text_search_complex(self, query_count):
        """
        IDENTICAL TASK: Complex multi-word phrase search with filtering and ranking
        Real-world scenario: POSTGRES_MODEL search with price filter + relevance ranking
        PostgreSQL implementation using advanced text search features
        """
        try:
            # IDENTICAL complex search scenarios across all databases
            search_scenarios = [
                {'phrase': 'premium gaming laptop', 'min_price': 500, 'max_price': 2000},
                {'phrase': 'wireless smartphone pro', 'min_price': 200, 'max_price': 1200},
                {'phrase': 'high quality book', 'min_price': 10, 'max_price': 100},
                {'phrase': 'electronics premium device', 'min_price': 100, 'max_price': 800},
                {'phrase': 'detailed product description', 'min_price': 50, 'max_price': 500}
            ]
            start_time = time.time()

            for _ in range(query_count):
                scenario = random.choice(search_scenarios)
                
                # Complex search: phrase + price filter + relevance ranking
                results = list(POSTGRES_MODEL.objects.annotate(
                    search=SearchVector('name', 'description', 'category'),
                    rank=SearchRank(SearchVector('name', 'description', 'category'), SearchQuery(scenario['phrase']))
                ).filter(
                    search=SearchQuery(scenario['phrase']),
                    price__gte=scenario['min_price'],
                    price__lte=scenario['max_price']
                ).order_by('-rank')[:20])

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchComplex'
        except Exception as e:
            logger.error(f"PostgreSQL complex full-text search failed: {e}")
            raise


class MongoBenchmarkStrategy(BenchmarkStrategy):
    """MongoDB implementation with full-text search using MongoDB's text indexes"""
    def _get_max_records(self):
        # number of max_records
        return self.client.count_documents({})

    def write(self, data):
        logger.info(f'mongo write data: {len(data)} records like: {data[:2]}')
        try:
            start_time = time.time()
            self.client.insert_many(data)
            end_time = time.time()
            return end_time - start_time, 'Write'
        except Exception as e:
            logger.error(f"MongoDB write benchmark failed: {e}")
            raise

    def read(self, query_count, field_name=None):
        field_value = FieldValue(self)
        try:
            start_time = time.time()
            for _ in range(query_count):
                if not field_name:
                    if random.choice([True, False]):
                        list(self.client.find({'category': 'Electronics'}))
                    else:
                        list(self.client.find({'price': {'$gte': 100, '$lte': 500}}))
                else:
                    query = {f"{field_name}": field_value.get_field_value(field_name)}
                    list(self.client.find(query))
            end_time = time.time()
            return end_time - start_time, 'Read'
        except Exception as e:
            logger.error(f"MongoDB read benchmark failed: {e}")
            raise

    def aggregate(self, data=None):
        try:
            pipeline = [
                {'$group': {'_id': '$category', 'avg_price': {'$avg': '$price'}, 'count': {'$sum': 1}}},
                {'$sort': {'avg_price': -1}}
            ]
            start_time = time.time()
            result = list(self.client.aggregate(pipeline))
            end_time = time.time()
            return end_time - start_time, 'Aggregate'
        except Exception as e:
            logger.error(f"MongoDB aggregate benchmark failed: {e}")
            raise

    def full_text_search_simple(self, query_count):
        """
        IDENTICAL TASK: Simple single-word text search across name and description fields
        MongoDB implementation using $text search with weighted index
        """
        try:
            # IDENTICAL search terms across all databases
            search_terms = ['Product', 'Electronics', 'Book', 'quality', 'premium', 'gaming', 'wireless']
            start_time = time.time()

            for _ in range(query_count):
                term = random.choice(search_terms)
                # Basic full-text search - single word lookup with MongoDB $text
                results = list(self.client.find(
                    {'$text': {'$search': term}},
                    {'score': {'$meta': 'textScore'}}
                ).sort([('score', {'$meta': 'textScore'})]).limit(20))

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchSimple'
        except Exception as e:
            logger.error(f"MongoDB simple full-text search failed: {e}")
            raise

    def full_text_search_complex(self, query_count):
        """
        IDENTICAL TASK: Complex multi-word phrase search with filtering and ranking
        Real-world scenario: Product search with price filter + relevance ranking
        MongoDB implementation using $text search + aggregation pipeline
        """
        try:
            # IDENTICAL complex search scenarios across all databases
            search_scenarios = [
                {'phrase': 'premium gaming laptop', 'min_price': 500, 'max_price': 2000},
                {'phrase': 'wireless smartphone pro', 'min_price': 200, 'max_price': 1200},
                {'phrase': 'high quality book', 'min_price': 10, 'max_price': 100},
                {'phrase': 'electronics premium device', 'min_price': 100, 'max_price': 800},
                {'phrase': 'detailed product description', 'min_price': 50, 'max_price': 500}
            ]
            start_time = time.time()

            for _ in range(query_count):
                scenario = random.choice(search_scenarios)
                
                # Complex search: phrase + price filter + relevance ranking using aggregation
                pipeline = [
                    {'$match': {
                        '$text': {'$search': scenario['phrase']},
                        'price': {'$gte': scenario['min_price'], '$lte': scenario['max_price']}
                    }},
                    {'$addFields': {'score': {'$meta': 'textScore'}}},
                    {'$sort': {'score': -1}},
                    {'$limit': 20}
                ]
                results = list(self.client.aggregate(pipeline))

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchComplex'
        except Exception as e:
            logger.error(f"MongoDB complex full-text search failed: {e}")
            raise


class ElasticBenchmarkStrategy(BenchmarkStrategy):
    """Elasticsearch implementation showcasing its full-text search power"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index_name = settings.ELASTICSEARCH['INDEX_NAME']

    def _get_max_records(self):
        # number of max_records
        return self.client.count(index=settings.ELASTICSEARCH['INDEX_NAME'])['count']

    def write(self, data):
        try:
            from elasticsearch.helpers import bulk

            start_time = time.time()

            def generate_docs():
                import uuid
                for item in data:
                    yield {"_index": self.index_name, "_id": str(uuid.uuid4()), "_source": item}

            logger.info(f"Elasticsearch write data: {len(data)} records like: {data[:2]}")
            try:
                success_count, failed_docs = bulk(self.client, generate_docs(), refresh=True, raise_on_error=False)
            finally:
                es_logger.setLevel(original_level)
            end_time = time.time()
            return end_time - start_time, 'Write'
        except Exception as e:
            logger.error(f"Elasticsearch write benchmark failed: {e}")
            raise

    def read(self, query_count, field_name=None):
        field_value = FieldValue(self)
        try:
            start_time = time.time()
            for _ in range(query_count):
                if not field_name:
                    if random.choice([True, False]):
                        self.client.search(index=self.index_name, body={'query': {'term': {'category.keyword': 'Electronics'}}})
                    else:
                        self.client.search(index=self.index_name, body={'query': {'range': {'price': {'gte': 100, 'lte': 500}}}})
                else:
                    query = {f"{field_name}.keyword": field_value.get_field_value(field_name)}
                    self.client.search(index=self.index_name,
                                       body={'query': {'term': query}})
            end_time = time.time()
            result = self.client.count(index=self.index_name,
                               body={'query': {'term': query}})
            logger.info(f"founded elastic records in read: {result['count']}")
            return end_time - start_time, 'Read'
        except Exception as e:
            logger.error(f"Elasticsearch read benchmark failed: {e}")
            raise

    def aggregate(self, data=None):
        try:
            query = {
                "size": 0,
                "aggs": {
                    "categories": {
                        "terms": {"field": "category.keyword", "order": {"avg_price": "desc"}},
                        "aggs": {"avg_price": {"avg": {"field": "price"}}}
                    }
                }
            }
            start_time = time.time()
            response = self.client.search(index=self.index_name, body=query)
            end_time = time.time()
            return end_time - start_time, 'Aggregate'
        except Exception as e:
            logger.error(f"Elasticsearch aggregate benchmark failed: {e}")
            raise

    def full_text_search_simple(self, query_count):
        """
        IDENTICAL TASK: Simple single-word text search across name and description fields
        Elasticsearch implementation using basic multi_match query
        """
        try:
            # IDENTICAL search terms across all databases
            search_terms = ['Product', 'Electronics', 'Book', 'quality', 'premium', 'gaming', 'wireless']
            start_time = time.time()

            for _ in range(query_count):
                term = random.choice(search_terms)

                # Basic full-text search - single word lookup with Elasticsearch
                query = {
                    "size": 20,
                    "query": {
                        "multi_match": {
                            "query": term,
                            "fields": ["name", "description"],
                            "type": "best_fields"
                        }
                    },
                    "sort": ["_score"]
                }

                response = self.client.search(index=self.index_name, body=query)

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchSimple'
        except Exception as e:
            logger.error(f"Elasticsearch simple full-text search failed: {e}")
            raise

    def full_text_search_complex(self, query_count):
        """
        IDENTICAL TASK: Complex multi-word phrase search with filtering and ranking
        Real-world scenario: Product search with price filter + relevance ranking
        Elasticsearch implementation using bool query with phrase matching and filters
        """
        try:
            # IDENTICAL complex search scenarios across all databases
            search_scenarios = [
                {'phrase': 'premium gaming laptop', 'min_price': 500, 'max_price': 2000},
                {'phrase': 'wireless smartphone pro', 'min_price': 200, 'max_price': 1200},
                {'phrase': 'high quality book', 'min_price': 10, 'max_price': 100},
                {'phrase': 'electronics premium device', 'min_price': 100, 'max_price': 800},
                {'phrase': 'detailed product description', 'min_price': 50, 'max_price': 500}
            ]
            start_time = time.time()

            for _ in range(query_count):
                scenario = random.choice(search_scenarios)
                
                # Complex search: phrase + price filter + relevance ranking
                query = {
                    "size": 20,
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "multi_match": {
                                        "query": scenario['phrase'],
                                        "fields": ["name", "description", "category"],
                                        "type": "phrase"
                                    }
                                }
                            ],
                            "filter": [
                                {
                                    "range": {
                                        "price": {
                                            "gte": scenario['min_price'],
                                            "lte": scenario['max_price']
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    "sort": ["_score"]
                }

                response = self.client.search(index=self.index_name, body=query)

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchComplex'
        except Exception as e:
            logger.error(f"Elasticsearch complex full-text search failed: {e}")
            raise
