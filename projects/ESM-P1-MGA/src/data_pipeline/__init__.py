"""src.data_pipeline — Data ingestion and preparation tasks 0A–0J."""

from src.data_pipeline import task_0a_pypsa_de
from src.data_pipeline import task_0b_entsoe
from src.data_pipeline import task_0c_era5
from src.data_pipeline import task_0d_era5_historical
from src.data_pipeline import task_0e_opsd
from src.data_pipeline import task_0f_cement_params
from src.data_pipeline import task_0g_destatis_wz08
from src.data_pipeline import task_0h_destatis_genesis
from src.data_pipeline import task_0i_eurostat
from src.data_pipeline import task_0j_validation

__all__ = [
    "task_0a_pypsa_de",
    "task_0b_entsoe",
    "task_0c_era5",
    "task_0d_era5_historical",
    "task_0e_opsd",
    "task_0f_cement_params",
    "task_0g_destatis_wz08",
    "task_0h_destatis_genesis",
    "task_0i_eurostat",
    "task_0j_validation",
]
