from django.urls import path

from . import views
# note1: update sitemap.py if changed here.


app_name = 'app1'

urlpatterns = [
    path('', views.benchmark_results_view, name='benchmark_results'),
    path('pure', views.pure_benchmark_view, name='pure_benchmark_view'),
    path('remove_tables/', views.remove_tables, name='remove_tables'),
    path('api/benchmark/', views.BenchmarkAPIView.as_view(), name='benchmark'),
]
