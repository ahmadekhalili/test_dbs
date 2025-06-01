import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from pymongo import MongoClient, ASCENDING
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create MongoDB collections and Elasticsearch indexes for Product model'
    table_name = 'products'

    def add_arguments(self, parser):
        # No arguments needed - all settings come from Django settings
        pass

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database migration...'))

        # Get settings
        mongo_settings = getattr(settings, 'MONGODB', {})
        elastic_settings = getattr(settings, 'ELASTICSEARCH', {})

        # Setup MongoDB
        self.setup_mongodb(mongo_settings)

        # Setup Elasticsearch
        self.setup_elasticsearch(elastic_settings)

        self.stdout.write(self.style.SUCCESS('Database migration completed successfully!'))

    def setup_mongodb(self, mongo_settings):
        """Setup MongoDB collection and indexes"""
        self.stdout.write('Setting up MongoDB...')

        # Get MongoDB settings with defaults
        host = mongo_settings.get('HOST', 'localhost')
        port = mongo_settings.get('PORT', 27017)
        db_name = mongo_settings.get('NAME', 'default_db')
        username = mongo_settings.get('USER')
        password = mongo_settings.get('PASSWORD')

        try:
            # Connect to MongoDB with authentication if provided
            if username and password:
                client = MongoClient(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
            else:
                client = MongoClient(host, port)

            db = client[db_name]
            collection = db[self.table_name]

            # Create indexes matching the PostgreSQL model
            # Index on category field
            collection.create_index([("category", ASCENDING)], name="category_idx")
            self.stdout.write(f'✓ Created MongoDB index on category field')

            # Index on price field
            collection.create_index([("price", ASCENDING)], name="price_idx")
            self.stdout.write(f'✓ Created MongoDB index on price field')

            # Create a sample document to establish the collection structure
            sample_doc = {
                "name": "Sample Product",
                "category": "Electronics",
                "price": 99.99,
                "stock": 100,
                "description": "This is a sample product",
                "rating": 4.5
            }

            # Check if collection is empty and insert sample if needed
            if collection.count_documents({}) == 0:
                collection.insert_one(sample_doc)
                self.stdout.write('✓ Created sample document to establish collection structure')
                # Remove the sample document
                collection.delete_one({"name": "Sample Product"})
                self.stdout.write('✓ Removed sample document')

            self.stdout.write(
                self.style.SUCCESS(f'MongoDB setup completed for database: {db_name}, collection: {self.table_name}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'MongoDB setup failed: {str(e)}'))
            raise

    def setup_elasticsearch(self, elastic_settings):
        """Setup Elasticsearch index with mapping and settings"""
        self.stdout.write('Setting up Elasticsearch...')

        # Get Elasticsearch settings with defaults
        host = elastic_settings.get('HOST', 'localhost')
        port = elastic_settings.get('PORT', 9200)
        index_name = elastic_settings.get('INDEX_NAME', self.table_name)
        username = elastic_settings.get('USER')
        password = elastic_settings.get('PASSWORD')
        use_ssl = elastic_settings.get('USE_SSL', False)

        try:
            # Build connection string
            scheme = 'https' if use_ssl else 'http'

            if username and password:
                es_url = f'{scheme}://{username}:{password}@{host}:{port}'
            else:
                es_url = f'{scheme}://{host}:{port}'

            # Connect to Elasticsearch
            es = Elasticsearch([es_url], verify_certs=use_ssl)

            # Check if Elasticsearch is running
            if not es.ping():
                raise ConnectionError("Could not connect to Elasticsearch")

            # Delete index if it exists
            if es.indices.exists(index=index_name):
                es.indices.delete(index=index_name)
                self.stdout.write(f'✓ Deleted existing index: {index_name}')

            # Define mapping for the products index
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "product_analyzer": {
                                "type": "standard",
                                "stopwords": "_english_"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "name": {
                            "type": "text",
                            "analyzer": "product_analyzer",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "category": {
                            "type": "keyword",  # Indexed as keyword for exact matches
                            "fields": {
                                "text": {
                                    "type": "text",
                                    "analyzer": "product_analyzer"
                                }
                            }
                        },
                        "price": {
                            "type": "double"  # Indexed as double for range queries
                        },
                        "stock": {
                            "type": "integer"
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "product_analyzer"
                        },
                        "rating": {
                            "type": "float"
                        }
                    }
                }
            }

            # Create the index with mapping
            es.indices.create(index=index_name, body=mapping)
            self.stdout.write(f'✓ Created Elasticsearch index: {index_name}')
            self.stdout.write(f'✓ Applied mapping with indexed fields: category, price')

            # Verify the index was created
            if es.indices.exists(index=index_name):
                index_info = es.indices.get(index=index_name)
                self.stdout.write('✓ Index verification successful')

            self.stdout.write(self.style.SUCCESS(f'Elasticsearch setup completed for index: {index_name}'))

        except RequestError as e:
            self.stdout.write(self.style.ERROR(f'Elasticsearch RequestError: {str(e)}'))
            raise
        except ConnectionError as e:
            self.stdout.write(self.style.ERROR(f'Elasticsearch connection failed: {str(e)}'))
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Elasticsearch setup failed: {str(e)}'))
            raise

    def print_summary(self):
        """Print summary of created structures"""
        summary = """

=== MIGRATION SUMMARY ===

MongoDB Collection: table_name
- Indexes created:
  * category_idx (category field)
  * price_idx (price field)

Elasticsearch Index: table_name  
- Indexed fields:
  * category (keyword + text fields)
  * price (double field)
- Full text search enabled on:
  * name
  * description

=== END SUMMARY ===
        """
        self.stdout.write(self.style.SUCCESS(summary))