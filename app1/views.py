from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction, connection
from django.conf import settings
import time
import random
import logging
from decimal import Decimal

from .models import Product
from .serializers import ProductSerializer, BenchmarkResultSerializer
from .connections import get_mongo_client, get_els_client

from setup_tables import ProductMongo

logger = logging.getLogger(__name__)
mongo_collection = get_mongo_client()[settings.MONGODB['NAME']][ProductMongo._meta['collection']]
es_client = get_els_client()


class BenchmarkAPIView(APIView):
    def check_database_connections(self):
        """
        Verify all database connections are working before running benchmarks.
        This prevents partial benchmark runs if a database is down.
        """
        errors = []

        # Check PostgreSQL
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            errors.append(f"PostgreSQL connection failed: {e}")

        # Check MongoDB
        try:
            mongo_collection.database.client.admin.command('ping')
        except Exception as e:
            errors.append(f"MongoDB connection failed: {e}")

        # Check Elasticsearch
        try:
            es_client.cluster.health()
        except Exception as e:
            errors.append(f"Elasticsearch connection failed: {e}")

        return errors

    def generate_test_data(self, count):
        """Generate test product data"""
        categories = ['Electronics', 'Books', 'Clothing', 'Food', 'Toys']
        data = []

        for i in range(count):
            product = {
                'name': f'Product {i}',
                'category': random.choice(categories),
                'price': round(random.uniform(10, 1000), 2),
                'stock': random.randint(0, 1000),
                'description': f'This is a detailed description for product {i}. ' * 10,
                'rating': round(random.uniform(1, 5), 1)
            }
            data.append(product)

        return data

    def benchmark_postgres_write(self, data):
        """Benchmark PostgreSQL write operations"""
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
            return end_time - start_time
        except Exception as e:
            logger.error(f"PostgreSQL write benchmark failed: {e}")
            raise

    def benchmark_postgres_read(self, query_count):
        """Benchmark PostgreSQL read operations"""
        try:
            start_time = time.time()

            for _ in range(query_count):
                # Random queries
                if random.choice([True, False]):
                    list(Product.objects.filter(category='Electronics'))
                else:
                    list(Product.objects.filter(price__gte=100, price__lte=500))

            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            logger.error(f"PostgreSQL read benchmark failed: {e}")
            raise

    def benchmark_mongodb_write(self, data):
        """Benchmark MongoDB write operations"""
        try:
            start_time = time.time()

            mongo_collection.insert_many(data)

            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            logger.error(f"MongoDB write benchmark failed: {e}")
            raise

    def benchmark_mongodb_read(self, query_count):
        """Benchmark MongoDB read operations"""
        try:
            start_time = time.time()

            for _ in range(query_count):
                if random.choice([True, False]):
                    list(mongo_collection.find({'category': 'Electronics'}))
                else:
                    list(mongo_collection.find({'price': {'$gte': 100, '$lte': 500}}))

            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            logger.error(f"MongoDB read benchmark failed: {e}")
            raise

    def benchmark_elasticsearch_write(self, data):
        """Benchmark ElasticSearch write operations"""
        try:
            start_time = time.time()

            # Bulk indexing
            actions = []
            for i, item in enumerate(data):
                actions.append({
                    "index": {
                        "_index": "products",
                        "_id": i
                    }
                })
                actions.append(item)

            es_client.bulk(body=actions, refresh=True)

            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            logger.error(f"Elasticsearch write benchmark failed: {e}")
            raise

    def benchmark_elasticsearch_read(self, query_count):
        """Benchmark ElasticSearch read operations"""
        try:
            start_time = time.time()

            for _ in range(query_count):
                if random.choice([True, False]):
                    es_client.search(
                        index='products',
                        body={'query': {'term': {'category': 'Electronics'}}}
                    )
                else:
                    es_client.search(
                        index='products',
                        body={'query': {'range': {'price': {'gte': 100, 'lte': 500}}}}
                    )

            end_time = time.time()
            return end_time - start_time
        except Exception as e:
            logger.error(f"Elasticsearch read benchmark failed: {e}")
            raise

    def clear_data(self):
        """Clear all test data with error handling"""
        try:
            # Clear PostgreSQL
            Product.objects.all().delete()
            logger.info("PostgreSQL data cleared")
        except Exception as e:
            logger.error(f"Failed to clear PostgreSQL data: {e}")

        try:
            # Clear MongoDB
            mongo_collection.delete_many({})
            logger.info("MongoDB data cleared")
        except Exception as e:
            logger.error(f"Failed to clear MongoDB data: {e}")

        try:
            # Clear ElasticSearch
            es_client.delete_by_query(
                index='products',
                body={'query': {'match_all': {}}},
                conflicts='proceed'  # Continue even if there are version conflicts
            )
            logger.info("Elasticsearch data cleared")
        except Exception as e:
            logger.error(f"Failed to clear Elasticsearch data: {e}")

    def post(self, request):
        """Run benchmark tests with comprehensive error handling"""
        # First check all database connections
        connection_errors = self.check_database_connections()
        if connection_errors:
            return Response({
                'error': 'Database connection check failed',
                'details': connection_errors
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        record_count = request.data.get('record_count', 1000)
        query_count = request.data.get('query_count', 100)

        # Validate input
        if record_count < 1 or record_count > 100000:
            return Response({
                'error': 'record_count must be between 1 and 100000'
            }, status=status.HTTP_400_BAD_REQUEST)

        if query_count < 1 or query_count > 10000:
            return Response({
                'error': 'query_count must be between 1 and 10000'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Clear existing data
        self.clear_data()

        # Generate test data
        test_data = self.generate_test_data(record_count)

        results = []
        errors = []

        # Run benchmarks with individual error handling
        benchmark_operations = [
            ('PostgreSQL', 'Write', lambda: self.benchmark_postgres_write(test_data)),
            ('PostgreSQL', 'Read', lambda: self.benchmark_postgres_read(query_count)),
            ('MongoDB', 'Write', lambda: self.benchmark_mongodb_write(test_data)),
            ('MongoDB', 'Read', lambda: self.benchmark_mongodb_read(query_count)),
            ('ElasticSearch', 'Write', lambda: self.benchmark_elasticsearch_write(test_data)),
            ('ElasticSearch', 'Read', lambda: self.benchmark_elasticsearch_read(query_count)),
        ]

        for database, operation, benchmark_func in benchmark_operations:
            try:
                execution_time = benchmark_func()
                records = record_count if operation == 'Write' else query_count

                results.append({
                    'database': database,
                    'operation': operation,
                    'total_time': execution_time,
                    'records_processed': records,
                    'avg_time_per_record': execution_time / records
                })
                logger.info(f"Completed {database} {operation} benchmark: {execution_time:.3f}s")
            except Exception as e:
                error_msg = f"{database} {operation} benchmark failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # Clear data after benchmark
        self.clear_data()

        # Return results with any errors that occurred
        response_data = {
            'results': BenchmarkResultSerializer(results, many=True).data
        }

        if errors:
            response_data['warnings'] = errors

        return Response(response_data, status=status.HTTP_200_OK)