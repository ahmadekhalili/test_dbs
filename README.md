## use:
Make the setup script executable and run it:
bashchmod +x setup.sh
./setup.sh

The script will handle everything automatically, including:

Starting all database containers
Waiting for them to be ready
Installing Python dependencies
Running migrations
Testing connections


Once setup completes successfully, start your Django server:
bashsource venv/bin/activate
python manage.py runserver

Test the benchmark API:
bashcurl -X POST http://localhost:8000/api/benchmark/ \
  -H "Content-Type: application/json" \
  -d '{"record_count": 1000, "query_count": 100}'
 
 
## Test fauilure
docker-compose logs postgres_db
docker-compose logs mongo_db
docker-compose logs elasticsearch_db

Test connections manually:
bashpython test_connections.py

Ensure ports aren't already in use:
The project uses ports 5431 (PostgreSQL), 27016 (MongoDB), and 9200 (Elasticsearch). Make sure these are free.