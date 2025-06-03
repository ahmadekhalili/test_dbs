from abc import ABC, abstractmethod
import time
import random
import logging
from typing import Dict, List, Tuple, Any, Callable
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

logger = logging.getLogger('web')

es_logger = logging.getLogger('elasticsearch')
original_level = es_logger.level
es_logger.setLevel(logging.WARNING)
logging.getLogger('pymongo').setLevel(logging.WARNING)

class BenchmarkStrategy(ABC):
    """Enhanced Strategy interface with full-text search capabilities"""
    def __init__(self, client):  # 'client for circular import error
        self.client = client

    @abstractmethod
    def write(self, data) -> Tuple[float, str]:
        pass

    @abstractmethod
    def read(self) -> Tuple[float, str]:
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


class PostgresBenchmarkStrategy(BenchmarkStrategy):
    """PostgreSQL implementation with full-text search using PostgreSQL's built-in capabilities"""

    def write(self, data):
        logger.info(f'data: {data}')
        try:
            start_time = time.time()
            with transaction.atomic():
                products = []
                for item in data:
                    products.append(Product(
                        name=item['name'],
                        category=item['category'],
                        price=Decimal(str(item['price'])),
                        stock=item['stock'],
                        description=item['description'],
                        rating=item['rating']
                    ))
                Product.objects.bulk_create(products)
            end_time = time.time()
            return end_time - start_time, 'Write'
        except Exception as e:
            logger.error(f"PostgreSQL write benchmark failed: {e}")
            raise

    def read(self, query_count):
        try:
            start_time = time.time()
            for _ in range(query_count):
                if random.choice([True, False]):
                    list(Product.objects.filter(category='Electronics'))
                else:
                    list(Product.objects.filter(price__gte=100, price__lte=500))
            end_time = time.time()
            return end_time - start_time, 'Read'
        except Exception as e:
            logger.error(f"PostgreSQL read benchmark failed: {e}")
            raise

    def aggregate(self, data=None):
        try:
            from django.db.models import Avg, Count
            start_time = time.time()
            result = (Product.objects
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
        Simple full-text search using PostgreSQL's LIKE and ILIKE operators
        Searches in name and description fields
        """
        try:
            search_terms = ['Product', 'detailed', 'description', 'Electronics', 'Books', 'quality', 'premium']
            start_time = time.time()

            for _ in range(query_count):
                term = random.choice(search_terms)
                # Simple text search using ILIKE (case-insensitive LIKE)
                results = list(Product.objects.filter(
                    Q(name__icontains=term) | Q(description__icontains=term)
                )[:20])  # Limit to 20 results

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchSimple'
        except Exception as e:
            logger.error(f"PostgreSQL simple full-text search failed: {e}")
            raise

    def full_text_search_complex(self, query_count):
        """
        Complex full-text search using PostgreSQL's built-in text search features
        Uses SearchVector and SearchQuery for more sophisticated search
        """
        try:
            search_queries = [
                'high quality product',
                'electronics premium',
                'detailed description',
                'product rating',
                'category books'
            ]
            start_time = time.time()

            for _ in range(query_count):
                query_text = random.choice(search_queries)

                # PostgreSQL full-text search with ranking
                results = list(Product.objects.annotate(
                    search=SearchVector('name', 'description', 'category'),
                    rank=SearchRank(SearchVector('name', 'description', 'category'), SearchQuery(query_text))
                ).filter(search=SearchQuery(query_text)).order_by('-rank')[:20])

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchComplex'
        except Exception as e:
            logger.error(f"PostgreSQL complex full-text search failed: {e}")
            raise


class MongoBenchmarkStrategy(BenchmarkStrategy):
    """MongoDB implementation with full-text search using MongoDB's text indexes"""

    def write(self, data):
        try:
            start_time = time.time()
            self.client.insert_many(data)
            end_time = time.time()
            return end_time - start_time, 'Write'
        except Exception as e:
            logger.error(f"MongoDB write benchmark failed: {e}")
            raise

    def read(self, query_count):
        try:
            start_time = time.time()
            for _ in range(query_count):
                if random.choice([True, False]):
                    list(self.client.find({'category': 'Electronics'}))
                else:
                    list(self.client.find({'price': {'$gte': 100, '$lte': 500}}))
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
        Simple full-text search using MongoDB's regex search
        """
        try:
            search_terms = ['Product', 'detailed', 'description', 'Electronics', 'Books', 'quality', 'premium']
            start_time = time.time()

            for _ in range(query_count):
                term = random.choice(search_terms)
                # Simple regex search (case-insensitive)
                results = list(self.client.find({
                    '$or': [
                        {'name': {'$regex': term, '$options': 'i'}},
                        {'description': {'$regex': term, '$options': 'i'}}
                    ]
                }).limit(20))

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchSimple'
        except Exception as e:
            logger.error(f"MongoDB simple full-text search failed: {e}")
            raise

    def full_text_search_complex(self, query_count):
        """
        Complex full-text search using MongoDB's $text operator with text indexes
        Note: Requires text index to be created on fields
        """
        try:
            search_queries = [
                'high quality product',
                'electronics premium',
                'detailed description',
                'product rating',
                'category books'
            ]
            start_time = time.time()

            # First, ensure text index exists (in production, this should be done during setup)
            try:
                self.client.create_index([
                    ('name', 'text'),
                    ('description', 'text'),
                    ('category', 'text')
                ])
            except:
                pass  # Index might already exist

            for _ in range(query_count):
                query_text = random.choice(search_queries)

                # MongoDB text search with scoring
                results = list(self.client.find(
                    {'$text': {'$search': query_text}},
                    {'score': {'$meta': 'textScore'}}
                ).sort([('score', {'$meta': 'textScore'})]).limit(20))

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchComplex'
        except Exception as e:
            logger.error(f"MongoDB complex full-text search failed: {e}")
            raise


class ElasticBenchmarkStrategy(BenchmarkStrategy):
    """Elasticsearch implementation showcasing its full-text search power"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index_name = 'products'

    def write(self, data):
        try:
            from elasticsearch.helpers import bulk
            if not self.client.indices.exists(index=self.index_name):
                # Create index with proper full-text search mapping
                self._create_fulltext_index()

            start_time = time.time()

            def generate_docs():
                for i, item in enumerate(data):
                    clean_doc = {k: (str(v) if hasattr(v, '__class__') and 'ObjectId' in str(type(v)) else v)
                                 for k, v in item.items() if k != '_id'}
                    yield {"_index": self.index_name, "_id": i, "_source": clean_doc}

            try:
                success_count, failed_docs = bulk(self.client, generate_docs(), refresh=True, raise_on_error=False)
            finally:
                es_logger.setLevel(original_level)
            end_time = time.time()
            return end_time - start_time, 'Write'
        except Exception as e:
            logger.error(f"Elasticsearch write benchmark failed: {e}")
            raise

    def _create_fulltext_index(self):
        """Create index optimized for full-text search"""
        mapping = {
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "category": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "price": {"type": "double"},
                    "stock": {"type": "integer"},
                    "rating": {"type": "float"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "custom_analyzer": {
                            "type": "standard",
                            "stopwords": "_none_"
                        }
                    }
                }
            }
        }

        self.client.indices.create(index=self.index_name, body=mapping)

    def read(self, query_count):
        try:
            start_time = time.time()
            for _ in range(query_count):
                if random.choice([True, False]):
                    self.client.search(index='products', body={'query': {'term': {'category.keyword': 'Electronics'}}})
                else:
                    self.client.search(index='products', body={'query': {'range': {'price': {'gte': 100, 'lte': 500}}}})
            end_time = time.time()
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
        Simple full-text search using Elasticsearch's match query
        This showcases basic full-text capabilities with automatic relevance scoring
        """
        try:
            search_terms = ['Product', 'detailed', 'description', 'Electronics', 'Books', 'quality', 'premium']
            start_time = time.time()

            for _ in range(query_count):
                term = random.choice(search_terms)

                # Simple multi-field match query
                query = {
                    "size": 20,
                    "query": {
                        "multi_match": {
                            "query": term,
                            "fields": ["name^2", "description", "category"],  # Boost name field
                            "type": "best_fields"
                        }
                    }
                }

                response = self.client.search(index=self.index_name, body=query)

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchSimple'
        except Exception as e:
            logger.error(f"Elasticsearch simple full-text search failed: {e}")
            raise

    def full_text_search_complex(self, query_count):
        """
        Complex full-text search showcasing Elasticsearch's advanced features:
        - Fuzzy matching for typos
        - Phrase matching
        - Field boosting
        - Filtering with search
        - Highlighting
        - Custom scoring
        """
        try:
            search_scenarios = [
                {
                    "name": "fuzzy_search",
                    "query": {
                        "size": 20,
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "multi_match": {
                                            "query": "productt",  # Intentional typo
                                            "fields": ["name^3", "description"],
                                            "fuzziness": "AUTO",  # Handle typos
                                            "prefix_length": 1
                                        }
                                    }
                                ],
                                "filter": [
                                    {"range": {"rating": {"gte": 3.0}}}
                                ]
                            }
                        },
                        "highlight": {
                            "fields": {
                                "name": {},
                                "description": {"fragment_size": 100}
                            }
                        }
                    }
                },
                {
                    "name": "phrase_and_boost",
                    "query": {
                        "size": 20,
                        "query": {
                            "bool": {
                                "should": [
                                    {
                                        "match_phrase": {
                                            "description": {
                                                "query": "detailed description",
                                                "boost": 2.0
                                            }
                                        }
                                    },
                                    {
                                        "match": {
                                            "name": {
                                                "query": "premium quality",
                                                "boost": 1.5
                                            }
                                        }
                                    },
                                    {
                                        "term": {
                                            "category.keyword": {
                                                "value": "Electronics",
                                                "boost": 1.2
                                            }
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    }
                },
                {
                    "name": "complex_filtering_aggregation",
                    "query": {
                        "size": 0,  # Only aggregations, no docs
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "match": {
                                            "description": "product"
                                        }
                                    }
                                ],
                                "filter": [
                                    {"range": {"price": {"gte": 50, "lte": 800}}},
                                    {"range": {"rating": {"gte": 2.0}}}
                                ]
                            }
                        },
                        "aggs": {
                            "price_ranges": {
                                "range": {
                                    "field": "price",
                                    "ranges": [
                                        {"to": 100},
                                        {"from": 100, "to": 500},
                                        {"from": 500}
                                    ]
                                },
                                "aggs": {
                                    "avg_rating": {"avg": {"field": "rating"}},
                                    "top_categories": {
                                        "terms": {"field": "category.keyword", "size": 3}
                                    }
                                }
                            }
                        }
                    }
                }
            ]

            start_time = time.time()

            for _ in range(query_count):
                scenario = random.choice(search_scenarios)
                response = self.client.search(index=self.index_name, body=scenario["query"])

                # Optional: Process results to simulate real usage
                if scenario["name"] == "complex_filtering_aggregation":
                    # Extract aggregation results
                    aggs = response.get('aggregations', {})
                elif 'highlight' in scenario["query"]:
                    # Process highlighted results
                    hits = response.get('hits', {}).get('hits', [])

            end_time = time.time()
            return end_time - start_time, 'FullTextSearchComplex'
        except Exception as e:
            logger.error(f"Elasticsearch complex full-text search failed: {e}")
            raise
