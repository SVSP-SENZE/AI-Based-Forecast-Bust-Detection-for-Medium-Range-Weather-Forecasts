import { useState, useEffect } from 'react';
import { fetchReplay, postRagQuery } from './api';

const REPLAY_DATES = ['2003-07-01', '2002-08-15', '2001-06-01'];

export default function ReplayPanel() {
  const [selectedDate, setSelectedDate] = useState(REPLAY_DATES[0]);
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
    const q = `Why might a forecast issued on ${selectedDate} over Maharashtra bust? The model flagged these drivers: ${replay.predictions ? replay.predictions.slice(0,2).map(p => p.rule_summary?.[0]).join('; ') : 'unknown'}`;
    const ans = await postRagQuery(q);
    setRagAnswer(ans);
    setRagLoading(false);
  }

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <h2 style={{ margin: '0 0 1rem' }}>🕐 Historical Replay</h2>
      <p style={{ color: '#64748b', margin: '0 0 1rem', fontSize: '0.85rem' }}>
        Select a real historical issue date. See what the model predicted using only information available at that time, then reveal what actually happened.
      </p>

      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {REPLAY_DATES.map((d) => (
          <button
            key={d}
            onClick={() => setSelectedDate(d)}
            style={{
              background: selectedDate === d ? '#2563eb' : '#e2e8f0',
              color: selectedDate === d ? '#fff' : '#374151',
              border: 'none',
              borderRadius: '6px',
              padding: '0.4rem 0.9rem',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            {d}
          </button>
        ))}
      </div>

      {loading && <p style={{ color: '#94a3b8' }}>Loading replay...</p>}

      {replay && !replay.error && replay.predictions && (
        <div>
          <h3 style={{ margin: '0 0 0.75rem', color: '#1e293b' }}>
            Forecast issued: {selectedDate}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
            {replay.predictions.map((p) => (
              <div
                key={p.lead_day}
                style={{
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '0.75rem',
                }}
              >
                <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a', marginBottom: '0.3rem' }}>
                  Day {p.lead_day} → {p.valid_date}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                  Bust prob:{' '}
                  <strong style={{ color: p.bust_probability > 0.45 ? '#ef4444' : p.bust_probability > 0.2 ? '#f59e0b' : '#22c55e' }}>
                    {(p.bust_probability * 100).toFixed(1)}%
                  </strong>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                  {p.confidence_band} confidence
                </div>
                {p.rule_summary && p.rule_summary[0] && (
                  <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.4rem', fontStyle: 'italic' }}>
                    {p.rule_summary[0]}
                  </div>
                )}
              </div>
            ))}
          </div>

          {replay.actual_rainfall !== null && replay.actual_rainfall !== undefined && (
            <div style={{ background: '#fef9c3', border: '1px solid #fde047', borderRadius: '8px', padding: '0.75rem', marginBottom: '1rem' }}>
              <strong>Actual IMD Rainfall Reference:</strong> {JSON.stringify(replay.actual_rainfall)}
            </div>
          )}

          {replay.note && (
            <div style={{ color: '#6b7280', fontSize: '0.8rem', marginBottom: '0.75rem', fontStyle: 'italic' }}>
              Note: {replay.note}
            </div>
          )}

          <button
            onClick={handleRag}
            disabled={ragLoading}
            style={{
              background: ragLoading ? '#93c5fd' : '#2563eb',
              color: '#fff', border: 'none', borderRadius: '6px',
              padding: '0.5rem 1rem', cursor: 'pointer', fontSize: '0.85rem',
            }}
          >
            {ragLoading ? 'Asking...' : '💬 Get Meteorological Context'}
          </button>

          {ragAnswer && (
            <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '6px', padding: '0.75rem', marginTop: '0.75rem' }}>
              <h4 style={{ margin: '0 0 0.4rem', color: '#0369a1' }}>📖 RAG Explanation</h4>
              <p style={{ margin: 0, fontSize: '0.84rem', color: '#1e3a5f' }}>{ragAnswer.answer}</p>
              {ragAnswer.sources && ragAnswer.sources.length > 0 && (
                <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: '#0369a1' }}>
                  Sources: {ragAnswer.sources.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {replay && replay.error && (
        <p style={{ color: '#ef4444' }}>Error: {replay.error}</p>
      )}
    </div>
  );
}
