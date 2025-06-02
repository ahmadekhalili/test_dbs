import pymongo
import mongoengine
from mongoengine import Document, StringField, DecimalField, IntField, FloatField
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
import json
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


class ElasticsearchManager:
    """Elasticsearch manager for Product operations"""

    def __init__(self):
        # Build Elasticsearch connection URL
        auth = None
        if settings.ELASTICSEARCH.get('USER') and settings.ELASTICSEARCH.get('PASSWORD'):
            auth = (settings.ELASTICSEARCH['USER'], settings.ELASTICSEARCH['PASSWORD'])

        scheme = 'https' if settings.ELASTICSEARCH.get('USE_SSL', False) else 'http'
        host = f"{scheme}://{settings.ELASTICSEARCH['HOST']}:{settings.ELASTICSEARCH['PORT']}"

        self.es = Elasticsearch(
            [host],
            http_auth=auth,
            verify_certs=settings.ELASTICSEARCH.get('USE_SSL', False)
        )
        self.index_name = settings.ELASTICSEARCH['INDEX_NAME']

    def create_index(self):
        """Create Elasticsearch index with mapping"""
        mapping = {
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "category": {
                        "type": "keyword"  # For exact matching and aggregations
                    },
                    "price": {
                        "type": "double"
                    },
                    "stock": {
                        "type": "integer"
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "rating": {
                        "type": "float"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "refresh_interval": "1s"
                }
            }
        }

        try:
            if self.es.indices.exists(index=self.index_name):
                print(f"Index '{self.index_name}' already exists")
                return True

            response = self.es.indices.create(
                index=self.index_name,
                body=mapping
            )
            print(f"Created Elasticsearch index: {self.index_name}")
            return True
        except RequestError as e:
            print(f"Error creating Elasticsearch index: {e}")
            return False

    def index_product(self, product_dict):
        """Index a product document"""
        try:
            response = self.es.index(
                index=self.index_name,
                id=product_dict.get('id'),
                body=product_dict
            )
            return response
        except Exception as e:
            print(f"Error indexing product: {e}")
            return None

    def search_products(self, query):
        """Search products in Elasticsearch"""
        try:
            response = self.es.search(
                index=self.index_name,
                body=query
            )
            return response
        except Exception as e:
            print(f"Error searching products: {e}")
            return None


def setup_mongodb():
    """Setup MongoDB connection and create indexes"""
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

        print(f"Connected to MongoDB: {settings.MONGODB['NAME']}")

        # Create indexes (they will be created automatically when first document is saved)
        # But we can ensure they exist by calling ensure_indexes
        ProductMongo.ensure_indexes()
        print("MongoDB indexes created for ProductMongo collection: products")

        return True
    except Exception as e:
        print(f"Error setting up MongoDB: {e}")
        return False


def setup_elasticsearch():
    """Setup Elasticsearch and create index"""
    try:
        es_manager = ElasticsearchManager()

        # Test connection
        if not es_manager.es.ping():
            print("Cannot connect to Elasticsearch")
            return False, None

        print("Connected to Elasticsearch")

        # Create index
        if es_manager.create_index():
            print(f"Elasticsearch index '{settings.ELASTICSEARCH['INDEX_NAME']}' is ready")
            return True, es_manager
        else:
            return False, None

    except Exception as e:
        print(f"Error setting up Elasticsearch: {e}")
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

    # Print summary
    print("\n" + "=" * 50)
    print("DATABASE INITIALIZATION SUMMARY")
    print("=" * 50)

    print("\n📊 MONGODB:")
    print(f"   Database Name: {settings.MONGODB['NAME']}")
    print(f"   Collection (Table) Name: products")
    print("   Fields:")
    print("     - name (StringField, max_length=200)")
    print("     - category (StringField, max_length=100)")
    print("     - price (DecimalField, precision=2)")
    print("     - stock (IntField)")
    print("     - description (StringField)")
    print("     - rating (FloatField)")
    print("   Indexes:")
    print("     - category (single field index)")
    print("     - price (single field index)")
    print("     - (category, price) (compound index)")

    print("\n🔍 ELASTICSEARCH:")
    print(f"   Index Name: {settings.ELASTICSEARCH['INDEX_NAME']}")
    print("   Fields (Mapping):")
    print("     - name (text, analyzed)")
    print("     - category (keyword, for exact match)")
    print("     - price (double)")
    print("     - stock (integer)")
    print("     - description (text, analyzed)")
    print("     - rating (float)")
    print("   Note: Elasticsearch automatically creates indexes for all fields")

    print(f"\n✅ MongoDB Setup: {'Success' if mongo_success else 'Failed'}")
    print(f"✅ Elasticsearch Setup: {'Success' if es_success else 'Failed'}")

    if mongo_success and es_success:
        print("\n🎉 Both databases are ready for use!")
        print("\nTo create products, use:")
        print("   product = ProductMongo(name='...', category='...', ...)")
        print("   product.save()")
    else:
        print("\n❌ Some databases failed to initialize. Check your connection settings.")


if __name__ == "__main__":
    main()
