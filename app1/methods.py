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
            arg1 = generate_test_data(count=write_count)  # is list
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
