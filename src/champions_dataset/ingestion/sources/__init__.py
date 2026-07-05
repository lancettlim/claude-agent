from .munchstats import build_munchstats_adapter
from .opgg import build_opgg_adapter
from .pokeapi import build_pokeapi_adapter

__all__ = [
    "build_munchstats_adapter",
    "build_opgg_adapter",
    "build_pokeapi_adapter",
]
