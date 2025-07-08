from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField


class Product(models.Model):  # db_table = 'products'
    """
    PostgreSQL model optimized for full-text search benchmarking
    Maintains exact same structure as MongoDB and Elasticsearch,.. for fair comparison
    """
    name = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    stock = models.IntegerField()
    description = models.TextField()
    rating = models.FloatField(db_index=True)

    # Optional: Pre-computed search vector for even faster full-text search
    # Uncomment if you want maximum PostgreSQL full-text search performance
    # search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        db_table = 'products'
        indexes = [
            # Basic indexes for standard queries
            models.Index(fields=['category']),
            models.Index(fields=['price']),
            models.Index(fields=['rating']),
            models.Index(fields=['category', 'price']),  # Compound index

            # NOTE: GIN indexes with gin_trgm_ops moved to setup_fulltext_search()
            # because they require pg_trgm extension to be enabled first
        ]

        # Database constraints for data integrity
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name='price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(stock__gte=0),
                name='stock_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(rating__gte=0) & models.Q(rating__lte=5),
                name='rating_range_valid'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"

    def to_dict(self):
        """Convert to dictionary for easy comparison with other databases"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': float(self.price),
            'stock': self.stock,
            'description': self.description,
            'rating': self.rating
        }


class Product2(models.Model):
    """
    """
    name = models.CharField(max_length=200, db_index=True, blank=True)
    name2 = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=200, blank=True)
    price = models.FloatField(blank=True, db_index=True)
    price2 = models.FloatField(blank=True)
    stock = models.IntegerField(blank=True)
    description = models.TextField(blank=True)
    rating = models.FloatField(blank=True)
