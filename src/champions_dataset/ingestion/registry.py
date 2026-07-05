from __future__ import annotations

from champions_dataset.shared.models import PipelineConfig

from .sources.munchstats import build_munchstats_adapter
from .sources.opgg import build_opgg_adapter
from .sources.pokeapi import build_pokeapi_adapter


def build_adapters(config: PipelineConfig, source_names: list[str]) -> list:
    factories = {
        "pokeapi": build_pokeapi_adapter,
        "opgg": build_opgg_adapter,
        "munchstats": build_munchstats_adapter,
    }
    adapters = []
    for name in source_names:
        if name not in factories:
            raise ValueError(f"Unsupported source: {name}")
        adapters.append(factories[name](config.sources[name]))
    return adapters
