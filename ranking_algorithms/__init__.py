"""
Ranking algorithms package.

This package contains all the ranking algorithms for different types of searches.
"""

from .apartment_ranking import SantaCruzApartmentRanking, LosGatosApartmentRanking
from .bmw_e39_parts import BMWE39PartsRanking

__all__ = ['SantaCruzApartmentRanking', 'LosGatosApartmentRanking', 'BMWE39PartsRanking']