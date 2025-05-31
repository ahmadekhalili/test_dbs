import time
import logging
from functools import wraps

from .connections import es_client

logger = logging.getLogger(__name__)


def ensure_es_index(index_name, mapping=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if not es_client.indices.exists(index=index_name):
                    es_client.indices.create(index=index_name, body=mapping or {})
                    logger.info(f"[Elasticsearch] Index '{index_name}' created.")
            except Exception as e:
                logger.error(f"[Elasticsearch] Index check/create failed: {e}")
            return func(*args, **kwargs)
        return wrapper
    return decorator