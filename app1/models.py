from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField


class Product(models.Model):
    """
    PostgreSQL model optimized for full-text search benchmarking
    Maintains exact same structure as MongoDB and Elasticsearch for fair comparison
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

    @classmethod
    def setup_fulltext_search(cls):
        """
        Setup PostgreSQL extensions and indexes for optimal full-text search
        Call this method after running migrations to ensure extensions are available
        """
        from django.db import connection

        with connection.cursor() as cursor:
            try:
                # Enable required PostgreSQL extensions
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
                print("✅ PostgreSQL extensions enabled (pg_trgm, unaccent)")

                # Create GIN indexes for full-text search (moved from Meta.indexes)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_fulltext_gin_idx 
                    ON products 
                    USING GIN (name gin_trgm_ops);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_description_gin_idx 
                    ON products 
                    USING GIN (description gin_trgm_ops);
                """)
                print("✅ GIN trigram indexes created")

                # Create advanced full-text search index
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_advanced_fulltext_idx 
                    ON products 
                    USING GIN (to_tsvector('english', 
                        COALESCE(name, '') || ' ' || 
                        COALESCE(description, '') || ' ' || 
                        COALESCE(category, '')
                    ));
                """)
                print("✅ Advanced full-text search index created")

                # Create trigram similarity indexes for fuzzy search
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_name_similarity_idx 
                    ON products 
                    USING GIN (name gin_trgm_ops);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS products_desc_similarity_idx 
                    ON products 
                    USING GIN (description gin_trgm_ops);
                """)
                print("✅ Trigram similarity indexes created")

                return True

            except Exception as e:
                print(f"❌ Error setting up full-text search: {e}")
                return False

    @classmethod
    def search_simple(cls, query, limit=20):
        """
        Simple full-text search method for testing
        Uses ILIKE for basic case-insensitive search
        """
        return cls.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(category__icontains=query)
        )[:limit]

    @classmethod
    def search_advanced(cls, query, limit=20):
        """
        Advanced full-text search using PostgreSQL's built-in features
        Uses SearchVector and SearchQuery for relevance ranking
        """
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

        # Create search vector combining multiple fields
        search_vector = SearchVector('name', weight='A') + \
                        SearchVector('description', weight='B') + \
                        SearchVector('category', weight='C')

        # Create search query
        search_query = SearchQuery(query)

        return cls.objects.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(
            search=search_query
        ).order_by('-rank')[:limit]

    @classmethod
    def search_fuzzy(cls, query, similarity_threshold=0.3, limit=20):
        """
        Fuzzy search using PostgreSQL's trigram similarity
        Requires pg_trgm extension
        """
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT *, 
                       GREATEST(
                           similarity(name, %s),
                           similarity(description, %s),
                           similarity(category, %s)
                       ) as sim_score
                FROM products 
                WHERE similarity(name, %s) > %s 
                   OR similarity(description, %s) > %s
                   OR similarity(category, %s) > %s
                ORDER BY sim_score DESC
                LIMIT %s;
            """, [query] * 8 + [similarity_threshold] * 3 + [limit])

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ==================== MIGRATION HELPER ====================

"""
To create the migration with these indexes, run:

python manage.py makemigrations
python manage.py migrate

Then in Django shell or management command:
python manage.py shell
>>> from your_app.models import Product
>>> Product.setup_fulltext_search()

Or create a management command:
"""