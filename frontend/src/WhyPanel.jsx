import { bandMeta, formatProb } from './utils';

export default function WhyPanel({ explanation, ragAnswer, onRagQuery, loading }) {
  if (!explanation) return null;

  const { bust_probability, confidence_band, top_drivers, rule_summary, lead_day } = explanation;
  const meta = bandMeta(bust_probability ?? 0);

  return (
    <div className="why-panel fade-in">
      {/* Risk summary */}
      <div className="why-risk-header" style={{ borderLeft: `3px solid ${meta.color}` }}>
        <div className="why-risk-row">
          <div>
            <div className="why-risk-label">Bust Probability</div>
            <div className="why-risk-value" style={{ color: meta.color }}>
              {formatProb(bust_probability)}
            </div>
          </div>
          <span className={`badge ${meta.cls}`}>{meta.label}</span>
        </div>
        <div className="why-prob-bar prob-bar">
          <div
            className="prob-bar-fill"
            style={{
              width: `${bust_probability * 100}%`,
              background: `linear-gradient(90deg, ${meta.color}88, ${meta.color})`,
            }}
          />
        </div>
      </div>

      {/* Rule-based signals */}
      <div className="why-section">
        <div className="why-section-title">⚡ Key Risk Signals</div>
        <ul className="why-signals">
          {rule_summary?.map((r, i) => (
            <li key={i} className="signal-item">{r}</li>
          ))}
        </ul>
      </div>

      {/* SHAP drivers */}
      {top_drivers?.length > 0 && (
        <div className="why-section">
          <div className="why-section-title">📊 Feature Drivers (SHAP)</div>
          <div className="shap-list">
            {top_drivers.map((d, i) => {
              const isUp = d.direction === 'up';
              return (
                <div key={i} className="shap-row">
                  <span className={`shap-dir ${isUp ? 'shap-up' : 'shap-down'}`}>
                    {isUp ? '▲' : '▼'}
                  </span>
                  <span className="shap-feature">{d.feature}</span>
                  <span className="shap-value mono">{d.value}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* RAG answer */}
      {ragAnswer && (
        <div className="rag-answer fade-in">
          <div className="rag-header">
            <span>📖</span>
            <span>Meteorological Context</span>
          </div>
          <p className="rag-text">{ragAnswer.answer}</p>
          {ragAnswer.sources?.length > 0 && (
            <div className="rag-sources">
              {ragAnswer.sources.map((s, i) => {
                const label = typeof s === 'object'
                  ? (s.title || s.citation || s.section || `Doc ${i + 1}`)
                  : String(s);
                return (
                  <span key={i} className="rag-source-tag">[{i + 1}] {label}</span>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* RAG button */}
      <div className="why-footer">
        <button
          className="btn btn-primary"
          style={{ width: '100%', justifyContent: 'center' }}
          onClick={onRagQuery}
          disabled={loading}
        >
          {loading ? (
            <><div className="spin" /> Asking AI…</>
          ) : (
            <><span>💬</span> Explain with Meteorological Context</>
          )}
        </button>
      </div>
    </div>
  );
}
