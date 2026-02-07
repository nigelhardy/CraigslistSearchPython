"""
Plugin manager for ranking algorithms.

This module handles registration and initialization of all ranking algorithms.
"""

from ranking_system import RankingAlgorithmRegistry
from ranking_algorithms import (SantaCruzApartmentRanking, LosGatosApartmentRanking, 
                             BMWE39PartsRanking, SubaruForesterBrakesRanking, 
                             SubaruForesterSuspensionRanking, SubaruPerformanceRanking,
                             SubaruForesterRanking)


def initialize_ranking_algorithms():
    """Initialize and register all available ranking algorithms."""
    # Register apartment ranking algorithms
    RankingAlgorithmRegistry.register(SantaCruzApartmentRanking())
    RankingAlgorithmRegistry.register(LosGatosApartmentRanking())
    
    # Register BMW E39 parts ranking algorithm
    RankingAlgorithmRegistry.register(BMWE39PartsRanking())
    
    # Register Subaru Forester parts ranking algorithms
    RankingAlgorithmRegistry.register(SubaruForesterBrakesRanking())
    RankingAlgorithmRegistry.register(SubaruForesterSuspensionRanking())
    
    # Register Subaru performance parts ranking algorithm
    RankingAlgorithmRegistry.register(SubaruPerformanceRanking())
    
    # Register Subaru Forester car ranking algorithm
    RankingAlgorithmRegistry.register(SubaruForesterRanking())


def get_available_algorithms():
    """Get a list of available algorithms for display."""
    return RankingAlgorithmRegistry.list_algorithms()