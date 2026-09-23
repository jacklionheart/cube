"""Compatibility imports for the cube-independent itemset miner."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from roto.mining import Dataset, swap_clusters
