# 🗄️ Multi-Database Benchmark Testing Platform

<div align="center">

[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-005571?style=for-the-badge&logo=elasticsearch&logoColor=white)](https://elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com/)

*A comprehensive Django application for benchmarking database operations across PostgreSQL, MongoDB, and Elasticsearch*

</div>

---

## 🚀 Quick Start

### ⚡ Installation & Setup

1. **🔧 Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **🐳 Start Database Containers**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **🔄 Run Django Migrations**
   ```bash
   python manage.py migrate
   ```

4. **✅ Test Database Connections**
   ```bash
   python test_connections.py
   ```

5. **🌐 Start Development Server**
   ```bash
   python manage.py runserver
   ```

---

## 🎯 Usage

### 📊 Benchmark API Testing

Test the performance comparison across all databases:

```bash
curl -X POST http://localhost:8000/api/benchmark/ \
  -H "Content-Type: application/json" \
  -d '{"record_count": 1000, "query_count": 100}'
```

### 🔧 Configuration

The application supports customizable benchmark parameters in `settings.py`:

- **📈 OPERATIONS**: Configure read/write/aggregate operation counts
- **🗄️ DATABASES_TO_TEST**: Select which databases to benchmark
- **🔄 REFRESH**: Enable/disable database cleanup between tests

---

## 🏗️ Architecture

### 🗃️ Database Configuration

| Database | Port | Purpose |
|----------|------|---------|
| 🐘 PostgreSQL | 5431 | Relational data operations |
| 🍃 MongoDB | 27016 | Document-based operations |
| 🔍 Elasticsearch | 9200 | Search and analytics |

### 📁 Project Structure

```
📦 test_dbs/
├── 🎯 app1/                    # Main application
│   ├── 🔧 database_operations.py  # DB strategy implementations
│   ├── 🔗 connections.py          # Database connection management
│   ├── 📊 views.py                # API endpoints
│   └── 🏗️ models.py               # Django models
├── 🐳 docker/                 # Docker configuration
├── 📝 logs/                   # Application logs
├── ⚙️ requirements.txt        # Python dependencies
└── 🛠️ setup_tables.py         # MongoDB schema setup
```

---

## 🔍 Troubleshooting

### 🚨 Common Issues

**📍 Port Conflicts**
```bash
# Check if ports are in use
netstat -an | grep :5431
netstat -an | grep :27016
netstat -an | grep :9200
```

**📋 Database Logs**
```bash
docker-compose logs postgres_db
docker-compose logs mongo_db
docker-compose logs elasticsearch_db
```

**🔗 Connection Testing**
```bash
python test_connections.py
```

### 🆘 Error Resolution

- Ensure Docker containers are running: `docker-compose ps`
- Verify port availability (5431, 27016, 9200)
- Check database credentials in `settings.py`
- Review logs in the `logs/` directory

---

## 🛠️ Development

### 🔄 Database Migration

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Custom database migration command
python manage.py migrate_dbs
```

---

## 📈 Performance Metrics

The benchmark API provides comprehensive performance metrics including:

- ⚡ **Operation Speed**: Average execution time
- 📊 **Throughput**: Operations per second
- 💾 **Memory Usage**: Resource consumption
- 🔄 **Connection Efficiency**: Database connection performance

---

<div align="center">

**Made with ❤️ for database performance testing**

</div>