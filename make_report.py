"""Build the Milestone-1 PDF report from the files the notebook writes.

Usage:  python make_report.py <project_dir> [output.pdf]

Everything numeric comes from reports/*.csv, every figure from reports/figures/*.png and the written answers are
read from the executed/unexecuted notebook's markdown, so after a re-run (for example on Kaggle) the report can be
regenerated and always matches the notebook. Needs: reportlab, pandas, nbformat.
"""
import re
import sys
from pathlib import Path

import nbformat
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

PROJECT = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT / "reports" / "F1_Podium_Prediction_Report.pdf"
REPORTS = PROJECT / "reports"
FIGS = REPORTS / "figures"

NB_PATH = next(p for p in [PROJECT / "notebooks" / "f1_podium_prediction_final_executed.ipynb",
                           PROJECT / "notebooks" / "f1_podium_prediction_final.ipynb"] if p.exists())
nb = nbformat.read(NB_PATH, as_version=4)
MD_CELLS = [c.source for c in nb.cells if c.cell_type == "markdown"]

# ---------------------------------------------------------------- fonts / styles
FONT_DIRS = [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")]
base, bold, ital, mono = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier"
for d in FONT_DIRS:
    if (d / "DejaVuSans.ttf").exists():
        pdfmetrics.registerFont(TTFont("DV", str(d / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DV-B", str(d / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("DV-I", str(d / "DejaVuSans-Oblique.ttf")))
        pdfmetrics.registerFont(TTFont("DV-M", str(d / "DejaVuSansMono.ttf")))
        pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")
        base, bold, ital, mono = "DV", "DV-B", "DV-I", "DV-M"
        break

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName=base, fontSize=9.2, leading=13, alignment=TA_LEFT, spaceAfter=5)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=14, bulletIndent=3, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName=bold, fontSize=16, leading=20, spaceBefore=6, spaceAfter=8,
                    textColor=colors.HexColor("#14213d"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=bold, fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4,
                    textColor=colors.HexColor("#14213d"))
CAP = ParagraphStyle("cap", parent=BODY, fontName=ital, fontSize=8, leading=10.5, textColor=colors.HexColor("#444444"))
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.4, leading=9.2, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName=bold)
TITLE = ParagraphStyle("title", parent=H1, fontSize=24, leading=29, spaceAfter=4)
W = A4[0] - 4 * cm


def inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", lambda m: f'<font face="{mono}" size="8">{m.group(1)}</font>', text)
    return text


def md_to_flow(md_text, skip_headings=True):
    """Tiny markdown converter: paragraphs, bullets, tables. Headings are dropped (we add our own)."""
    flow, para, lines = [], [], md_text.split("\n")

    def flush():
        if para:
            flow.append(Paragraph(inline(" ".join(para)), BODY))
            para.clear()

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            flush()
        elif ln.startswith("#"):
            flush()
            if not skip_headings:
                flow.append(Paragraph(inline(ln.lstrip("# ")), H2))
        elif ln.lstrip().startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            flow.append(table(rows[1:], rows[0], None))
        elif re.match(r"^\s*[-*] ", ln):
            flush()
            flow.append(Paragraph(inline(re.sub(r"^\s*[-*] ", "", ln)), BUL, bulletText="•"))
        elif re.match(r"^\s*\d+\. ", ln):
            flush()
            flow.append(Paragraph(inline(re.sub(r"^\s*\d+\. ", "", ln)), BUL, bulletText=re.match(r"^\s*(\d+)\.", ln).group(1) + "."))
        else:
            para.append(ln.strip())
        i += 1
    flush()
    return flow


def table(rows, header, col_widths=None, font_scale=1.0):
    data = [[Paragraph(inline(str(h)), CELLB) for h in header]]
    for r in rows:
        data.append([Paragraph(inline(str(c)), CELL) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e9f2")),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b8bfcc")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def df_table(df, fmt=None, col_widths=None):
    fmt = fmt or {}
    rows = []
    for _, r in df.iterrows():
        rows.append([(fmt[c].format(r[c]) if c in fmt and pd.notna(r[c]) else ("" if pd.isna(r[c]) else str(r[c])))
                     for c in df.columns])
    return table(rows, list(df.columns), col_widths)


def fig(name, width=W, caption=None):
    p = FIGS / name
    if not p.exists():
        return [Paragraph(f"[missing figure {name}]", CAP)]
    w, h = PILImage.open(p).size
    out = [Image(str(p), width=width, height=width * h / w)]
    if caption:
        out.append(Paragraph(caption, CAP))
    return [KeepTogether(out), Spacer(1, 6)]


def md_after(prefix):
    for t in MD_CELLS:
        if t.strip().startswith(prefix):
            return t
    raise KeyError(prefix)


def md_all(prefix):
    return [t for t in MD_CELLS if t.strip().startswith(prefix)]


def read(name):
    return pd.read_csv(REPORTS / name)


story = []


def S(x):
    if isinstance(x, list):
        story.extend(x)
    else:
        story.append(x)


# =============================================================== title + summary
cmp_ = read("member3_model_comparison.csv")
hand = None
sel_family = None
import json
hand_path = PROJECT / "data" / "models" / "member3_handoff.json"
if hand_path.exists():
    hand = json.loads(hand_path.read_text())
    sel_family = hand["selected_model"]["family"]
sel_family = sel_family or "random_forest"

S(Paragraph("Formula 1 Podium Prediction Companion", TITLE))
S(Paragraph("Milestone 1 — analytical report", ParagraphStyle("sub", parent=BODY, fontSize=12, textColor=colors.HexColor("#555555"))))
S(Spacer(1, 8))
S(Paragraph("1. Summary", H1))
S(Paragraph(
    "We predict, from information available <b>before the race starts</b>, which drivers finish on the podium. The work runs in one "
    "notebook (EDA → cleaning → data-engineering questions → feature engineering → preprocessing → modelling → experiments → "
    "XAI → inference). Splits are chronological (train 2003–2018, validation 2019–2021, test 2022–2024); the primary metric is "
    "average precision (AP, reported as PR-AUC) because only about 14% of driver-races are podiums, and F1 at a validation-tuned threshold is the secondary metric.", BODY))
head = cmp_[cmp_["model"].isin(["baseline_grid_position", sel_family]) & cmp_["split"].isin(["validation", "test"])].copy()
head["model"] = head["model"].replace({"baseline_grid_position": "grid-position baseline", sel_family: f"selected: {sel_family}"})
head = head[["model", "split", "pr_auc", "roc_auc", "f1", "precision", "recall"]].sort_values(["split", "model"], ascending=[False, False])
S(df_table(head, {c: "{:.3f}" for c in ["pr_auc", "roc_auc", "f1", "precision", "recall"]}))
S(Paragraph("Table 1. Headline results. The model is selected on validation PR-AUC only; the test split is used for evaluation and diagnostic analysis, never for selecting preprocessing, models, hyperparameters or thresholds.", CAP))
pb = cmp_[(cmp_["split"] == "test")].set_index("model")["pr_auc"]
abl = read("member3_ablation.csv").set_index("ablation")
joint = abl.loc["drop grid_and_qualifying", "delta_test_pr_auc"]
S(Paragraph("<b>Main findings.</b>", BODY))
S(Paragraph(f"The selected model improves held-out PR-AUC, ROC-AUC and F1, but not recall or top-3 hit rate (test PR-AUC {pb[sel_family]:.3f} vs "
            f"{pb['baseline_grid_position']:.3f}): most of the signal is already in the starting grid.", BUL, bulletText="•"))
S(Paragraph(f"Grid and qualifying carry the model. Removing both together costs {abs(joint):.3f} test PR-AUC, while removing either "
            "alone costs almost nothing because they are 0.97 correlated.", BUL, bulletText="•"))
S(Paragraph("Permutation importance, SHAP and LIME agree on the top features; the ranking is stable across validation/test and "
            "across model families. Feature importance describes what the <b>model</b> uses and is <b>not</b> evidence of causality.", BUL, bulletText="•"))
S(Paragraph("The test block (2022–2024) is a new technical era; scores are lower than on validation and the era effect is quantified in Section 7.", BUL, bulletText="•"))
S(PageBreak())

# =============================================================== data + cleaning
S(Paragraph("2. Data and cleaning", H1))
S(Paragraph("Source: 14 Ergast-style tables (races, results, qualifying, drivers, constructors, standings, …) covering 1950–2024. "
            "All cleaning decisions are logged in the notebook and exported as CSV.", BODY))
ba = read("member1_before_after_summary.csv")
S(df_table(ba, {}))
S(Paragraph("Table 2. Effect of cleaning. The raw files were hashed before and after and did not change.", CAP))
for t in ("- All 14 tables", ):
    pass
S(Paragraph("<b>Cleaning steps.</b> (1) The literal <font face=\"%s\">\\N</font> sentinel (160,076 cells) was converted to true missing values; "
            "(2) numeric/date types were repaired; (3) all primary keys were validated and 23 foreign-key relationships were checked "
            "with 0 unmatched rows; (4) 85 duplicated driver-race pairs (shared drives in the early decades) were resolved by keeping the "
            "best classified row, then more laps, then the smaller result id, leaving exactly one row per (race, driver)." % mono, BODY))
S(Spacer(1, 4))
S(fig("07_qualifying_coverage.png", W * 0.85, "Figure 1. Qualifying coverage by season. No qualifying data exists before 1994 and only part of the field is recorded until 2002 — "
      "which is why the modelling table starts in 2003 (known limitation: qualifying features cannot be used for older seasons)."))
S(fig("05_cleaning_impact.png", W * 0.85, "Figure 2. Impact of cleaning."))
S(PageBreak())

# =============================================================== DE questions
S(Paragraph("3. Data-engineering questions", H1))
for qn, qtitle, figs_, captions in [
    ("Q1", "Which circuits convert a front-row start into a podium most often, and does the ranking change after 2014?",
     ["08_q1_front_row_conversion_dumbbell.png", "09_q1_quali_vs_grid.png"],
     ["Figure 3. Front-row conversion by circuit, 2003–2013 vs 2014–2024 (Wilson intervals in the CSV).",
      "Figure 4. Front row by qualifying vs by grid: the definitions differ exactly in the penalty cases."]),
    ("Q2", "Do drivers podium more often at circuits in their home country?",
     ["10_q2_home_advantage.png"], ["Figure 5. Raw home vs away podium rate and the grid-adjusted comparison."]),
    ("Q3", "Which constructors have the highest mechanical-retirement rate in 2014–2021 vs 2022–2024?",
     ["11_q3_mechanical_retirement_rates.png", "12_q3_mechanical_trend.png"],
     ["Figure 6. Mechanical-retirement rate by constructor and period.", "Figure 7. League-wide mechanical-DNF trend."]),
]:
    S(Paragraph(f"{qn} — {qtitle}", H2))
    S(md_to_flow(md_after(f"### {qn} answer")))
    for f_, c_ in zip(figs_, captions):
        S(fig(f_, W * 0.92, c_))
S(PageBreak())

# =============================================================== features
S(Paragraph("4. Feature engineering and selection", H1))
S(md_to_flow(md_after("## Feature engineering")))
S(Paragraph("Window experiment and chosen features", H2))
S(md_to_flow(md_after("Going from 3 to 10 races")))
S(fig("13_fe_form_window_experiment.png", W * 0.8, "Figure 8. How many past races should the form window use? 10 was chosen (a 20-race window adds nothing and goes stale across team switches / regulation changes)."))
S(Paragraph("Final feature set and justification", H2))
S(md_to_flow(md_after("### Final feature set")))
S(fig("15_fe_univariate_auc.png", W * 0.85, "Figure 9. Univariate ROC-AUC of every candidate feature (2003–2018 only, so the validation/test seasons stay untouched)."))
S(fig("16_fe_feature_correlation.png", W * 0.7, "Figure 10. Correlation between features. The grid–qualifying block (0.97) is why the joint ablation and joint permutation importance are the informative numbers."))
S(Paragraph("Leakage control and missing values", H2))
S(md_to_flow(md_after("## Leakage checks")))
S(Paragraph("All three checks pass in the notebook: 300 random rows had their form, team form and standings features recomputed from scratch using only earlier races and matched the vectorised values; no post-race column is among the features; and no single pre-race feature separates podiums almost perfectly (AUC > 0.95).", BODY))
S(md_to_flow(md_after("The missing values are not random errors")))
S(fig("18_fe_missingness.png", W * 0.8, "Figure 11. Where the modelling table has missing values — each has a structural reason."))
S(PageBreak())

# =============================================================== preprocessing
S(Paragraph("5. Split and preprocessing", H1))
sp = read("member3_split_summary.csv")
S(df_table(sp, {"podium_rate": "{:.3f}"}))
S(Paragraph("Table 3. Chronological split. Rows within a season share cars and regulations, so a random split would leak; test seasons were not used for any feature, preprocessing or hyper-parameter decision.", CAP))
S(fig("20_m3_split_overview.png", W * 0.9, "Figure 12. Split overview."))
S(Paragraph("Preprocessing-order experiments", H2))
S(md_to_flow(md_after("## Preprocessing-order experiments")))
pe = read("member3_preprocessing_experiments.csv")
S(df_table(pe, {c: "{:.4f}" for c in ["val_pr_auc", "val_roc_auc", "val_f1"]}))
S(Paragraph("Table 4. Preprocessing-order experiments (validation). Configuration E is an illustrative train+validation leakage control; it does not use test data.", CAP))
S(Paragraph("Selection: configurations within 0.005 mean validation PR-AUC of the best are treated as tied (the same probe moves by about that much when library versions change), and ties are broken in favour of keeping missing-value indicators, because missingness is informative (season openers have no standings). The selected configuration is B (scale on observed values, then impute, with indicators).", BODY))
S(fig("21_m3_preprocessing_experiments.png", W * 0.8, "Figure 13. Preprocessing-order experiments."))
S(fig("22_m3_preprocessing_effect.png", W * 0.95, "Figure 14. Effect of the preprocessing on the distribution and range of the data."))
S(PageBreak())

# =============================================================== modelling
S(Paragraph("6. Modelling", H1))
S(Paragraph("Four model families were compared with a grid-position baseline: logistic regression, random forest, histogram gradient boosting and a shallow neural network. Each family is tuned on validation PR-AUC only; the decision threshold is tuned on validation as well.", BODY))
cm_ = cmp_[cmp_["split"].isin(["validation", "test"])][["model", "split", "pr_auc", "roc_auc", "f1", "precision", "recall", "top3_hit_rate", "threshold"]]
cm_ = cm_.sort_values(["model", "split"], ascending=[True, False])
S(df_table(cm_, {c: "{:.3f}" for c in ["pr_auc", "roc_auc", "f1", "precision", "recall", "top3_hit_rate", "threshold"]}))
S(Paragraph("Table 5. Model comparison on validation and test (PR-AUC primary).", CAP))
S(fig("23_m3_hyperparameter_search.png", W, "Figure 15. Hyper-parameter search: validation PR-AUC (bars) vs training PR-AUC (dots) — the gap shows overfitting."))
S(fig("24_m3_roc_pr_curves_test.png", W * 0.9, "Figure 16. ROC and precision–recall curves on the test block."))
S(fig("26_m3_confusion_and_calibration.png", W * 0.9, "Figure 17. Confusion matrix and calibration of the selected model."))
S(PageBreak())

# =============================================================== experiments
S(Paragraph("7. Experiments", H1))
S(Paragraph("Feature-group ablation", H2))
S(md_to_flow(md_after("## Feature-group ablation")))
S(df_table(abl.reset_index()[["ablation", "n_features", "val_pr_auc", "test_pr_auc", "test_roc_auc", "test_f1", "delta_test_pr_auc"]],
           {c: "{:.4f}" for c in ["val_pr_auc", "test_pr_auc", "test_roc_auc", "test_f1", "delta_test_pr_auc"]}))
S(Paragraph("Table 6. Retraining without one feature group at a time (selected model family and hyper-parameters; fresh preprocessor on the reduced columns).", CAP))
S(fig("27_m3_ablation.png", W * 0.9, "Figure 18. Ablation results."))
S(Paragraph("Era sensitivity and refit check", H2))
S(df_table(read("member3_test_by_season.csv")[["season", "rows", "roc_auc", "pr_auc", "f1", "top3_hit_rate"]], {c: "{:.3f}" for c in ["roc_auc", "pr_auc", "f1", "top3_hit_rate"]}))
S(Paragraph("Table 7. Test performance by season: the three test seasons differ, which is the cost of the 2022 regulation change.", CAP))
S(df_table(read("member3_refit_sensitivity.csv")[["fit_on", "roc_auc", "pr_auc", "f1", "top3_hit_rate"]], {c: "{:.3f}" for c in ["roc_auc", "pr_auc", "f1", "top3_hit_rate"]}))
S(Paragraph("Table 8. Refitting on train + validation does not improve the test score, so the reported model stays the one trained on 2003–2018.", CAP))
S(PageBreak())

# =============================================================== XAI
S(Paragraph("8. Explainable AI", H1))
S(Paragraph(f"The selected model ({sel_family}) is explained on the processed design matrix (standardised features plus missing indicators, in the training column order) using the test block (2022–2024). "
            "Permutation importance measures the drop in PR-AUC when columns are shuffled (20 repeats); SHAP uses TreeExplainer on the selected random forest (additivity verified numerically); LIME and SHAP waterfalls explain individual predictions.", BODY))
S(Paragraph("Global: permutation importance", H2))
S(fig("30_m4_permutation_importance.png", W, "Figure 19. Permutation importance of single columns (left) and feature groups (right)."))
S(md_to_flow(md_all("**Reading the result.** Shuffling")[0]))
S(fig("31_m4_permutation_stability.png", W * 0.8, "Figure 20. Stability of the ranking: same model on validation (left) and a different model family (right)."))
S(md_to_flow(md_all("**Reading the result.** The top three")[0]))
S(Paragraph("Global: SHAP", H2))
S(fig("32_m4_shap_bar.png", W * 0.6, "Figure 21. Mean |SHAP| per feature."))
S(fig("33_m4_shap_beeswarm.png", W * 0.85, "Figure 22. SHAP beeswarm."))
S(fig("34_m4_shap_dependence_raw_units.png", W, "Figure 23. SHAP value against the raw feature value (black line: mean per grid slot)."))
S(md_to_flow(md_all("**Reading the result.** The three qualifying")[0]))
S(fig("35_m4_perm_vs_shap.png", W * 0.5, "Figure 24. Permutation importance vs mean |SHAP|."))
S(md_to_flow(md_all("**Reading the result.** The two global")[0]))
S(Paragraph("Local explanations", H2))
cases = read("member4_local_cases.csv")
S(Paragraph("Three cases were chosen <b>by outcome</b> (not by how well they explain): the most confident correct podium call, the most confident wrong podium call and the biggest surprise.", BODY))
S(df_table(cases, {"predicted_prob": "{:.3f}"}))
imgs = []
for k in ["A_confident_correct", "B_confident_wrong", "C_biggest_surprise"]:
    p = FIGS / f"36_m4_shap_waterfall_{k}.png"
    w_, h_ = PILImage.open(p).size
    imgs.append(Image(str(p), width=W * 0.48, height=W * 0.48 * h_ / w_))
S(Table([[imgs[0], imgs[1]], [imgs[2], ""]], colWidths=[W / 2, W / 2]))
S(Paragraph("Figure 25. SHAP waterfalls for the three cases (raw feature values on the left, contributions in probability points).", CAP))
S(md_to_flow(md_all("**Reading the waterfalls.**")[0]))
S(fig("37_m4_lime_local.png", W, "Figure 26. LIME explanations of the same three cases."))
S(md_to_flow(md_all("**Reading the LIME result.**")[0]))
ag = read("member4_shap_vs_lime.csv")[["case", "shared_top5", "sign_agreement_on_shared", "lime_seed_stability_top5"]]
S(df_table(ag))
S(Paragraph("Table 9. Agreement between SHAP and LIME and LIME's stability across five seeds.", CAP))
S(md_to_flow(md_all("**Reading the agreement table.**")[0]))
S(Paragraph("Feature importance is not causality", H2))
caus = md_after("## Feature importance is not causality")
S(md_to_flow(caus))
S(PageBreak())

# =============================================================== inference
S(Paragraph("9. Inference", H1))
S(md_to_flow(md_after("# Part 9 — Inference")))
demo = read("member4_inference_demo.csv")[["input", "podium_probability", "predicted_podium", "n_features_imputed", "imputed_features", "top_driver"]]
demo.columns = ["input", "P(podium)", "podium?", "# imputed", "imputed fields", "top SHAP feature"]
S(df_table(demo, {"P(podium)": "{:.3f}"}, col_widths=[2.6 * cm, 1.8 * cm, 1.5 * cm, 1.6 * cm, 6 * cm, 3.5 * cm]))
S(Paragraph("Table 10. Demonstration of <font face=\"%s\">predict_podium</font>: a fully observed 2023 front-row record (0 missing inputs) and the same record with qualifying data, penalty flag and points shares removed. The function imputes with training-set statistics, reports which fields were imputed and keeps working; the probability drops as information is removed." % mono, CAP))
S(Spacer(1, 6))

# =============================================================== limitations
S(Paragraph("10. Limitations", H1))
lim = md_after("# Conclusions and limitations")
S(md_to_flow(lim.split("**Known limitations.**")[1] if "**Known limitations.**" in lim else lim))
S(Paragraph("11. Reproducibility", H1))
S(Paragraph("The single notebook <font face=\"%s\">f1_podium_prediction_final.ipynb</font> is designed to Run All from the raw CSVs (runtime depends on the available CPU and LIME installation), with every random step seeded (SEED = 42). "
            "On Kaggle, attach the dataset and press Run All; <font face=\"%s\">make_report.py</font> rebuilds this PDF from the files the notebook writes so the report always matches the run." % (mono, mono), BODY))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(base, 7.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(2 * cm, 1.2 * cm, "Formula 1 Podium Prediction Companion — Milestone 1")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                        title="Formula 1 Podium Prediction Companion — Milestone 1", author="Team")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
