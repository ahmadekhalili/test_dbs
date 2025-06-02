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


class ProductMongo(Document):
    """MongoDB model using MongoEngine"""
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
    Elasticsearch manager for Product operations with selective indexing.
    Only 'category' and 'price' fields are indexed for fast search.
    Other fields are stored but not indexed to save memory and improve write performance.
    """

    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize Elasticsearch connection

        Args:
            connection_config: Dictionary containing connection parameters
            Example: {
                'host': 'localhost',
                'port': 9200,
                'user': 'elastic',
                'password': 'password',
                'use_ssl': False,
                'index_name': 'products'
            }
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
        Create Elasticsearch index with optimized mapping.
        Only 'category' and 'price' fields are indexed for search.
        Other fields are stored but not indexed to optimize performance.

        Returns:
            bool: True if successful, False otherwise
        """
        mapping = {
            "mappings": {
                "properties": {
                    # فیلدهای غیر قابل جستجو (فقط ذخیره می‌شوند)
                    "name": {
                        "type": "text",
                        "index": False,  # No indexing for faster writes
                        "store": True  # Store for retrieval
                    },
                    "description": {
                        "type": "text",
                        "index": False,  # No indexing for faster writes
                        "store": True  # Store for retrieval
                    },
                    "stock": {
                        "type": "integer",
                        "index": False,  # No indexing for faster writes
                        "store": True  # Store for retrieval
                    },
                    "rating": {
                        "type": "float",
                        "index": False,  # No indexing for faster writes
                        "store": True  # Store for retrieval
                    },

                    # فیلدهای قابل جستجو (indexed برای جستجوی سریع)
                    "category": {
                        "type": "keyword",  # Exact match
                        "index": True,  # Enable indexing for fast search
                        "store": True,  # Also store for retrieval
                        "eager_global_ordinals": True  # Optimize for aggregations
                    },
                    "price": {
                        "type": "double",  # High precision for money
                        "index": True,  # Enable indexing for range queries
                        "store": True,  # Also store for retrieval
                        "coerce": False  # Strict type checking
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "refresh_interval": "1s",
                    "max_result_window": 50000,  # Allow deep pagination
                    # بهینه‌سازی برای نوشتن سریع‌تر
                    "translog": {
                        "durability": "async",
                        "flush_threshold_size": "512mb"
                    }
                },
                # تنظیمات تحلیل‌گر (اگرچه فعلاً استفاده نمی‌شود)
                "analysis": {
                    "analyzer": {
                        "product_analyzer": {
                            "type": "standard",
                            "stopwords": "_none_"
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
            return True

        except RequestError as e:
            self.logger.error(f"Error creating index: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating index: {e}")
            return False

    def add_product(self, product: ProductData, product_id: Optional[str] = None) -> bool:
        """
        Add a product to the index

        Args:
            product: ProductData instance
            product_id: Optional custom ID, if None Elasticsearch will generate one

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.es.index(
                index=self.index_name,
                id=product_id,
                body=product.to_dict(),
                refresh='wait_for'  # Ensure immediate availability for search
            )

            self.logger.info(f"Successfully indexed product: {response['_id']}")
            return True

        except Exception as e:
            self.logger.error(f"Error indexing product: {e}")
            return False


def setup_mongodb():
    """Setup MongoDB connection and create indexes"""
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

        # Create indexes (they will be created automatically when first document is saved)
        # But we can ensure they exist by calling ensure_indexes
        ProductMongo.ensure_indexes()
        print("✅ MongoDB indexes created for ProductMongo collection: products")

        return True
    except Exception as e:
        print(f"❌ Error setting up MongoDB: {e}")
        return False


def setup_elasticsearch():
    """Setup Elasticsearch and create index"""
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

        # Create index
        if es_manager.create_index():
            print(f"✅ Elasticsearch index '{settings.ELASTICSEARCH['INDEX_NAME']}' is ready")
            return True, es_manager
        else:
            return False, None

    except Exception as e:
        print(f"❌ Error setting up Elasticsearch: {e}")
        return False, None


def create_sample_product_example():
    """Example of how to create a product (not executed automatically)"""
    # This is just an example - not executed by default
    example_product = ProductMongo(
        name='Example Product',
        category='Example Category',
        price=Decimal('99.99'),
        stock=10,
        description='This is an example product',
        rating=4.0
    )
    # To save: example_product.save()
    return example_product


def main():
    """Main function to setup databases (initialization only)"""
    print("=== Initializing MongoDB and Elasticsearch ===\n")

    # Setup MongoDB
    mongo_success = setup_mongodb()

    # Setup Elasticsearch
    es_success, es_manager = setup_elasticsearch()

    # Summary
    print("\n=== Setup Summary ===")
    print(f"MongoDB: {'✅ Success' if mongo_success else '❌ Failed'}")
    print(f"Elasticsearch: {'✅ Success' if es_success else '❌ Failed'}")

    if mongo_success and es_success:
        print("\n🎉 All databases initialized successfully!")
    else:
        print("\n⚠️  Some databases failed to initialize. Check the errors above.")


if __name__ == "__main__":
    main()