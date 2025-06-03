# ==================== UPDATED SETUP_TABLES.PY WITH FULL-TEXT SEARCH ====================

import django
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dbs_test.settings')
django.setup()

import pymongo
import mongoengine
from mongoengine import Document, StringField, DecimalField, IntField, FloatField
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
import json
from decimal import Decimal
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError, ConnectionError
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger('web')


class ProductMongo(Document):
    """MongoDB model using MongoEngine with full-text search support"""
    name = StringField(max_length=200, required=True)
    category = StringField(max_length=100, required=True)
    price = DecimalField(min_value=0, precision=2, required=True)
    stock = IntField(min_value=0, required=True)
    description = StringField(required=True)
    rating = FloatField(min_value=0, max_value=5, required=True)

    meta = {
        'collection': 'products',
        'indexes': [
            'category',  # Single field index on category
            'price',  # Single field index on price
            ('category', 'price'),  # Compound index
            # Full-text search index
            {
                'fields': ['$name', '$description', '$category'],
                'default_language': 'english',
                'weights': {'name': 10, 'description': 5, 'category': 1}
            }
        ]
    }

    def to_dict(self):
        """Convert document to dictionary for Elasticsearch"""
        return {
            'id': str(self.id),
            'name': self.name,
            'category': self.category,
            'price': float(self.price),
            'stock': self.stock,
            'description': self.description,
            'rating': self.rating
        }


@dataclass
class ProductData:
    """Data class for product structure validation"""
    name: str
    category: str
    price: float
    stock: int
    description: str
    rating: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Elasticsearch"""
        return {
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'stock': self.stock,
            'description': self.description,
            'rating': self.rating
        }


class ElasticsearchProductManager:
    """
    Enhanced Elasticsearch manager optimized for full-text search capabilities
    """

    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize Elasticsearch connection

        Args:
            connection_config: Dictionary containing connection parameters
        """
        self.logger = logging.getLogger(__name__)
        self._setup_connection(connection_config)
        self.index_name = connection_config['index_name']

    def _setup_connection(self, config: Dict[str, Any]) -> None:
        """Setup Elasticsearch connection with error handling"""
        try:
            # Build connection URL
            auth = None
            if config.get('user') and config.get('password'):
                auth = (config['user'], config['password'])

            scheme = 'https' if config.get('use_ssl', False) else 'http'
            host = f"{scheme}://{config['host']}:{config['port']}"

            self.es = Elasticsearch(
                [host],
                http_auth=auth,
                verify_certs=config.get('use_ssl', False),
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )

            # Test connection
            if not self.es.ping():
                raise ConnectionError("Cannot connect to Elasticsearch")

        except Exception as e:
            self.logger.error(f"Failed to setup Elasticsearch connection: {e}")
            raise

    def create_index(self) -> bool:
        """
        Create Elasticsearch index optimized for full-text search.
        This mapping showcases Elasticsearch's full-text search power.
        """
        mapping = {
            "mappings": {
                "properties": {
                    # Full-text searchable fields with advanced analysis
                    "name": {
                        "type": "text",
                        "analyzer": "product_name_analyzer",
                        "search_analyzer": "product_search_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            },
                            "suggest": {
                                "type": "completion"
                            }
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "product_description_analyzer",
                        "search_analyzer": "product_search_analyzer",
                        "term_vector": "with_positions_offsets",  # For highlighting
                        "fields": {
                            "raw": {
                                "type": "keyword"
                            }
                        }
                    },
                    "category": {
                        "type": "text",
                        "analyzer": "keyword",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            },
                            "suggest": {
                                "type": "completion"
                            }
                        }
                    },

                    # Numerical and exact-match fields
                    "price": {
                        "type": "double",
                        "index": True
                    },
                    "stock": {
                        "type": "integer",
                        "index": True
                    },
                    "rating": {
                        "type": "float",
                        "index": True
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "refresh_interval": "1s",
                    "max_result_window": 50000,
                    # Optimize for search performance
                    "codec": "best_compression",
                    "max_regex_length": 1000
                },
                # Advanced analyzers for full-text search
                "analysis": {
                    "tokenizer": {
                        "product_tokenizer": {
                            "type": "standard",
                            "max_token_length": 255
                        }
                    },
                    "filter": {
                        "product_stemmer": {
                            "type": "stemmer",
                            "language": "english"
                        },
                        "product_stop": {
                            "type": "stop",
                            "stopwords": ["the", "is", "at", "which", "on"]
                        },
                        "product_synonym": {
                            "type": "synonym",
                            "synonyms": [
                                "smartphone,mobile,phone",
                                "laptop,computer,pc",
                                "tv,television",
                                "book,novel,guide"
                            ]
                        },
                        "product_lowercase": {
                            "type": "lowercase"
                        },
                        "product_edge_ngram": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 10
                        }
                    },
                    "analyzer": {
                        "product_name_analyzer": {
                            "type": "custom",
                            "tokenizer": "product_tokenizer",
                            "filter": [
                                "product_lowercase",
                                "product_synonym",
                                "product_stemmer"
                            ]
                        },
                        "product_description_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "product_lowercase",
                                "product_stop",
                                "product_synonym",
                                "product_stemmer"
                            ]
                        },
                        "product_search_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "product_lowercase",
                                "product_synonym",
                                "product_stemmer"
                            ]
                        },
                        "autocomplete_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": [
                                "product_lowercase",
                                "product_edge_ngram"
                            ]
                        }
                    }
                }
            }
        }

        try:
            if self.es.indices.exists(index=self.index_name):
                self.logger.info(f"Index '{self.index_name}' already exists")
                return True

            response = self.es.indices.create(
                index=self.index_name,
                body=mapping
            )

            self.logger.info(f"Successfully created index: {self.index_name}")
            self.logger.info("Index optimized for full-text search with:")
            self.logger.info("- Custom analyzers for name and description")
            self.logger.info("- Synonym support")
            self.logger.info("- Stemming and stop word filtering")
            self.logger.info("- Edge n-gram for autocomplete")
            self.logger.info("- Completion suggester support")
            return True

        except RequestError as e:
            self.logger.error(f"Error creating index: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating index: {e}")
            return False


def setup_mongodb():
    """Setup MongoDB connection and create indexes including full-text search"""
    print("📦 Setting up MongoDB...")
    try:
        # Build MongoDB URI
        if settings.MONGODB.get('USER') and settings.MONGODB.get('PASSWORD'):
            mongo_uri = f"mongodb://{settings.MONGODB['USER']}:{settings.MONGODB['PASSWORD']}@{settings.MONGODB['HOST']}:{settings.MONGODB['PORT']}/{settings.MONGODB['NAME']}"
        else:
            mongo_uri = f"mongodb://{settings.MONGODB['HOST']}:{settings.MONGODB['PORT']}/{settings.MONGODB['NAME']}"

        # Connect to MongoDB
        mongoengine.connect(
            db=settings.MONGODB['NAME'],
            host=mongo_uri,
            alias='default'
        )

        print(f"✅ Connected to MongoDB: {settings.MONGODB['NAME']}")

        # Create indexes including full-text search
        ProductMongo.ensure_indexes()
        print("✅ MongoDB indexes created for ProductMongo collection: products")
        print("   - Category index")
        print("   - Price index")
        print("   - Compound index (category, price)")
        print("   - Full-text search index (name, description, category)")

        return True
    except Exception as e:
        print(f"❌ Error setting up MongoDB: {e}")
        return False


def setup_elasticsearch():
    """Setup Elasticsearch and create index optimized for full-text search"""
    print("\n🔍 Setting up Elasticsearch...")
    try:
        # Create configuration from settings
        config = {
            'host': settings.ELASTICSEARCH['HOST'],
            'port': settings.ELASTICSEARCH['PORT'],
            'index_name': settings.ELASTICSEARCH['INDEX_NAME']
        }

        # Add authentication if provided
        if settings.ELASTICSEARCH.get('USER'):
            config['user'] = settings.ELASTICSEARCH['USER']
        if settings.ELASTICSEARCH.get('PASSWORD'):
            config['password'] = settings.ELASTICSEARCH['PASSWORD']
        if 'USE_SSL' in settings.ELASTICSEARCH:
            config['use_ssl'] = settings.ELASTICSEARCH['USE_SSL']

        es_manager = ElasticsearchProductManager(config)

        # Test connection
        if not es_manager.es.ping():
            print("❌ Cannot connect to Elasticsearch")
            return False, None

        print("✅ Connected to Elasticsearch")

        # Create index with full-text search optimization
        if es_manager.create_index():
            print(f"✅ Elasticsearch index '{settings.ELASTICSEARCH['INDEX_NAME']}' is ready")
            print("   🚀 Optimized for full-text search with:")
            print("      - Custom analyzers (name, description, search)")
            print("      - Synonym support (smartphone=mobile=phone)")
            print("      - Stemming (running→run, products→product)")
            print("      - Stop word filtering")
            print("      - Edge n-gram for autocomplete")
            print("      - Completion suggester")
            print("      - Term vectors for highlighting")
            return True, es_manager
        else:
            return False, None

    except Exception as e:
        print(f"❌ Error setting up Elasticsearch: {e}")
        return False, None


def setup_postgresql_fulltext():
    """Setup PostgreSQL full-text search extensions"""
    print("\n🐘 Setting up PostgreSQL full-text search...")
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            # Enable PostgreSQL full-text search extensions
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                print("✅ pg_trgm extension enabled (for similarity search)")
            except:
                print("⚠️  pg_trgm extension not available (optional)")

            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
                print("✅ unaccent extension enabled (for accent-insensitive search)")
            except:
                print("⚠️  unaccent extension not available (optional)")

            # Create GIN indexes for full-text search
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_fulltext_gin_idx 
                    ON products 
                    USING GIN (to_tsvector('english', name || ' ' || description || ' ' || category));
                """)
                print("✅ GIN full-text search index created")
            except Exception as e:
                print(f"⚠️  Could not create GIN index: {e}")

            # Create trigram indexes for similarity search
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_name_trgm_idx 
                    ON products 
                    USING GIN (name gin_trgm_ops);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_description_trgm_idx 
                    ON products 
                    USING GIN (description gin_trgm_ops);
                """)
                print("✅ Trigram indexes created for similarity search")
            except Exception as e:
                print(f"⚠️  Could not create trigram indexes: {e}")

        print("✅ PostgreSQL full-text search setup completed")
        return True

    except Exception as e:
        print(f"❌ Error setting up PostgreSQL full-text search: {e}")
        return False


def create_sample_product_example():
    """Example of how to create a product optimized for full-text search testing"""
    example_products = [
        {
            'name': 'Premium Wireless Smartphone Pro Max',
            'category': 'Electronics',
            'price': Decimal('899.99'),
            'stock': 50,
            'description': 'High-quality premium smartphone with advanced camera technology, long-lasting battery life, and wireless charging capabilities. Perfect for professional photography and mobile gaming.',
            'rating': 4.8
        },
        {
            'name': 'Professional Programming Guide Book',
            'category': 'Books',
            'price': Decimal('49.99'),
            'stock': 100,
            'description': 'Comprehensive programming guide for software developers. Covers advanced algorithms, data structures, and best practices for modern software development.',
            'rating': 4.5
        },
        {
            'name': 'Ultra Gaming Laptop Computer',
            'category': 'Electronics',
            'price': Decimal('1299.99'),
            'stock': 25,
            'description': 'Powerful gaming laptop with high-performance graphics card, fast processor, and premium display. Ideal for gaming, video editing, and professional work.',
            'rating': 4.7
        }
    ]

    return example_products


def main():
    """Main function to setup databases with full-text search capabilities"""
    print("=== Initializing Databases with Full-Text Search Support ===\n")

    # Setup PostgreSQL full-text search
    postgres_ft_success = setup_postgresql_fulltext()

    # Setup MongoDB
    mongo_success = setup_mongodb()

    # Setup Elasticsearch
    es_success, es_manager = setup_elasticsearch()

    # Summary
    print("\n" + "=" * 60)
    print("🎯 FULL-TEXT SEARCH SETUP SUMMARY")
    print("=" * 60)
    print(f"PostgreSQL FT: {'✅ Ready' if postgres_ft_success else '❌ Failed'}")
    print(f"MongoDB FT:    {'✅ Ready' if mongo_success else '❌ Failed'}")
    print(f"Elasticsearch: {'✅ Ready' if es_success else '❌ Failed'}")

    if postgres_ft_success and mongo_success and es_success:
        print("\n🚀 ALL DATABASES READY FOR FULL-TEXT SEARCH BENCHMARKING!")
        print("\n📊 Expected Performance Rankings for Full-Text Search:")
        print("   🥇 1st: Elasticsearch (Optimized for search)")
        print("   🥈 2nd: MongoDB (Good text indexing)")
        print("   🥉 3rd: PostgreSQL (Basic full-text features)")

        print("\n🧪 Test with these query examples:")
        print('   - tests: ["full_text_search_simple"]')
        print('   - tests: ["full_text_search_complex"]')
        print('   - tests: ["write", "full_text_search_simple", "full_text_search_complex"]')

    else:
        print("\n⚠️  Some databases failed to initialize. Check the errors above.")
        print("💡 Full-text search benchmarking may not work properly.")


if __name__ == "__main__":
    main()