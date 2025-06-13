from django.apps import AppConfig
from elasticsearch import Elasticsearch



class App1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app1'
