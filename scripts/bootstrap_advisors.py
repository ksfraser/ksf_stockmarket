#!/usr/bin/env python3
"""
Bootstrap advisor accounts in the stockmarket system.
Creates advisor users with 100,000 CAD starting capital on Jan 2 2025.
"""

import sys
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

sys.path.insert(0, '/home/ksf_stockmarket/ksf_stockmarket')

try:
    from src.Model.Database import Database
    from src.Model.User import User
    from src.Model.Portfolio import Portfolio
except ImportError as e:
    logger.error('Import error: %s', e)
    logger.error('Make sure you are running from the project root')
    sys.exit(1)


START_DATE = '2025-01-02'
STARTING_CAPITAL = 100000.0  # CAD


# Advisor definitions
