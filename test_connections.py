#!/usr/bin/env python
"""
Test script to verify all database connections are working properly.
Run this after starting Docker containers to ensure everything is set up correctly.
"""

import os
import sys
import django
from decimal import Decimal

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dbs_test.settings')
django.setup()

from django.db import connection
from app1.models import Product
from app1.connections import get_mongo_client, get_els_client
es_client = get_els_client()
mongo_collection = get_mongo_client()


def test_postgresql():
    """Test PostgreSQL connection and basic operations"""
    print("\n1. Testing PostgreSQL Connection...")
    try:
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print("   ✓ PostgreSQL connection successful")

        # Test model operations
        test_product = Product.objects.create(
            name="Test Product",
            category="Test",
            price=Decimal("99.99"),
            stock=100,
            description="Test description",
            rating=4.5
        )
        print("   ✓ Successfully created test product with ID:", test_product.id)

        # Test query
        found_product = Product.objects.get(id=test_product.id)
        print("   ✓ Successfully retrieved product:", found_product.name)

        # Clean up
        test_product.delete()
        print("   ✓ Successfully deleted test product")

        return True
    except Exception as e:
        print(f"   ✗ PostgreSQL test failed: {e}")
        return False


def test_mongodb():
    """Test MongoDB connection and basic operations"""
    print("\n2. Testing MongoDB Connection...")
    try:
        # Test insert
        result = mongo_collection.insert_one({
            'name': 'Test MongoDB Product',
            'category': 'Test',
            'price': 99.99,
            'stock': 100,
            'description': 'Test MongoDB description',
            'rating': 4.5
        })
        print("   ✓ Successfully inserted document with ID:", result.inserted_id)

        # Test query
        found_doc = mongo_collection.find_one({'_id': result.inserted_id})
        print("   ✓ Successfully retrieved document:", found_doc['name'])

        # Test index usage
        explain = mongo_collection.find({'category': 'Test'}).explain()
        if 'winningPlan' in explain['executionStats']:
            print("   ✓ MongoDB indexes are being used")

        # Clean up
        mongo_collection.delete_one({'_id': result.inserted_id})
        print("   ✓ Successfully deleted test document")

        return True
    except Exception as e:
        print(f"   ✗ MongoDB test failed: {e}")
        return False


def test_elasticsearch():
    """Test Elasticsearch connection and basic operations"""
    print("\n3. Testing Elasticsearch Connection...")
    try:
        # Check cluster health
        health = es_client.cluster.health()
        print(f"   ✓ Elasticsearch cluster status: {health['status']}")

        # Test document indexing
        doc = {
            'name': 'Test ES Product',
            'category': 'Test',
            'price': 99.99,
            'stock': 100,
            'description': 'Test Elasticsearch description',
            'rating': 4.5
        }

        response = es_client.index(index='products', id='test_doc', body=doc, refresh=True)
        print("   ✓ Successfully indexed document:", response['_id'])

        # Test retrieval
        get_response = es_client.get(index='products', id='test_doc')
        print("   ✓ Successfully retrieved document:", get_response['_source']['name'])

        # Test search
        search_response = es_client.search(
            index='products',
            body={'query': {'term': {'category': 'Test'}}}
        )
        print(f"   ✓ Search query executed, found {search_response['hits']['total']['value']} documents")

        # Clean up
        es_client.delete(index='products', id='test_doc', refresh=True)
        print("   ✓ Successfully deleted test document")

        return True
    except Exception as e:
        print(f"   ✗ Elasticsearch test failed: {e}")
        return False


def main():
    """Run all connection tests"""
    print("=" * 60)
    print("Database Connection Test Suite")
    print("=" * 60)

    results = {
        'PostgreSQL': test_postgresql(),
        'MongoDB': test_mongodb(),
        'Elasticsearch': test_elasticsearch()
    }

    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    all_passed = True
    for db, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{db}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All database connections are working properly!")
        print("You can now run the benchmark API at: http://localhost:8000/api/benchmark/")
    else:
        print("\n✗ Some database connections failed. Please check the Docker containers.")
        print("Run 'docker-compose ps' to check container status.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())