"""
Ranking algorithms package.

This package contains all the ranking algorithms for different types of searches.
"""

from .apartment_ranking import SantaCruzApartmentRanking, LosGatosApartmentRanking
from .bmw_e39_parts import BMWE39PartsRanking
from .subaru_forester_parts import SubaruForesterBrakesRanking, SubaruForesterSuspensionRanking
from .subaru_performance_parts import SubaruPerformanceRanking
from .subaru_forester_cars import SubaruForesterRanking

__all__ = ['SantaCruzApartmentRanking', 'LosGatosApartmentRanking', 'BMWE39PartsRanking', 
           'SubaruForesterBrakesRanking', 'SubaruForesterSuspensionRanking', 'SubaruPerformanceRanking', 'SubaruForesterRanking']