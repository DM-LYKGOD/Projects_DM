"""
mock_data.py — Synthetic German Energy Network Builder
=====================================================
Builds a 37-bus PyPSA-DE-compatible network using German NUTS-2 regions.
Used as fallback when real data downloads fail.
"""

import pandas as pd
import pypsa
from pathlib import Path


def build_synthetic_germany_network() -> pypsa.Network:
    """
    Build a 37-bus synthetic German energy network for the year 2025.

    Topology:
        37 German NUTS-2 buses in a ring (last bus → first bus).
        Each bus has 4 generators (solar, onwind, OCGT, lignite) and 1 load.

    Returns:
        pypsa.Network: Fully built network with 37 buses, 148 generators,
                       37 loads, 8760 snapshots (hourly 2025), 37 lines.
    """
    NUTS2_IDS = [
        "DE11",
        "DE12",
        "DE13",
        "DE14",
        "DE21",
        "DE22",
        "DE23",
        "DE24",
        "DE25",
        "DE26",
        "DE27",
        "DE30",
        "DE40",
        "DE50",
        "DE60",
        "DE71",
        "DE72",
        "DE73",
        "DE91",
        "DE92",
        "DE93",
        "DE94",
        "DEA1",
        "DEA2",
        "DEA3",
        "DEA4",
        "DEA5",
        "DEB1",
        "DEB2",
        "DEB3",
        "DEC0",
        "DED2",
        "DED4",
        "DED5",
        "DEE0",
        "DEF0",
        "DEG0",
    ]
    assert len(NUTS2_IDS) == 37, f"Expected 37 NUTS-2 buses, got {len(NUTS2_IDS)}"

    snapshots = pd.date_range("2025-01-01", periods=8760, freq="h")

    n = pypsa.Network()
    n.set_snapshots(snapshots)

    for bus in NUTS2_IDS:
        n.add("Bus", bus, carrier="AC")

    for bus in NUTS2_IDS:
        n.add(
            "Generator",
            f"solar_{bus}",
            bus=bus,
            carrier="solar",
            p_nom=2000,
            marginal_cost=0,
            p_max_pu=0.2,
        )
        n.add(
            "Generator",
            f"onwind_{bus}",
            bus=bus,
            carrier="onwind",
            p_nom=1500,
            marginal_cost=0,
            p_max_pu=0.3,
        )
        n.add(
            "Generator",
            f"OCGT_{bus}",
            bus=bus,
            carrier="OCGT",
            p_nom=1000,
            marginal_cost=60,
        )
        n.add(
            "Generator",
            f"lignite_{bus}",
            bus=bus,
            carrier="lignite",
            p_nom=800,
            marginal_cost=45,
        )
        n.add("Load", f"load_{bus}", bus=bus, p_set=1500)

    n_lines = len(NUTS2_IDS)
    for i in range(n_lines):
        bus_from = NUTS2_IDS[i]
        bus_to = NUTS2_IDS[(i + 1) % n_lines]
        line_name = f"line_{bus_from}_{bus_to}"
        n.add("Line", line_name, bus0=bus_from, bus1=bus_to, x=0.01, r=0.01, s_nom=5000)

    return n
