# Final submission steps (Formula 1 - Milestone 1)

Deadline: **18 October 2026, 11:59 PM**. Submission: https://forms.gle/esDxHsvfzffYHVAZ9

1. On Kaggle, use **notebooks/f1_podium_prediction_final.ipynb** (single integrated notebook).
2. Create a private/public Kaggle Dataset holding **all 14 files in data/raw/** from THIS ZIP, attach it to the notebook (Add Input). Do not rely on a public 2020-only version of the dataset; this project uses data through 2024.
3. In Kaggle notebook Settings, enable **Internet** if the notebook needs to install `lime` (and possibly `shap`). Click **Run All**. Check for errors in every section including LIME and inference.
4. **Save Version** with outputs, configure permissions so evaluators can read the notebook, and copy its URL.
5. Upload this project to a GitHub repo; ensure README includes Kaggle URL and actual team names/IDs. Check that the GitHub URL is accessible.
6. Submit Kaggle notebook URL, GitHub repo URL and `reports/F1_Podium_Prediction_Report.pdf` through the official form.

## Validation already performed
- Full cleaned-data, feature engineering, modeling, ablation, SHAP, inference and export were successfully rerun locally.
- Two LIME-specific execution cells (159, 162) could not be tested locally because the `lime` distribution was unavailable. Original group-generated LIME figures and tables remain in reports/. Kaggle Run All must verify those two cells.
- The NN always uses scikit-learn MLP (not a different backend depending on what is installed). The final selected random forest is stable on the retest.
- The PDF is produced from exported CSVs and figures by running `python make_report.py .` **from the project root**, separate from notebook Run All.
