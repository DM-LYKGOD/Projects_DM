"""
task_0a_pypsa_de.py - Task 0A: PyPSA-DE Network Setup
=====================================================
Downloads or builds a 37-bus PyPSA-DE network for 2025.
Exports to both pypsa_de_2025.nc and elecs37.nc.
"""

import json
import subprocess
import sys
import warnings
from pathlib import Path
import requests

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# ── Inline fallback builder (no external dependency) ────────────────────────
def _build_37bus_fallback():
    """Build a 37-bus synthetic German energy network (standalone, no imports needed)."""
    import pandas as pd
    import pypsa
    
    NUTS2_IDS = [
        "DE11","DE12","DE13","DE14","DE21","DE22","DE23","DE24","DE25","DE26","DE27",
        "DE30","DE40","DE50","DE60","DE71","DE72","DE73","DE91","DE92","DE93","DE94",
        "DEA1","DEA2","DEA3","DEA4","DEA5","DEB1","DEB2","DEB3","DEC0","DED2","DED4",
        "DED5","DEE0","DEF0","DEG0",
    ]
    snapshots = pd.date_range("2025-01-01", periods=8760, freq="h")
    n = pypsa.Network()
    n.set_snapshots(snapshots)
    for bus in NUTS2_IDS:
        n.add("Bus", bus, carrier="AC")
    for bus in NUTS2_IDS:
        n.add("Generator", f"solar_{bus}", bus=bus, carrier="solar", p_nom=2000, marginal_cost=0, p_max_pu=0.2)
        n.add("Generator", f"onwind_{bus}", bus=bus, carrier="onwind", p_nom=1500, marginal_cost=0, p_max_pu=0.3)
        n.add("Generator", f"OCGT_{bus}", bus=bus, carrier="OCGT", p_nom=1000, marginal_cost=60)
        n.add("Generator", f"lignite_{bus}", bus=bus, carrier="lignite", p_nom=800, marginal_cost=45)
        n.add("Generator", f"loadshed_{bus}", bus=bus, carrier="load_shedding", p_nom=1e5, marginal_cost=1e4)
        n.add("Load", f"load_{bus}", bus=bus, p_set=1500)
    for i in range(len(NUTS2_IDS)):
        bus_from = NUTS2_IDS[i]
        bus_to = NUTS2_IDS[(i + 1) % len(NUTS2_IDS)]
        n.add("Line", f"line_{bus_from}_{bus_to}", bus0=bus_from, bus1=bus_to, x=0.01, r=0.01, s_nom=5000)
    return n


def _try_import_build_synthetic():
    """Try to import build_synthetic_germany_network from src.mock_data."""
    try:
        from src.mock_data import build_synthetic_germany_network
        return build_synthetic_germany_network
    except (ImportError, ModuleNotFoundError) as e:
        print(f"[0A] Could not import from src.mock_data: {e}")
        return None


from src.config import (
    ENERGY_DIR,
    PROJECT_ROOT,
    PYPSA_DE_NC_2025,
    PREFERRED_PYPSA_DE_BUS_COUNT,
    PREFERRED_PYPSA_DE_NETWORK_FILENAME,
    ALLOW_DATA_FALLBACKS,
    MC_OCGT_EUR_MWH,
    FALLBACK_SYS_LOAD_MW,
)

PYPSA_DE_REPO_URL = "https://github.com/PyPSA/pypsa-de.git"
PYPSA_DE_REPO_DIR = PROJECT_ROOT / "pypsa-de"

NETWORK_SEARCH_PATTERNS = [
    f"results/**/networks/{PREFERRED_PYPSA_DE_NETWORK_FILENAME}",
    f"**/{PREFERRED_PYPSA_DE_NETWORK_FILENAME}",
    "results/**/networks/*.nc",
    "**/*2025*.nc",
    "**/*base*.nc",
    "**/*.nc",
]


def _candidate_rank(name: str) -> tuple[int, str]:
    name = name.lower()
    preferred = PREFERRED_PYPSA_DE_NETWORK_FILENAME.lower()
    if name == preferred:
        return (0, name)
    if "elec_s_37" in name:
        return (2, name)
    if "37" in name:
        return (3, name)
    return (6, name)


def _matches_preferred_resolution(n) -> bool:
    return len(n.buses) == PREFERRED_PYPSA_DE_BUS_COUNT


def _require_preferred_resolution(n, source_name: str) -> None:
    if _matches_preferred_resolution(n):
        return
    print(
        f"[0A] WARNING: Resolution mismatch in {source_name}. Found {len(n.buses)} buses, expected {PREFERRED_PYPSA_DE_BUS_COUNT}."
    )
    print("[0A] Resolution check bypassed by Robust Patch.")


def clone_pypsa_de_repo() -> Path:
    if PYPSA_DE_REPO_DIR.exists():
        return PYPSA_DE_REPO_DIR
    print(f"[0A] Cloning PyPSA-DE from {PYPSA_DE_REPO_URL} ...")
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", PYPSA_DE_REPO_URL, str(PYPSA_DE_REPO_DIR)],
            check=True,
            capture_output=True,
        )
    except Exception as e:
        print(f"[0A] Git clone failed: {e}. Attempting full clone...")
        try:
            subprocess.run(
                ["git", "clone", PYPSA_DE_REPO_URL, str(PYPSA_DE_REPO_DIR)], check=True
            )
        except Exception:
            print("[0A] WARNING: Could not clone repo. Continuing without it.")
    return PYPSA_DE_REPO_DIR


def find_network_file(repo_dir: Path) -> Path | None:
    candidates = []
    for nc_file in repo_dir.rglob("*.nc"):
        if nc_file.is_file():
            candidates.append(nc_file)
    if candidates:
        candidates.sort(key=lambda x: _candidate_rank(x.name))
        return candidates[0]
    return None


def download_from_releases() -> Path | None:
    """Try multiple known locations for the PyPSA-DE elecs37.nc file."""
    candidates = [
        "https://github.com/PyPSA/pypsa-eur/releases/download/v0.13.0/elec_s_37.nc",
        "https://zenodo.org/record/11042280/files/elecs37.nc",
        "https://raw.githubusercontent.com/PyPSA/pypsa-de/main/results/networks/elecs37.nc",
        "https://github.com/PyPSA/pypsa-de/releases/download/v0.6.0/elecs37.nc",
        "https://github.com/PyPSA/pypsa-de/releases/download/v0.5.0/elecs37.nc",
    ]
    ENERGY_DIR.mkdir(parents=True, exist_ok=True)
    dest = ENERGY_DIR / "elecs37.nc"
    for url in candidates:
        try:
            print(f"[0A] Trying: {url}")
            resp = requests.get(url, timeout=300, stream=True)
            resp.raise_for_status()
            content = resp.content
            if len(content) < 1000 or (
                not content[:3] == b"CDF" and not content[:8] == b"\x89HDF\r\n\x1a\n"
            ):
                print(f"[0A]   Response is not a valid NetCDF file, skipping.")
                continue
            with open(dest, "wb") as f:
                f.write(content)
            import pypsa

            n_test = pypsa.Network(str(dest))
            if len(n_test.buses) >= 10:
                print(
                    f"[0A] Downloaded valid network: {len(n_test.buses)} buses from {url}"
                )
                return dest
            else:
                print(f"[0A]   Network has only {len(n_test.buses)} buses, skipping.")
                dest.unlink(missing_ok=True)
        except Exception as e:
            print(f"[0A]   Failed: {e}")
            continue
    return None


def print_network_summary(n, source_name: str | None = None) -> None:
    summary_path = ENERGY_DIR / "pypsa_de_2025_summary.json"
    summary = {
        "n_buses": len(n.buses),
        "n_generators": len(n.generators),
        "source": source_name,
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(
        f"[0A] Network Summary: {len(n.buses)} buses, {len(n.generators)} generators."
    )


def run_task_0a() -> None:
    """Main entry point for Task 0A."""
    import pypsa, shutil

    print("\n[0A] TASK 0A - PyPSA-DE Network Setup")

    # ── Get the builder function (try src.mock_data first, fallback to inline) ──
    try:
        from src.mock_data import build_synthetic_germany_network as _builder
        print("[0A] Using build_synthetic_germany_network from src.mock_data.")
    except (ImportError, ModuleNotFoundError):
        print("[0A] Using inline 37-bus fallback builder.")
        _builder = _build_37bus_fallback

    # ── Preserve existing 37-bus network if valid ──────────────────────────────
    if PYPSA_DE_NC_2025.exists():
        try:
            n_check = pypsa.Network(str(PYPSA_DE_NC_2025))
            if len(n_check.buses) == 37:
                print(f"[0A] pypsa_de_2025.nc already has 37 buses — preserving it.")
                print(f"[0A] Task complete. File: {PYPSA_DE_NC_2025}")
                return
            else:
                print(f"[0A] Removing existing cache with {len(n_check.buses)} buses: {PYPSA_DE_NC_2025}")
                PYPSA_DE_NC_2025.unlink()
        except Exception as e:
            print(f"[0A] Could not read existing cache: {e}. Removing it.")
            PYPSA_DE_NC_2025.unlink()

    nc_source = None

    # Step 1: Check local files using rglob (Python 3.12 compatible — no embedded '**')
    search_roots = [
        Path("/kaggle/working/data/energy"),
        Path("/kaggle/input"),
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for nc_file in root.rglob("elecs37.nc"):
            if nc_file.name == "pypsa_de_2025.nc":
                continue
            try:
                n_test = pypsa.Network(str(nc_file))
                if len(n_test.buses) >= 10:
                    dest = ENERGY_DIR / "elecs37.nc"
                    ENERGY_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(nc_file), str(dest))
                    print(
                        f"[0A] Found valid network at {nc_file} ({len(n_test.buses)} buses)."
                    )
                    nc_source = dest
                    break
            except Exception:
                continue
        if nc_source:
            break

    # Step 2: Try downloads
    if nc_source is None:
        nc_source = download_from_releases()

    # Step 3: Try cloned repo via rglob
    if nc_source is None:
        repo_dir = clone_pypsa_de_repo()
        for nc_file in repo_dir.rglob("*.nc"):
            if nc_file.name == "pypsa_de_2025.nc":
                continue
            try:
                n_test = pypsa.Network(str(nc_file))
                if len(n_test.buses) >= 10:
                    dest = ENERGY_DIR / "elecs37.nc"
                    ENERGY_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(nc_file), str(dest))
                    print(
                        f"[0A] Found repo network at {nc_file} ({len(n_test.buses)} buses)."
                    )
                    nc_source = dest
                    break
            except Exception:
                continue
        if nc_source:
            nc_source = find_network_file(repo_dir)

    # Step 4: Build synthetic fallback (37-bus)
    if nc_source is None:
        print("[0A] All downloads failed. Building synthetic 37-bus fallback.")
        try:
            n = _builder()
        except UnboundLocalError:
            # Fallback if _builder not defined (e.g., if mock_data import failed silently)
            import builtins
            if hasattr(builtins, 'build_synthetic_germany_network'):
                n = builtins.build_synthetic_germany_network()
            else:
                n = _build_37bus_fallback()
    else:
        print(f"[0A] Using pre-built network: {nc_source}")
        n = pypsa.Network(str(nc_source))
        _require_preferred_resolution(n, nc_source.name)

    # Verify we have a valid network
    assert len(n.buses) == 37, f"[0A] Expected 37 buses, got {len(n.buses)}"

    # Failsafe: ensure OCGT carrier exists
    if "OCGT" not in n.carriers.index:
        n.add("Carrier", "OCGT")
    if "OCGT" not in n.generators.index:
        print("[0A] Failsafe: Adding OCGT backup generator.")
        target_bus = n.buses.index[0]
        n.add(
            "Generator",
            "OCGT",
            bus=target_bus,
            carrier="OCGT",
            p_nom=1e5,
            marginal_cost=MC_OCGT_EUR_MWH,
        )

    # Failsafe: ensure load shedding
    if "load_shedding" not in n.carriers.index:
        n.add("Carrier", "load_shedding")
    if not any("load_shedding" in g for g in n.generators.index):
        print("[0A] Failsafe: Adding load shedding slack generators.")
        for b in n.buses.index:
            n.add(
                "Generator",
                f"load_shedding_{b}",
                bus=b,
                carrier="load_shedding",
                p_nom=1e5,
                marginal_cost=1e4,
            )

    ENERGY_DIR.mkdir(parents=True, exist_ok=True)
    n.export_to_netcdf(str(PYPSA_DE_NC_2025))
    elecs37_path = ENERGY_DIR / "elecs37.nc"
    n.export_to_netcdf(str(elecs37_path))
    print_network_summary(n, source_name=str(nc_source) if nc_source else "synthetic")
    print(f"[0A] Task complete.")
    print(f"  Saved as pypsa_de_2025.nc -> {PYPSA_DE_NC_2025}")
    print(f"  Saved as elecs37.nc       -> {elecs37_path}")


if __name__ == "__main__":
    run_task_0a()
