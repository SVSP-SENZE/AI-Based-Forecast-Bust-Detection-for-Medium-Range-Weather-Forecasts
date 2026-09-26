import { bandColor } from './utils';

export default function WhyPanel({ explanation, ragAnswer, onRagQuery, loading }) {
  if (!explanation) {
    return (
      <div style={{ padding: '1rem', color: '#94a3b8', fontStyle: 'italic' }}>
        Click a grid cell on the map to see drivers.
      </div>
    );
  }

  const { bust_probability, confidence_band, top_drivers, rule_summary } = explanation;

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <h3 style={{ margin: '0 0 0.5rem' }}>
        Why is confidence{' '}
        <span style={{ color: bandColor(confidence_band), fontWeight: 700 }}>
          {confidence_band}?
        </span>
      </h3>
      <p style={{ color: '#64748b', margin: '0 0 1rem' }}>
        Bust probability:{' '}
        <strong style={{ color: bandColor(confidence_band) }}>
          {(bust_probability * 100).toFixed(1)}%
        </strong>
      </p>

      {/* Rule-based reasons */}
      <h4 style={{ margin: '0 0 0.4rem', fontSize: '0.9rem', color: '#374151' }}>
        Key Signals
      </h4>
      <ul style={{ margin: '0 0 1rem', paddingLeft: '1.2rem', color: '#374151' }}>
        {rule_summary.map((r, i) => (
          <li key={i} style={{ marginBottom: '0.3rem', fontSize: '0.85rem' }}>{r}</li>
        ))}
      </ul>

      {/* SHAP drivers */}
      {top_drivers && top_drivers.length > 0 && (
        <>
          <h4 style={{ margin: '0 0 0.4rem', fontSize: '0.9rem', color: '#374151' }}>
            Model Feature Drivers (SHAP)
          </h4>
          <div style={{ marginBottom: '1rem' }}>
            {top_drivers.map((d, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '0.35rem',
                  fontSize: '0.82rem',
                }}
              >
                <span
                  style={{
                    background: d.direction === 'up' ? '#fee2e2' : '#dcfce7',
                    color: d.direction === 'up' ? '#dc2626' : '#16a34a',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 600,
                    minWidth: '28px',
                    textAlign: 'center',
                  }}
                >
                  {d.direction === 'up' ? '↑' : '↓'}
                </span>
                <span style={{ flex: 1, color: '#374151' }}>
                  <strong>{d.feature}</strong>
                </span>
                <span style={{ color: '#6b7280' }}>val={d.value}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* RAG explanation */}
      {ragAnswer && (
        <div
          style={{
            background: '#f0f9ff',
            border: '1px solid #bae6fd',
            borderRadius: '6px',
            padding: '0.75rem',
            marginBottom: '1rem',
          }}
        >
          <h4 style={{ margin: '0 0 0.4rem', fontSize: '0.9rem', color: '#0369a1' }}>
            📖 Meteorological Context (RAG)
          </h4>
          <p style={{ margin: 0, fontSize: '0.84rem', color: '#1e3a5f', lineHeight: 1.5 }}>
            {ragAnswer.answer}
          </p>
          {ragAnswer.sources && ragAnswer.sources.length > 0 && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#0369a1' }}>
              Sources:{' '}
              {ragAnswer.sources.map((s, i) => (
                <span key={i} style={{ marginRight: '0.5rem' }}>
                  [{i + 1}] {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        onClick={onRagQuery}
        disabled={loading}
        style={{
          background: loading ? '#93c5fd' : '#2563eb',
          color: '#fff',
          border: 'none',
          borderRadius: '6px',
          padding: '0.5rem 1rem',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: '0.85rem',
        }}
      >
        {loading ? 'Asking AI...' : '💬 Explain with Meteorological Context'}
      </button>
    </div>
  );
}
