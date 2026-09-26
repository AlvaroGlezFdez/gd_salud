"""Pipeline de modelo predictivo de churn — versión ejecutable.

Se ejecuta una vez para generar los artefactos:
  - 05_clustering/feature_importance.png
  - 05_clustering/modelo_churn.pkl
  - 05_clustering/clientes_segmentados.csv  (con la nueva columna churn_proba)

El notebook 05_clustering/modelo_churn.ipynb contiene la misma lógica
organizada en celdas con explicaciones para inspección manual.
"""
import os
import sys
import sqlite3
import warnings

# Forzamos UTF-8 en stdout — Windows por defecto usa cp1252 y rompe con
# caracteres Unicode (emojis, box-drawing, etc.) que aparecen en prints.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

warnings.filterwarnings('ignore', category=UserWarning)

RANDOM_STATE = 42
DWH_PATH = '02_dwh/saleshealth_dwh.db'
PG_URL   = 'postgresql+psycopg2://postgres:alvaro@localhost:5432/saleshealth'
OUT_DIR  = '05_clustering'

FEATURE_COLS = [
    'cltv_parcial', 'frecuencia', 'recencia',
    'return_rate', 'avg_ticket', 'margen_ratio',
]


def main():
    # ── 1. Cargar fact_sales + dim_date desde el DWH ───────────────────────
    print('[1/8] Cargando fact_sales del DWH…')
    dwh = sqlite3.connect(DWH_PATH)
    sales = pd.read_sql("""
        SELECT f.customer_id, f.sale_id, f.sale_item_id,
               f.quantity, f.subtotal, f.margin, d.date AS sale_date
        FROM   fact_sales f
        JOIN   dim_date  d ON f.date_id = d.date_id
    """, dwh)
    sales['sale_date'] = pd.to_datetime(sales['sale_date'])
    print(f'      {len(sales):,} líneas de venta cargadas')

    # ── 2. Fecha de corte = percentil 67 del rango temporal ────────────────
    cutoff = sales['sale_date'].quantile(0.67)
    print(f'[2/8] Fecha de corte (P67): {cutoff.date()}')
    obs  = sales[sales['sale_date'] <  cutoff]
    eva  = sales[sales['sale_date'] >= cutoff]
    print(f'      Observación: {len(obs):,} líneas  ·  Evaluación: {len(eva):,} líneas')

    # ── 3. Features en periodo de observación ──────────────────────────────
    print('[3/8] Construyendo features de observación…')
    feats = obs.groupby('customer_id').agg(
        ingresos        = ('subtotal',     'sum'),
        margen_total    = ('margin',       'sum'),
        frecuencia      = ('sale_id',       pd.Series.nunique),
        items_comprados = ('sale_item_id', 'count'),
        primera_compra  = ('sale_date',    'min'),
        ultima_compra   = ('sale_date',    'max'),
    ).reset_index()

    feats['anios_relacion'] = (
        (feats['ultima_compra'] - feats['primera_compra']).dt.days / 365.25 + 1
    ).clip(lower=1.0)
    feats['margen_ratio'] = np.where(
        feats['ingresos'] > 0, feats['margen_total'] / feats['ingresos'], 0.0,
    )
    feats['cltv_parcial'] = (
        feats['ingresos'] * feats['margen_ratio']
        * feats['frecuencia'] * feats['anios_relacion']
    )
    feats['recencia']   = (cutoff - feats['ultima_compra']).dt.days
    feats['avg_ticket'] = feats['ingresos'] / feats['frecuencia']
    print(f'      {len(feats):,} clientes con actividad en observación')

    # ── 4. Devoluciones observables al cierre del periodo (PG) ─────────────
    print('[4/8] Cruzando devoluciones (return_date < cutoff)…')
    pg = create_engine(PG_URL)
    returns = pd.read_sql(f"""
        SELECT s.customer_id, COUNT(*) AS items_devueltos
        FROM   return_item ri
        JOIN   sale_item   si ON ri.sale_item_id = si.sale_item_id
        JOIN   sale        s  ON si.sale_id      = s.sale_id
        WHERE  ri.return_date < TIMESTAMP '{cutoff}'
        GROUP  BY s.customer_id
    """, pg)
    pg.dispose()

    feats = feats.merge(returns, on='customer_id', how='left')
    feats['items_devueltos'] = feats['items_devueltos'].fillna(0).astype(int)
    feats['return_rate']     = np.where(
        feats['items_comprados'] > 0,
        feats['items_devueltos'] / feats['items_comprados'], 0.0,
    )

    # ── 5. Etiqueta: churn = 1 si NO compró en evaluación ──────────────────
    print('[5/8] Calculando etiqueta de churn…')
    eval_customers = set(eva['customer_id'].unique())
    feats['churn'] = (~feats['customer_id'].isin(eval_customers)).astype(int)
    rate = feats['churn'].mean() * 100
    print(f'      Tasa de churn: {rate:.2f}%  '
          f'({feats["churn"].sum():,}/{len(feats):,})')

    # ── 6. Train/Test split + entrenamiento de los dos modelos ─────────────
    print('[6/8] Entrenando RandomForest y XGBoost…')
    X = feats[FEATURE_COLS].copy()
    y = feats['churn']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y,
    )

    rf = RandomForestClassifier(
        n_estimators=200, max_depth=6,
        random_state=RANDOM_STATE, n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    xgb = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        random_state=RANDOM_STATE, eval_metric='logloss',
        n_jobs=-1, tree_method='hist',
    )
    xgb.fit(X_train, y_train)

    def evaluar(name, model):
        proba = model.predict_proba(X_test)[:, 1]
        pred  = model.predict(X_test)
        auc   = roc_auc_score(y_test, proba)
        cm    = confusion_matrix(y_test, pred)
        rep   = classification_report(y_test, pred, digits=3, zero_division=0)
        print(f'\n  ── {name} ──────────────────────────────')
        print(f'  AUC-ROC  : {auc:.4f}')
        print(f'  Confusion matrix:\n{cm}')
        print(rep)
        return auc

    rf_auc  = evaluar('RandomForest', rf)
    xgb_auc = evaluar('XGBoost',     xgb)

    # ── 7. Mejor modelo + importancias + persistencia ──────────────────────
    if xgb_auc >= rf_auc:
        best_name, best_model = 'XGBoost', xgb
    else:
        best_name, best_model = 'RandomForest', rf
    print(f'\n[7/8] Mejor modelo: {best_name} (AUC={max(rf_auc, xgb_auc):.4f})')

    imp = (
        pd.Series(best_model.feature_importances_, index=FEATURE_COLS)
          .sort_values(ascending=True)
    )
    sns.set_theme(style='whitegrid', context='notebook')
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(imp.index, imp.values,
                   color='#1f4e79', edgecolor='white')
    for b, v in zip(bars, imp.values):
        ax.text(v, b.get_y() + b.get_height() / 2, f' {v:.3f}',
                va='center', fontsize=9)
    ax.set_xlabel('Importancia (Gini / gain)')
    ax.set_title(f'Feature importance — {best_name}',
                 fontsize=12, fontweight='bold', pad=10)
    ax.set_xlim(0, imp.max() * 1.18)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'feature_importance.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f'      Guardado: {OUT_DIR}/feature_importance.png')

    # Persistencia del modelo
    pkl_path = os.path.join(OUT_DIR, 'modelo_churn.pkl')
    joblib.dump({
        'model':         best_model,
        'model_name':    best_name,
        'feature_cols':  FEATURE_COLS,
        'cutoff_date':   cutoff.isoformat(),
        'auc_test':      float(max(rf_auc, xgb_auc)),
    }, pkl_path)
    print(f'      Guardado: {pkl_path}')

    # ── 8. Aplicar a TODOS los clientes y actualizar segmentados.csv ───────
    print('[8/8] Aplicando modelo a todos los clientes…')
    feats['churn_proba'] = best_model.predict_proba(X)[:, 1]

    seg_path = os.path.join(OUT_DIR, 'clientes_segmentados.csv')
    seg = pd.read_csv(seg_path)
    seg = seg.drop(columns=['churn_proba'], errors='ignore')
    seg = seg.merge(
        feats[['customer_id', 'churn_proba']],
        on='customer_id', how='left',
    )
    n_with = seg['churn_proba'].notna().sum()
    n_total = len(seg)
    print(f'      Clientes con churn_proba: {n_with:,}/{n_total:,}  '
          f'(NaN = nuevos sin observación previa)')

    # Redondeo a 4 decimales para legibilidad del CSV
    seg['churn_proba'] = seg['churn_proba'].round(4)
    seg.to_csv(seg_path, index=False, encoding='utf-8')
    print(f'      Guardado: {seg_path}')

    dwh.close()
    print('\n[OK] Pipeline completado.')

    # Para el reporte en la respuesta
    return {
        'cutoff':        cutoff,
        'rf_auc':        rf_auc,
        'xgb_auc':       xgb_auc,
        'best_name':     best_name,
        'churn_rate':    rate,
        'n_obs_clients': len(feats),
        'importances':   imp,
        'n_with_proba':  int(n_with),
    }


if __name__ == '__main__':
    main()
