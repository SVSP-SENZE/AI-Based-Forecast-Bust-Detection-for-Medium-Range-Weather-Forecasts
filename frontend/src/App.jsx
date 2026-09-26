import { useState, useEffect, useCallback } from 'react';
import RegionMap from './RegionMap';
import WhyPanel from './WhyPanel';
import ReplayPanel from './ReplayPanel';
import MetricsPanel from './MetricsPanel';
import { fetchRegion, fetchExplanation, postRagQuery } from './api';
import { bandColor } from './utils';

const LEAD_DAYS = [1, 3, 5, 7, 10];
const DEFAULT_DATE = '2003-07-01';

export default function App() {
  const [activeTab, setActiveTab] = useState('map');     // 'map' | 'replay' | 'metrics'
  const [leadDay, setLeadDay] = useState(3);
  const [issueDate, setIssueDate] = useState(DEFAULT_DATE);
  const [cells, setCells] = useState([]);
  const [selectedCell, setSelectedCell] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [ragAnswer, setRagAnswer] = useState(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [mapLoading, setMapLoading] = useState(false);
  const [apiError, setApiError] = useState(null);

  const loadRegion = useCallback(async () => {
    setMapLoading(true);
    setApiError(null);
    try {
      const data = await fetchRegion(leadDay, issueDate);
      setCells(data.cells || []);
    } catch (e) {
      setApiError('Cannot reach API. Make sure the backend is running on port 8000.');
      setCells([]);
    }
    setMapLoading(false);
  }, [leadDay, issueDate]);

  useEffect(() => {
    loadRegion();
  }, [loadRegion]);

  const handleCellClick = useCallback(async (cell) => {
    setSelectedCell(cell);
    setExplanation(null);
    setRagAnswer(null);
    try {
      const exp = await fetchExplanation(cell.lat, cell.lon, leadDay, issueDate);
      setExplanation(exp);
    } catch {}
  }, [leadDay, issueDate]);

  const handleRagQuery = useCallback(async () => {
    if (!explanation) return;
    setRagLoading(true);
    const q = `Why might the Day ${leadDay} rainfall forecast issued on ${issueDate} over lat=${explanation.location?.lat}, lon=${explanation.location?.lon} bust? The model identified: ${explanation.rule_summary?.join('; ')}`;
    const ans = await postRagQuery(q, explanation);
    setRagAnswer(ans);
    setRagLoading(false);
  }, [explanation, leadDay, issueDate]);

  const tabStyle = (tab) => ({
    background: activeTab === tab ? '#2563eb' : '#e2e8f0',
    color: activeTab === tab ? '#fff' : '#374151',
    border: 'none',
    borderRadius: '6px',
    padding: '0.45rem 1rem',
    cursor: 'pointer',
    fontSize: '0.85rem',
    fontWeight: activeTab === tab ? 700 : 400,
  });

  return (
    <div style={{ fontFamily: 'sans-serif', background: '#f1f5f9', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ background: '#0f172a', color: '#fff', padding: '1rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>
            ⛈️ Forecast Bust Detector
          </h1>
          <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8' }}>
            AI-based reliability engine · Maharashtra region · GEFSv12 + IMD
          </p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
          <button style={tabStyle('map')} onClick={() => setActiveTab('map')}>🗺️ Map</button>
          <button style={tabStyle('replay')} onClick={() => setActiveTab('replay')}>🕐 Replay</button>
          <button style={tabStyle('metrics')} onClick={() => setActiveTab('metrics')}>📊 Metrics</button>
        </div>
      </div>

      {/* Error banner */}
      {apiError && (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '0.75rem 1.5rem', fontSize: '0.85rem' }}>
          ⚠️ {apiError}
        </div>
      )}

      {/* Map tab */}
      {activeTab === 'map' && (
        <div style={{ display: 'flex', gap: '0', height: 'calc(100vh - 80px)' }}>
          {/* Left: controls + map */}
          <div style={{ flex: 1.6, display: 'flex', flexDirection: 'column', padding: '1rem', gap: '0.75rem', overflow: 'auto' }}>
            {/* Controls */}
            <div style={{ background: '#fff', borderRadius: '8px', padding: '0.75rem 1rem', display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap', boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: '#64748b', display: 'block', marginBottom: '0.25rem' }}>Issue Date</label>
                <input
                  type="date"
                  value={issueDate}
                  onChange={(e) => setIssueDate(e.target.value)}
                  style={{ border: '1px solid #d1d5db', borderRadius: '5px', padding: '0.3rem 0.5rem', fontSize: '0.85rem' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: '#64748b', display: 'block', marginBottom: '0.25rem' }}>Lead Day</label>
                <div style={{ display: 'flex', gap: '0.35rem' }}>
                  {LEAD_DAYS.map((d) => (
                    <button
                      key={d}
                      onClick={() => setLeadDay(d)}
                      style={{
                        background: leadDay === d ? '#2563eb' : '#e2e8f0',
                        color: leadDay === d ? '#fff' : '#374151',
                        border: 'none', borderRadius: '5px',
                        padding: '0.3rem 0.6rem', cursor: 'pointer', fontSize: '0.82rem',
                        fontWeight: leadDay === d ? 700 : 400,
                      }}
                    >
                      D{d}
                    </button>
                  ))}
                </div>
              </div>
              {mapLoading && <span style={{ fontSize: '0.8rem', color: '#3b82f6' }}>Loading map...</span>}
            </div>

            {/* Legend */}
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.78rem', color: '#64748b' }}>
              {[['High confidence', '#22c55e'], ['Moderate confidence', '#f59e0b'], ['Low confidence (bust risk)', '#ef4444']].map(([label, color]) => (
                <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ width: 14, height: 14, background: color, borderRadius: 3, display: 'inline-block' }} />
                  {label}
                </span>
              ))}
            </div>

            {/* Map */}
            <div style={{ background: '#fff', borderRadius: '8px', overflow: 'hidden', flex: 1, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
              <RegionMap cells={cells} onCellClick={handleCellClick} selectedCell={selectedCell} />
            </div>
          </div>

          {/* Right: Why panel */}
          <div style={{ width: '340px', background: '#fff', borderLeft: '1px solid #e2e8f0', overflow: 'auto', boxShadow: '-2px 0 8px rgba(0,0,0,.04)' }}>
            {selectedCell && (
              <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: '0.82rem', color: '#475569' }}>
                📍 Lat {selectedCell.lat} · Lon {selectedCell.lon} · Day {leadDay}
              </div>
            )}
            <WhyPanel
              explanation={explanation}
              ragAnswer={ragAnswer}
              onRagQuery={handleRagQuery}
              loading={ragLoading}
            />
          </div>
        </div>
      )}

      {/* Replay tab */}
      {activeTab === 'replay' && (
        <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1rem', background: '#fff', marginTop: '1rem', borderRadius: '8px' }}>
          <ReplayPanel />
        </div>
      )}

      {/* Metrics tab */}
      {activeTab === 'metrics' && (
        <div style={{ maxWidth: '900px', margin: '0 auto', padding: '1rem', background: '#fff', marginTop: '1rem', borderRadius: '8px' }}>
          <MetricsPanel />
        </div>
      )}
    </div>
  );
}
