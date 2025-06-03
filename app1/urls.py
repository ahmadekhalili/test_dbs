from django.urls import path

from . import views
# note1: update sitemap.py if changed here.


app_name = 'app1'

urlpatterns = [
    path('', views.BenchmarkAPIView.as_view(), name='benchmark'),
]
