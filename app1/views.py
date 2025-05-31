from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

import time
import random
from decimal import Decimal

from .models import Product
from .serializers import ProductSerializer, BenchmarkResultSerializer
from .methods import ensure_es_index
from .connections import es_client, mongo_collection, es_mapping


class BenchmarkAPIView(APIView):
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

    def benchmark_postgres_read(self, query_count):
        """Benchmark PostgreSQL read operations"""
        start_time = time.time()

        for _ in range(query_count):
            # Random queries
            if random.choice([True, False]):
                Product.objects.filter(category='Electronics').all()
            else:
                Product.objects.filter(price__gte=100, price__lte=500).all()

        end_time = time.time()
        return end_time - start_time

    def benchmark_mongodb_write(self, data):
        """Benchmark MongoDB write operations"""
        start_time = time.time()

        mongo_collection.insert_many(data)

        end_time = time.time()
        return end_time - start_time

    def benchmark_mongodb_read(self, query_count):
        """Benchmark MongoDB read operations"""
        start_time = time.time()

        for _ in range(query_count):
            if random.choice([True, False]):
                list(mongo_collection.find({'category': 'Electronics'}))
            else:
                list(mongo_collection.find({'price': {'$gte': 100, '$lte': 500}}))

        end_time = time.time()
        return end_time - start_time

    @ensure_es_index(index_name='products', mapping=es_mapping)
    def benchmark_elasticsearch_write(self, data):
        """Benchmark ElasticSearch write operations"""
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

    def benchmark_elasticsearch_read(self, query_count):
        """Benchmark ElasticSearch read operations"""
        start_time = time.time()

        for _ in range(query_count):
            if random.choice([True, False]):
                # فقط از فیلدهای index شده استفاده می‌کنیم
                es_client.search(
                    index='products',
                    body={'query': {'term': {'category': 'Electronics'}}}
                )
            else:
                # فقط از فیلدهای index شده استفاده می‌کنیم
                es_client.search(
                    index='products',
                    body={'query': {'range': {'price': {'gte': 100, 'lte': 500}}}}
                )

        end_time = time.time()
        return end_time - start_time

    def clear_data(self):
        """Clear all test data"""
        # Clear PostgreSQL
        Product.objects.all().delete()

        # Clear MongoDB
        mongo_collection.delete_many({})

        # Clear ElasticSearch
        es_client.delete_by_query(
            index='products',
            body={'query': {'match_all': {}}}
        )

    def post(self, request):
        """Run benchmark tests"""
        record_count = request.data.get('record_count', 1000)
        query_count = request.data.get('query_count', 100)

        # Clear existing data
        self.clear_data()

        # Generate test data
        test_data = self.generate_test_data(record_count)

        results = []

        # PostgreSQL benchmarks
        postgres_write_time = self.benchmark_postgres_write(test_data)
        results.append({
            'database': 'PostgreSQL',
            'operation': 'Write',
            'total_time': postgres_write_time,
            'records_processed': record_count,
            'avg_time_per_record': postgres_write_time / record_count
        })

        postgres_read_time = self.benchmark_postgres_read(query_count)
        results.append({
            'database': 'PostgreSQL',
            'operation': 'Read',
            'total_time': postgres_read_time,
            'records_processed': query_count,
            'avg_time_per_record': postgres_read_time / query_count
        })

        # MongoDB benchmarks
        mongodb_write_time = self.benchmark_mongodb_write(test_data)
        results.append({
            'database': 'MongoDB',
            'operation': 'Write',
            'total_time': mongodb_write_time,
            'records_processed': record_count,
            'avg_time_per_record': mongodb_write_time / record_count
        })

        mongodb_read_time = self.benchmark_mongodb_read(query_count)
        results.append({
            'database': 'MongoDB',
            'operation': 'Read',
            'total_time': mongodb_read_time,
            'records_processed': query_count,
            'avg_time_per_record': mongodb_read_time / query_count
        })

        # ElasticSearch benchmarks
        es_write_time = self.benchmark_elasticsearch_write(test_data)
        results.append({
            'database': 'ElasticSearch',
            'operation': 'Write',
            'total_time': es_write_time,
            'records_processed': record_count,
            'avg_time_per_record': es_write_time / record_count
        })

        es_read_time = self.benchmark_elasticsearch_read(query_count)
        results.append({
            'database': 'ElasticSearch',
            'operation': 'Read',
            'total_time': es_read_time,
            'records_processed': query_count,
            'avg_time_per_record': es_read_time / query_count
        })

        # Clear data after benchmark
        self.clear_data()

        serializer = BenchmarkResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)