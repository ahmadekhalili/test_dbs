# Database Testing & Benchmarking Django Project

## Project Overview
This is a Django application designed to test and benchmark database operations across multiple database systems: PostgreSQL, MongoDB, and Elasticsearch. The project implements a benchmarking API to compare performance across different database backends.

## Development Environment

### Running the Application
```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Start Django development server
python manage.py runserver
```

### Database Setup
The project uses Docker Compose to run multiple databases:
- PostgreSQL on port 5431
- MongoDB on port 27016  
- Elasticsearch on port 9200

Start databases:
```bash
cd docker
docker-compose up -d
```

### Testing Database Connections
```bash
python test_connections.py
```

### Running Migrations
```bash
python manage.py migrate
```

### Creating tables
```bash
python manage.py setup_tables (before calling http://localhost:8000/api/benchmark/)
```

### Benchmark API Testing
```bash
curl -X POST http://localhost:8000/api/benchmark/ \
  -H "Content-Type: application/json" \
  -d '{"record_count": 1000, "query_count": 100}'
```

## Project Structure

### Core Components
- `app1/models.py` - Django models for PostgreSQL
- `app1/database_operations.py` - Database operation strategies for each DB
- `app1/connections.py` - Database connection management
- `app1/views.py` - API endpoints including BenchmarkAPIView
- `setup_tables.py` - MongoDB model definitions

### Key Configuration
- Database settings in `dbs_test/settings.py`
- Test parameters: `OPERATIONS_COUNT`, `DATABASES_TO_TEST`, `REFRESH`
- Logging configuration for django.log, web.log, driver.log

### Troubleshooting

Check database logs:
```bash
docker-compose logs postgres_db
docker-compose logs mongo_db  
docker-compose logs elasticsearch_db
```

Ensure ports 5431, 27016, and 9200 are available.

## Dependencies
See `requirements.txt` for full dependency list. Key packages:
- Django & DRF
- psycopg2-binary (PostgreSQL)
- pymongo & mongoengine (MongoDB)
- elasticsearch client

## Testing
The application includes database benchmarking tests accessible via the REST API at `/api/benchmark/`.