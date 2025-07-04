from django.conf import settings
from typing import List, Tuple, Callable  # این import وجود ندارد
from functools import partial
import random
import logging
import copy
import importlib

from setup_tables import ProductMongo
from .connections import get_mongo_client, get_els_client

logger = logging.getLogger('web')
mongo_collection = get_mongo_client()[settings.MONGODB['NAME']][ProductMongo._meta['collection']]
es_client = get_els_client()


def generate_test_data(count):
    """Generate test product data"""
    categories = ['Electronics', 'Books', 'Clothing', 'Food', 'Toys']
    return [{
        'name': f'Product {i}',
        'category': random.choice(categories),
        'price': round(random.uniform(10, 1000), 2),
        'stock': random.randint(0, 1000),
        'description': f'This is a detailed description for product {i}. ' * 10,
        'rating': round(random.uniform(1, 5), 1)
    } for i in range(count)]


def generate_realistic_test_data(count):
    """Generate more realistic test data for better full-text search testing"""
    categories = ['Electronics', 'Books', 'Clothing', 'Food', 'Toys', 'Sports', 'Home & Garden']

    # More realistic product names and descriptions
    product_templates = {
        'Electronics': [
            ('Smartphone Pro Max', 'High-quality premium smartphone with advanced camera and long battery life'),
            ('Wireless Headphones', 'Premium wireless headphones with noise cancellation and superior sound quality'),
            ('Gaming Laptop', 'Powerful gaming laptop with high-performance graphics and fast processor'),
            ('Smart TV', 'Ultra HD smart television with streaming capabilities and voice control'),
            ('Tablet Device', 'Lightweight tablet with high-resolution display and long-lasting battery')
        ],
        'Books': [
            ('Programming Guide', 'Comprehensive programming guide for beginners and advanced developers'),
            ('Science Fiction Novel', 'Exciting science fiction story with detailed world-building and characters'),
            ('Cooking Recipes', 'Collection of delicious recipes with detailed instructions and tips'),
            ('History Book', 'In-depth historical analysis with detailed research and documentation'),
            ('Self-Help Manual', 'Practical self-improvement guide with actionable advice and strategies')
        ],
        'Clothing': [
            ('Premium T-Shirt', 'High-quality cotton t-shirt with comfortable fit and durable fabric'),
            ('Designer Jeans', 'Stylish designer jeans with premium denim and perfect fit'),
            ('Winter Jacket', 'Warm winter jacket with weather protection and comfortable design'),
            ('Running Shoes', 'Professional running shoes with advanced cushioning and support'),
            ('Casual Dress', 'Elegant casual dress with premium fabric and versatile style')
        ]
    }

    data = []
    for i in range(count):
        category = random.choice(categories)

        if category in product_templates:
            name_template, desc_template = random.choice(product_templates[category])
            name = f"{name_template} {i}"
            description = f"{desc_template}. Product ID: {i}. Detailed specifications and features included."
        else:
            name = f'Product {i}'
            description = f'This is a detailed description for product {i} in {category} category. High quality and reliable.'

        product = {
            'name': name,
            'category': category,
            'price': round(random.uniform(10, 1000), 2),
            'stock': random.randint(0, 1000),
            'description': description,
            'rating': round(random.uniform(1, 5), 1)
        }
        data.append(product)

    return data


class BenchmarkOperationBuilder:

    def generate_argument_for_operations(self, methods):  # required call before build_operations
        methods = methods.copy()     # required (for .pop)
        argument_for_methods = {}
        if methods.get('write'):
            write_count = methods.pop('write')
            arg1 = generate_realistic_test_data(count=write_count)  # is list
            argument_for_methods['write'] = [arg1]
        for method_name, count in methods.items():  # other operations are only count (int)
            argument_for_methods[method_name] = [count]
        self.argument_for_methods = argument_for_methods
        return self

    def build_operations(self) -> List[Tuple[str, str, Callable]]:
        """Build operations based on specified tests including full-text search"""
        operations = []
        
        for db_name, class_name in settings.DATABASES_TO_TEST.items():
            # Dynamically import the class from database_operations module
            module = importlib.import_module('app1.database_operations')
            Database = getattr(module, class_name)
            
            if db_name == "Elastic":
                db_ob = Database(client=es_client)
            elif db_name == "Mongo":
                db_ob = Database(client=mongo_collection)
            elif db_name == "Postgres":
                db_ob = Database(client=None)  # PostgreSQL uses Django ORM, no client needed

            for method_name, count in settings.OPERATIONS_COUNT.items():
                method = getattr(db_ob, method_name, None)
                if method:
                    args = self.argument_for_methods.get(method_name, None)
                    func = partial(method, *[copy.deepcopy(arg) for arg in args]) if args else partial(method, count)
                    operations.append((db_name, method_name, count, func))

        return operations


from django.conf import settings
from typing import List, Tuple, Callable  # این import وجود ندارد
from functools import partial
import random
import logging
import copy
import importlib

from setup_tables import ProductMongo
from .connections import get_mongo_client, get_els_client

logger = logging.getLogger('web')
mongo_collection = get_mongo_client()[settings.MONGODB['NAME']][ProductMongo._meta['collection']]
es_client = get_els_client()


def generate_test_data(count):
    """Generate test product data"""
    categories = ['Electronics', 'Books', 'Clothing', 'Food', 'Toys']
    return [{
        'name': f'Product {i}',
        'category': random.choice(categories),
        'price': round(random.uniform(10, 1000), 2),
        'stock': random.randint(0, 1000),
        'description': f'This is a detailed description for product {i}. ' * 10,
        'rating': round(random.uniform(1, 5), 1)
    } for i in range(count)]


def generate_realistic_test_data(count):
    """Generate more realistic test data for better full-text search testing"""
    categories = ['Electronics', 'Books', 'Clothing', 'Food', 'Toys', 'Sports', 'Home & Garden']

    # More realistic product names and descriptions
    product_templates = {
        'Electronics': [
            ('Smartphone Pro Max', 'High-quality premium smartphone with advanced camera and long battery life'),
            ('Wireless Headphones', 'Premium wireless headphones with noise cancellation and superior sound quality'),
            ('Gaming Laptop', 'Powerful gaming laptop with high-performance graphics and fast processor'),
            ('Smart TV', 'Ultra HD smart television with streaming capabilities and voice control'),
            ('Tablet Device', 'Lightweight tablet with high-resolution display and long-lasting battery')
        ],
        'Books': [
            ('Programming Guide', 'Comprehensive programming guide for beginners and advanced developers'),
            ('Science Fiction Novel', 'Exciting science fiction story with detailed world-building and characters'),
            ('Cooking Recipes', 'Collection of delicious recipes with detailed instructions and tips'),
            ('History Book', 'In-depth historical analysis with detailed research and documentation'),
            ('Self-Help Manual', 'Practical self-improvement guide with actionable advice and strategies')
        ],
        'Clothing': [
            ('Premium T-Shirt', 'High-quality cotton t-shirt with comfortable fit and durable fabric'),
            ('Designer Jeans', 'Stylish designer jeans with premium denim and perfect fit'),
            ('Winter Jacket', 'Warm winter jacket with weather protection and comfortable design'),
            ('Running Shoes', 'Professional running shoes with advanced cushioning and support'),
            ('Casual Dress', 'Elegant casual dress with premium fabric and versatile style')
        ]
    }

    data = []
    for i in range(count):
        category = random.choice(categories)

        if category in product_templates:
            name_template, desc_template = random.choice(product_templates[category])
            name = f"{name_template} {i}"
            description = f"{desc_template}. Product ID: {i}. Detailed specifications and features included."
        else:
            name = f'Product {i}'
            description = f'This is a detailed description for product {i} in {category} category. High quality and reliable.'

        product = {
            'name': name,
            'category': category,
            'price': round(random.uniform(10, 1000), 2),
            'stock': random.randint(0, 1000),
            'description': description,
            'rating': round(random.uniform(1, 5), 1)
        }
        data.append(product)

    return data


class BenchmarkOperationBuilder:

    def generate_argument_for_operations(self, methods):  # required call before build_operations
        methods = methods.copy()  # required (for .pop)
        argument_for_methods = {}
        if methods.get('write'):
            write_count = methods.pop('write')
            arg1 = generate_realistic_test_data(count=write_count)  # is list
            argument_for_methods['write'] = [arg1]
        for method_name, count in methods.items():  # other operations are only count (int)
            argument_for_methods[method_name] = [count]
        self.argument_for_methods = argument_for_methods
        return self

    def build_operations(self) -> List[Tuple[str, str, Callable]]:
        """Build operations based on specified tests including full-text search"""
        operations = []

        for db_name, class_name in settings.DATABASES_TO_TEST.items():
            # Dynamically import the class from database_operations module
            module = importlib.import_module('app1.database_operations')
            Database = getattr(module, class_name)

            if db_name == "Elastic":
                db_ob = Database(client=es_client)
            elif db_name == "Mongo":
                db_ob = Database(client=mongo_collection)
            elif db_name == "Postgres":
                db_ob = Database(client=None)  # PostgreSQL uses Django ORM, no client needed

            for method_name, count in settings.OPERATIONS_COUNT.items():
                method = getattr(db_ob, method_name, None)
                if method:
                    args = self.argument_for_methods.get(method_name, None)
                    func = partial(method, *[copy.deepcopy(arg) for arg in args]) if args else partial(method, count)
                    operations.append((db_name, method_name, count, func))

        return operations


import pymongo
import mongoengine
from mongoengine import Document, StringField, DecimalField, IntField, FloatField
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError, NotFoundError
from django.db import connection, transaction
from django.conf import settings
import logging
import os
import sys

logger = logging.getLogger('web')


class DatabaseCleanup:
    """
    dop table Product and products from mongo elastic
    """

    def __init__(self):
        """Initialize cleanup utility with database connections"""
        self.logger = logging.getLogger(__name__)
        self._setup_connections()

    def _setup_connections(self):
        """Setup connections to all three databases using your specific credentials"""
        # PostgreSQL is already connected via Django using your akh_db database

        # Setup MongoDB connection to your test_db database
        try:
            # Your MongoDB configuration doesn't use authentication, so we build a simple URI
            # This connects to localhost:27016/test_db without username/password
            mongo_uri = f"mongodb://{settings.MONGODB['HOST']}:{settings.MONGODB['PORT']}/{settings.MONGODB['NAME']}"

            mongoengine.connect(
                db=settings.MONGODB['NAME'],  # This will be 'test_db'
                host=mongo_uri,
                alias='default'
            )
            print(f"✅ Connected to MongoDB: {settings.MONGODB['NAME']} on port {settings.MONGODB['PORT']}")
        except Exception as e:
            print(f"⚠️  MongoDB connection failed: {e}")

        # Setup Elasticsearch connection to your local instance
        try:
            # Your Elasticsearch configuration doesn't use authentication or SSL
            # So we create a simple HTTP connection to localhost:9200
            scheme = 'http'  # Your USE_SSL is False
            host = f"{scheme}://{settings.ELASTICSEARCH['HOST']}:{settings.ELASTICSEARCH['PORT']}"

            self.es = Elasticsearch(
                [host],
                http_auth=None,  # No authentication needed for your setup
                verify_certs=False,  # No SSL verification needed
                request_timeout=30
            )

            if self.es.ping():
                print(f"✅ Connected to Elasticsearch: {host}")
                print(f"   Target index: '{settings.ELASTICSEARCH['INDEX_NAME']}'")
            else:
                print("⚠️  Elasticsearch connection failed")
                self.es = None
        except Exception as e:
            print(f"⚠️  Elasticsearch connection failed: {e}")
            self.es = None

    def cleanup_postgresql(self):
        """
        Clean up PostgreSQL Product table and related indexes.
        This removes both the Django model table and any custom full-text search indexes.
        """
        print("\n🐘 Cleaning PostgreSQL...")

        try:
            with connection.cursor() as cursor:
                # First, check if the products table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'app1_product'
                    );
                """)
                table_exists = cursor.fetchone()[0]

                if table_exists:
                    # Drop custom full-text search indexes first
                    custom_indexes = [
                        'products_fulltext_gin_idx',
                        'products_name_trgm_idx',
                        'products_description_trgm_idx'
                    ]

                    for index_name in custom_indexes:
                        try:
                            cursor.execute(f"DROP INDEX IF EXISTS {index_name};")
                            print(f"   ✅ Dropped index: {index_name}")

                        except Exception as e:
                            print(f"   ⚠️  Could not drop index {index_name}: {e}")

                    # Drop the products table (this will also drop Django-created indexes)
                    cursor.execute("DROP TABLE IF EXISTS app1_product CASCADE;")
                    print("   ✅ Dropped Product table")

                    # Also drop any Django migration entries for the products app
                    cursor.execute("""
                        DELETE FROM django_migrations 
                        WHERE app = 'app1' OR migration LIKE '%product%';
                    """)
                    print("   ✅ Cleaned Django migration records")

                else:
                    print("   ℹ️  Product table doesn't exist")

                return True

        except Exception as e:
            print(f"   ❌ Error cleaning PostgreSQL: {e}")
            return False

    def cleanup_mongodb(self):
        """
        Clean up MongoDB products collection and all its indexes.
        This completely removes the collection and recreates it fresh.
        """
        print("\n📦 Cleaning MongoDB...")

        try:
            # Get the database
            db = mongoengine.connection.get_db()

            # Check if products collection exists
            if 'products' in db.list_collection_names():
                # Drop the entire collection (this removes all documents and indexes)
                db.products.drop()
                print("   ✅ Dropped products collection")
                print("   ✅ All indexes automatically removed with collection")
            else:
                print("   ℹ️  Products collection doesn't exist")

            return True

        except Exception as e:
            print(f"   ❌ Error cleaning MongoDB: {e}")
            return False

    def cleanup_elasticsearch(self):
        """
        Clean up Elasticsearch product index.
        This removes the entire index including all documents and mappings.
        """
        print("\n🔍 Cleaning Elasticsearch...")

        if not self.es:
            print("   ⚠️  Elasticsearch not connected, skipping cleanup")
            return False

        try:
            index_name = settings.ELASTICSEARCH['INDEX_NAME']

            # Check if index exists
            if self.es.indices.exists(index=index_name):
                # Delete the index (this removes all documents, mappings, and settings)
                self.es.indices.delete(index=index_name)
                print(f"   ✅ Deleted index: {index_name}")
                print("   ✅ All documents and mappings removed")
            else:
                print(f"   ℹ️  Index '{index_name}' doesn't exist")

            return True

        except Exception as e:
            print(f"   ❌ Error cleaning Elasticsearch: {e}")
            return False

    def verify_cleanup(self):
        """
        Verify that all cleanup operations were successful.
        This checks each database to confirm data removal.
        """
        print("\n🔍 Verifying cleanup...")

        # Verify PostgreSQL cleanup
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'app1_product'
                    );
                """)
                pg_table_exists = cursor.fetchone()[0]

                if pg_table_exists:
                    print("   ❌ PostgreSQL: Product table still exists")
                else:
                    print("   ✅ PostgreSQL: Product table removed")
        except Exception as e:
            print(f"   ⚠️  PostgreSQL verification failed: {e}")

        # Verify MongoDB cleanup
        try:
            db = mongoengine.connection.get_db()
            mongo_collection_exists = 'products' in db.list_collection_names()

            if mongo_collection_exists:
                print("   ❌ MongoDB: Products collection still exists")
            else:
                print("   ✅ MongoDB: Products collection removed")
        except Exception as e:
            print(f"   ⚠️  MongoDB verification failed: {e}")

        # Verify Elasticsearch cleanup
        try:
            if self.es:
                index_name = settings.ELASTICSEARCH['INDEX_NAME']
                es_index_exists = self.es.indices.exists(index=index_name)

                if es_index_exists:
                    print(f"   ❌ Elasticsearch: Index '{index_name}' still exists")
                else:
                    print(f"   ✅ Elasticsearch: Index '{index_name}' removed")
            else:
                print("   ⚠️  Elasticsearch verification skipped (not connected)")
        except Exception as e:
            print(f"   ⚠️  Elasticsearch verification failed: {e}")

    def run_complete_cleanup(self):
        """
        Execute complete cleanup process across all databases.
        This is the main method that orchestrates the entire cleanup.
        """
        print("=== DATABASE CLEANUP UTILITY ===\n")
        print("This will remove ALL Product data from:")
        print("  📊 PostgreSQL (Django ORM)")
        print("  📦 MongoDB (MongoEngine)")
        print("  🔍 Elasticsearch")
        print("\n⚠️  WARNING: This action cannot be undone!")

        # Ask for confirmation
        confirmation = input("\nAre you sure you want to proceed? (type 'yes' to confirm): ")
        if confirmation.lower() != 'yes':
            print("❌ Cleanup cancelled by user")
            return False

        print("\n🚀 Starting cleanup process...\n")

        # Execute cleanup for each database
        results = {
            'postgresql': self.cleanup_postgresql(),
            'mongodb': self.cleanup_mongodb(),
            'elasticsearch': self.cleanup_elasticsearch()
        }

        # Verify all cleanup operations
        self.verify_cleanup()

        # Summary
        print("\n" + "=" * 60)
        print("📊 CLEANUP SUMMARY")
        print("=" * 60)

        success_count = sum(results.values())
        total_count = len(results)

        for db_name, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"{db_name.capitalize():15} {status}")

        if success_count == total_count:
            print(f"\n🎉 CLEANUP COMPLETED SUCCESSFULLY!")
            print("All Product data has been removed from all databases.")
            print("\n💡 You can now run setup_tables.py to recreate clean tables.")
        else:
            print(f"\n⚠️  PARTIAL CLEANUP: {success_count}/{total_count} databases cleaned")
            print("Check the errors above and retry if needed.")

        return success_count == total_count