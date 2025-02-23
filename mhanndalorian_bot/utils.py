"""
Utility functions
"""

from __future__ import absolute_import, annotations

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def func_timer(f):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.debug(f"  [ {f.__name__}() ] took: {(te - ts):.6f} seconds")
        return result

    return wrap


def func_debug_logger(f):
    """Decorator for applying DEBUG logging to a function if enabled in the MBot class"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        logger.debug(f"  [ function {f.__name__}() ] called with args: {args} and kwargs: {kw}")
        result = f(*args, **kw)
        return result

    return wrap
