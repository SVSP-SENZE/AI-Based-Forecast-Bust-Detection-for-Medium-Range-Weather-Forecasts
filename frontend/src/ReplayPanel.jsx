import { useState, useEffect } from 'react';
import { fetchReplay, postRagQuery } from './api';
import { bandMeta, formatProb } from './utils';

const REPLAY_CASES = [
  { date: '2003-07-01', title: 'Peak Monsoon Active Surge', region: 'Konkan & Western Ghats', highlight: 'Extreme Bust' },
  { date: '2002-08-15', title: 'All-India Monsoon Drought / Break', region: 'Central Maharashtra', highlight: 'High Confidence' },
  { date: '2001-06-01', title: 'Monsoon Onset Vortex Transition', region: 'Coastal Arabian Sea', highlight: 'Elevated Risk' },
];

export default function ReplayPanel() {
  const [selectedDate, setSelectedDate] = useState(REPLAY_CASES[0].date);
  const [replay, setReplay] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ragAnswer, setRagAnswer] = useState(null);
  const [ragLoading, setRagLoading] = useState(false);

  async function load(date) {
    setLoading(true);
    setReplay(null);
    setRagAnswer(null);
    try {
      const data = await fetchReplay(date);
      setReplay(data);
    } catch (e) {
      setReplay({ error: e.message });
    }
    setLoading(false);
  }

  useEffect(() => {
    load(selectedDate);
  }, [selectedDate]);

  async function handleRag() {
    if (!replay) return;
    setRagLoading(true);
    const q = `Why did the forecast issued on ${selectedDate} over Maharashtra exhibit high bust risk? The model flagged: ${replay.predictions ? replay.predictions.slice(0, 3).map(p => p.rule_summary?.[0]).filter(Boolean).join('; ') : 'convective uncertainty'}`;
    const ans = await postRagQuery(q);
    setRagAnswer(ans);
    setRagLoading(false);
  }

  return (
    <div className="fade-in">
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>
            Historical Forecast Bust Replay
          </h2>
          <span className="badge badge-blue">Deterministic Case Studies</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.5 }}>
          Inspect how the model performed on real historical monsoon events using strictly antecedent forecast data available on the issue date, verified against ground-truth IMD observations.
        </p>
      </div>

      {/* Case Selector Buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px', marginBottom: '20px' }}>
        {REPLAY_CASES.map((c) => {
          const isSelected = selectedDate === c.date;
          return (
            <button
              key={c.date}
              onClick={() => setSelectedDate(c.date)}
              style={{
                textAlign: 'left',
                padding: '12px 14px',
                background: isSelected ? 'var(--accent-dim)' : 'var(--bg-surface)',
                border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span className="mono" style={{ color: isSelected ? 'var(--text-accent)' : 'var(--text-primary)', fontWeight: 600 }}>
                  {c.date}
                </span>
                <span className={`badge ${c.highlight === 'Extreme Bust' ? 'badge-red' : c.highlight === 'High Confidence' ? 'badge-green' : 'badge-amber'}`} style={{ fontSize: '9px' }}>
                  {c.highlight}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>{c.title}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{c.region}</div>
            </button>
          );
        })}
      </div>

      {loading && (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <div className="spin" style={{ margin: '0 auto 12px' }} />
          Loading case replay...
        </div>
      )}

      {replay && !replay.error && replay.predictions && (
        <div className="card" style={{ padding: '18px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>
                Target Evaluation Run
              </span>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                Issue Date: {selectedDate} (Maharashtra Region Grid)
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleRag}
              disabled={ragLoading}
            >
              {ragLoading ? <><div className="spin" /> Querying Synoptic RAG...</> : <><span>📖</span> Meteorological RAG Context</>}
            </button>
          </div>

          {/* Lead Day Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', marginBottom: '16px' }}>
            {replay.predictions.map((p) => {
              const meta = bandMeta(p.bust_probability);
              return (
                <div
                  key={p.lead_day}
                  style={{
                    background: 'var(--bg-raised)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Day {p.lead_day}
                    </span>
                    <span className={`badge ${meta.cls}`} style={{ fontSize: '9px', padding: '1px 6px' }}>
                      {meta.label}
                    </span>
                  </div>

                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    Valid: {p.valid_date}
                  </div>

                  <div style={{ margin: '4px 0' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Bust Probability</div>
                    <div className="mono" style={{ fontSize: '18px', fontWeight: 700, color: meta.color }}>
                      {formatProb(p.bust_probability)}
                    </div>
                  </div>

                  <div className="prob-bar">
                    <div className="prob-bar-fill" style={{ width: `${p.bust_probability * 100}%`, background: meta.color }} />
                  </div>

                  {p.rule_summary && p.rule_summary[0] && (
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.3 }}>
                      {p.rule_summary[0]}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Ground truth reference box */}
          {replay.actual_rainfall !== null && replay.actual_rainfall !== undefined && (
            <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: 'var(--radius-sm)', padding: '12px', marginBottom: '14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--amber)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Ground Truth IMD Rainfall Verification
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-primary)' }}>
                {typeof replay.actual_rainfall === 'object' ? JSON.stringify(replay.actual_rainfall) : replay.actual_rainfall}
              </div>
            </div>
          )}

          {/* RAG Answer Display */}
          {ragAnswer && (
            <div className="rag-answer fade-in" style={{ marginTop: '12px' }}>
              <div className="rag-header">
                <span>📖</span>
                <span>Meteorological Physical Synthesis</span>
              </div>
              <p className="rag-text">{ragAnswer.answer}</p>
              {ragAnswer.sources && ragAnswer.sources.length > 0 && (
                <div className="rag-sources">
                  {ragAnswer.sources.map((s, i) => (
                    <span key={i} className="rag-source-tag">
                      [{i + 1}] {typeof s === 'object' ? (s.title || s.citation || `Doc ${i + 1}`) : s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {replay && replay.error && (
        <div className="error-banner" style={{ borderRadius: 'var(--radius-sm)' }}>
          <span>⚠</span> Replay failed: {replay.error}
        </div>
      )}
    </div>
  );
}
