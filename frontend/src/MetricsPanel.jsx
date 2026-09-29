import { useState, useEffect } from 'react';
import { fetchMetrics } from './api';

export default function MetricsPanel() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(() => setMetrics(null));
  }, []);

  if (!metrics) {
    return (
      <div style={{ padding: '2rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        <div className="spin" style={{ margin: '0 auto 12px' }} />
        Loading verification metrics...
      </div>
    );
  }

  const modelOrder = ['XGBoost', 'LogisticRegression', 'ClimatologicalBaseline'];
  const displayNames = {
    XGBoost: 'XGBoost (Calibrated Multi-Physics)',
    LogisticRegression: 'Logistic Regression (Linear Benchmark)',
    ClimatologicalBaseline: 'Climatological Baseline (Uncalibrated)',
  };

  const xgb = metrics['XGBoost'] || {};

  return (
    <div className="fade-in">
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>
            Model Verification & Performance
          </h2>
          <span className="badge badge-green">Validated</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.5 }}>
          Evaluated strictly on chronologically held-out test data (final 15% temporal split).
          Labelled using 85th percentile extreme forecast-error thresholds stratified across lead days & seasons.
        </p>
      </div>

      {/* KPI Top Summary Cards */}
      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">XGBoost ROC-AUC</div>
          <div className="metric-num metric-highlight">{xgb.roc_auc ?? '—'}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            vs {metrics['LogisticRegression']?.roc_auc ?? '—'} (LogReg)
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Precision-Recall AUC</div>
          <div className="metric-num metric-highlight">{xgb.pr_auc ?? '—'}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Imbalanced extreme event skill
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Brier Score (Lower = Better)</div>
          <div className="metric-num" style={{ color: 'var(--text-accent)' }}>{xgb.brier ?? '—'}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Post-isotonic calibration
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Optimal F1 Score</div>
          <div className="metric-num" style={{ color: 'var(--amber)' }}>{xgb.f1 ?? '—'}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            At calibrated operating threshold
          </div>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="card" style={{ overflow: 'hidden', marginBottom: '20px' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg-raised)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
            Benchmark Comparison
          </span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Model Architecture</th>
              <th style={{ textAlign: 'center' }}>ROC-AUC</th>
              <th style={{ textAlign: 'center' }}>PR-AUC</th>
              <th style={{ textAlign: 'center' }}>Brier Score</th>
              <th style={{ textAlign: 'center' }}>F1 Score</th>
            </tr>
          </thead>
          <tbody>
            {modelOrder.filter((n) => metrics[n]).map((name) => {
              const m = metrics[name];
              const isPrimary = name === 'XGBoost';
              return (
                <tr key={name} className={isPrimary ? 'highlight-row' : ''}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: isPrimary ? 600 : 400, color: isPrimary ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {displayNames[name] || name}
                      </span>
                      {isPrimary && <span className="badge badge-green" style={{ fontSize: '9px', padding: '1px 6px' }}>Primary</span>}
                    </div>
                  </td>
                  <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: isPrimary ? 'var(--green)' : 'var(--text-secondary)', fontWeight: isPrimary ? 700 : 400 }}>
                    {m.roc_auc}
                  </td>
                  <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: isPrimary ? 'var(--green)' : 'var(--text-secondary)', fontWeight: isPrimary ? 700 : 400 }}>
                    {m.pr_auc}
                  </td>
                  <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                    {m.brier}
                  </td>
                  <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: isPrimary ? 'var(--amber)' : 'var(--text-muted)' }}>
                    {m.f1}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ padding: '12px 16px', background: 'var(--bg-raised)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
        <strong style={{ color: 'var(--text-secondary)' }}>Methodology Note:</strong> Split is strictly chronological: 70% train / 15% validation / 15% test. Zero temporal or spatial data leakage. The primary XGBoost model combines atmospheric dynamical proxies (divergence, shear, ensemble spread) with isotonic regression probability calibration to guarantee sharp, reliable uncertainty bands.
      </div>
    </div>
  );
}
