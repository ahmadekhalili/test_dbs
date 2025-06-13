from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction, connection
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.test import APIRequestFactory

import time
import random
import logging
from decimal import Decimal

from .models import Product
from .methods import BenchmarkOperationBuilder
from .serializers import ProductSerializer, BenchmarkResultSerializer
from .connections import get_mongo_client, get_els_client

from setup_tables import ProductMongo

logger = logging.getLogger('web')
mongo_collection = get_mongo_client()[settings.MONGODB['NAME']][ProductMongo._meta['collection']]
es_client = get_els_client()


@method_decorator(csrf_exempt, name='dispatch')
class BenchmarkAPIView(APIView):
    def check_database_connections(self):
        """Verify all database connections are working before running benchmarks."""
        errors = []

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            errors.append(f"PostgreSQL connection failed: {e}")

        try:
            mongo_collection.database.client.admin.command('ping')
        except Exception as e:
            errors.append(f"MongoDB connection failed: {e}")

        try:
            es_client.cluster.health()
        except Exception as e:
            errors.append(f"Elasticsearch connection failed: {e}")

        return errors

    def clear_data(self):
        """Clear all test data with error handling"""
        try:
            Product.objects.all().delete()

            # MongoDB - Drop collection
            mongo_collection.delete_many({})

            # Elasticsearch - Delete index
            index_name = 'products'  # or whatever your index name is
            es_client.delete_by_query(
                index=index_name,
                body={
                    "query": {
                        "match_all": {}
                    }
                }
            )

            print("Product tables removed from all databases")
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")

    def get(self, request):
        """Run benchmark tests with comprehensive error handling"""
        # Connection check
        connection_errors = self.check_database_connections()
        if connection_errors:
            return Response({
                'error': 'Database connection check failed',
                'details': connection_errors
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


        if settings.REFRESH:
            self.clear_data()

        # Build operations using SOLID principles
        operation_builder = BenchmarkOperationBuilder()
        benchmark_operations = operation_builder.generate_argument_for_operations(settings.OPERATIONS_COUNT).build_operations()
        # Execute benchmarks
        results = []
        errors = []

        for database, operation_type, count, benchmark_func in benchmark_operations:
            try:
                execution_time, operation = benchmark_func()

                results.append({
                    'database': database,
                    'operation': operation,
                    'total_time': execution_time,
                    'records_processed': count,
                    'avg_time_per_record': execution_time / count
                })
                logger.info(f"Completed {database} {operation} benchmark: {execution_time:.3f}s")
            except Exception as e:
                error_msg = f"{database} {operation_type} benchmark failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # Cleanup
        if settings.REFRESH:
            self.clear_data()
            logger.info('All data cleared after test')

        # Response
        response_data = {'results': BenchmarkResultSerializer(results, many=True).data}
        if errors:
            response_data['warnings'] = errors

        return Response(response_data, status=status.HTTP_200_OK)


def benchmark_results_view(request):
    """Render the benchmark results table view"""
    # Results will be shown after running benchmark via API
    factory = APIRequestFactory()
    get_request = factory.get('/fake-path/')  # URL can be dummy
    # Pass through the authenticated user if needed
    get_request.user = request.user

    # Call the view's GET method using DRF's `as_view`
    # This will invoke the same lifecycle as an external HTTP GET
    response = BenchmarkAPIView().get(get_request).data
    dbs_benchmarks = response.get('results')
    if dbs_benchmarks:
        logger.info(f"response received, dbs results: {len(response['results'])}")
        return render(request, 'app1/benchmark_results.html', {'results': dbs_benchmarks})
    else:
        logger.error(f"no result from api response. response: {response}")
        return render(request, 'app1/benchmark_results.html', {
            'results': []
        })
