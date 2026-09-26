import { useState, useEffect } from 'react';
import { fetchMetrics } from './api';

export default function MetricsPanel() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(() => setMetrics(null));
  }, []);

  if (!metrics) return <div style={{ padding: '1rem', color: '#94a3b8' }}>Loading metrics...</div>;

  const modelOrder = ['XGBoost', 'LogisticRegression', 'ClimatologicalBaseline'];
  const displayNames = {
    XGBoost: 'XGBoost (Primary)',
    LogisticRegression: 'Logistic Regression',
    ClimatologicalBaseline: 'Climatological Baseline',
  };
  const rowStyle = (name) => ({
    background: name === 'XGBoost' ? '#f0fdf4' : '#f8fafc',
    fontWeight: name === 'XGBoost' ? 700 : 400,
  });

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <h2 style={{ margin: '0 0 0.5rem' }}>📊 Model Performance</h2>
      <p style={{ color: '#64748b', margin: '0 0 1rem', fontSize: '0.85rem' }}>
        Evaluation on chronologically held-out test set (final 15% of issue dates — dates the model never saw during training or calibration).
      </p>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <thead>
          <tr style={{ background: '#1e293b', color: '#fff' }}>
            {['Model', 'ROC-AUC', 'PR-AUC', 'Brier Score', 'F1'].map((h) => (
              <th key={h} style={{ padding: '0.5rem 0.75rem', textAlign: h === 'Model' ? 'left' : 'center' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {modelOrder.filter((n) => metrics[n]).map((name) => {
            const m = metrics[name];
            return (
              <tr key={name} style={rowStyle(name)}>
                <td style={{ padding: '0.5rem 0.75rem' }}>{displayNames[name] || name}</td>
                <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center', color: name === 'XGBoost' ? '#16a34a' : '#374151' }}>{m.roc_auc}</td>
                <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center', color: name === 'XGBoost' ? '#16a34a' : '#374151' }}>{m.pr_auc}</td>
                <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center' }}>{m.brier}</td>
                <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center' }}>{m.f1}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p style={{ marginTop: '0.75rem', fontSize: '0.78rem', color: '#6b7280' }}>
        * Temporal split: 70% train / 15% validation / 15% test (chronological). No data leakage. Bust label: 85th percentile stratified error threshold per lead day &times; season.
      </p>
    </div>
  );
}
