# Master's Thesis: Phytoplankton Density Prediction Using Machine Learning

Welcome to the official repository for my Master's Thesis (2025). This project focuses on predicting the density and growth rates of 58 species of phytoplankton in Greifensee using high-frequency data and various Machine Learning models (Random Forest, XGBoost, and a custom Hybrid XGBoost-Regressor architecture).

## 🚀 Project Overview
The research focuses on answering critical ecological questions using advanced predictive modeling:
- **Predictability vs. Density:** Is there a trade-off between the mean density of a species and our ability to predict its growth?
- **Feature Importance:** What are the most crucial drivers of species growth? (Comparing Environmental variables, Temporal factors, and Engineered Features like lags and rolling windows).
- **Model Comparison:** How do traditional regressors compare to advanced two-stage hybrid models?
- **Ablation Studies:** What happens to predictive performance when we remove autoregressive (lag) and rolling window features?

## 📁 Repository Structure

```text
├── 01_Data/
│   └── Greifensee_data_pomati_2019to2022_taxa (1).csv   # The main high-frequency dataset
├── 04_Visualizations/                                   # Key output graphs and heatmaps
├── All_Scripts/
│   └── Final_Script for Master Thesis.py                # Unified, final analysis pipeline
├── Master_Thesis_FInal (1).pdf                          # Full Thesis Document
├── requirements.txt                                     # Python dependencies
└── README.md                                            # This file
```

*(Note: Intermediate scripts and output data files have been organized out of this main branch for clarity).*

## 🛠️ Installation & Setup

To reproduce the results or run the script locally, ensure you have Python 3.8+ installed.

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Master-Thesis-2025.git
   cd Master-Thesis-2025
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage

The entire experimental pipeline—including data pre-processing, temporal train/test splitting, feature engineering, model training (RF, XGBoost, Hybrid), ablation studies, and figure generation—can be executed via the main script:

```bash
python "All_Scripts\Final_Script for Master Thesis.py"
```

The script will automatically detect the dataset, parse the 58 species, and output all final figures to the `04_Visualizations/` directory.

## 📊 Key Findings & Results

1. **Feature Engineering Power:** Engineered features (specifically `lag` and `rolling_mean`) accounted for the vast majority of predictive power. 
2. **Environmental Limitations:** Relying purely on environmental factors (ablation study) severely limited predictive `R²` models across almost all species.
3. **Model Performance:** Random Forest Regression provided highly competitive baseline metrics, while specific species benefited from the Hybrid classification-regression approach.

 *(Refer to `Master_Thesis_FInal (1).pdf` for the full methodology and results).*

## ✍️ Author
**Debapratim Mukherjee**  
*Master's Thesis 2025*
