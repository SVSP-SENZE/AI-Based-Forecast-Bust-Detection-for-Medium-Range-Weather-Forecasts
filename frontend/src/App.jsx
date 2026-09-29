import { useState, useEffect, useCallback } from 'react';
import RegionMap from './RegionMap';
import WhyPanel from './WhyPanel';
import ReplayPanel from './ReplayPanel';
import MetricsPanel from './MetricsPanel';
import { fetchRegion, fetchExplanation, fetchReliability, postRagQuery } from './api';
import { bandMeta, formatProb } from './utils';
import './App.css';

const LEAD_DAYS = [1, 3, 5, 7, 10];
const DEFAULT_DATE = '2003-07-15';

export default function App() {
  const [activeTab, setActiveTab] = useState('map');
  const [leadDay, setLeadDay] = useState(5);
  const [issueDate, setIssueDate] = useState(DEFAULT_DATE);
  const [cells, setCells] = useState([]);
  const [selectedCell, setSelectedCell] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [reliability, setReliability] = useState(null); // full 10-day trajectory
  const [ragAnswer, setRagAnswer] = useState(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [mapLoading, setMapLoading] = useState(false);
  const [explLoading, setExplLoading] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [backendOk, setBackendOk] = useState(null);

  // Health ping
  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then(r => r.ok ? setBackendOk(true) : setBackendOk(false))
      .catch(() => setBackendOk(false));
  }, []);

  const loadRegion = useCallback(async () => {
    setMapLoading(true);
    setApiError(null);
    try {
      const data = await fetchRegion(leadDay, issueDate);
      setCells(data.cells || []);
    } catch {
      setApiError('Cannot reach backend on port 8000. Please start the API server.');
      setCells([]);
    }
    setMapLoading(false);
  }, [leadDay, issueDate]);

  useEffect(() => { loadRegion(); }, [loadRegion]);

  const handleCellClick = useCallback(async (cell) => {
    setSelectedCell(cell);
    setExplanation(null);
    setReliability(null);
    setRagAnswer(null);
    setExplLoading(true);
    try {
      const [exp, rel] = await Promise.all([
        fetchExplanation(cell.lat, cell.lon, leadDay, issueDate),
        fetchReliability(cell.lat, cell.lon, issueDate),
      ]);
      setExplanation(exp);
      setReliability(rel);
    } catch {}
    setExplLoading(false);
  }, [leadDay, issueDate]);

  const handleRagQuery = useCallback(async () => {
    if (!explanation) return;
    setRagLoading(true);
    const q = `Why might the Day ${leadDay} rainfall forecast over lat=${explanation.location?.lat}°N, lon=${explanation.location?.lon}°E issued on ${issueDate} bust? The model signals: ${explanation.rule_summary?.join('; ')}`;
    const ans = await postRagQuery(q, explanation);
    setRagAnswer(ans);
    setRagLoading(false);
  }, [explanation, leadDay, issueDate]);

  // Compute map-wide statistics
  const mapStats = cells.length > 0 ? {
    highRisk: cells.filter(c => c.bust_probability >= 0.55).length,
    elevRisk:  cells.filter(c => c.bust_probability >= 0.35 && c.bust_probability < 0.55).length,
    modRisk:  cells.filter(c => c.bust_probability >= 0.18 && c.bust_probability < 0.35).length,
    safe:     cells.filter(c => c.bust_probability < 0.18).length,
    avgProb:  cells.reduce((a,c) => a + c.bust_probability, 0) / cells.length,
  } : null;

  return (
    <div className="app-shell">
      {/* ── HEADER ── */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon">⛈</div>
          <div>
            <div className="brand-title">Forecast Bust Detector</div>
            <div className="brand-sub">AI-based reliability engine · Maharashtra & W. Ghats · GEFSv12 + IMD</div>
          </div>
        </div>

        <nav className="header-nav">
          {[
            { id: 'map',     icon: '◈', label: 'Map' },
            { id: 'replay',  icon: '⟳', label: 'Replay' },
            { id: 'metrics', icon: '⊞', label: 'Metrics' },
          ].map(t => (
            <button
              key={t.id}
              className={`nav-tab ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              <span className="nav-icon">{t.icon}</span>{t.label}
            </button>
          ))}
        </nav>

        <div className="header-status">
          <div className={`status-pill ${backendOk === true ? 'ok' : backendOk === false ? 'error' : 'pinging'}`}>
            <div className="status-dot" />
            {backendOk === true ? 'API Live' : backendOk === false ? 'API Offline' : 'Connecting…'}
          </div>
        </div>
      </header>

      {/* ── ERROR BANNER ── */}
      {apiError && (
        <div className="error-banner">
          <span>⚠</span> {apiError}
        </div>
      )}

      {/* ══════════════ MAP TAB ══════════════ */}
      {activeTab === 'map' && (
        <div className="map-layout">

          {/* ── LEFT COLUMN ── */}
          <div className="map-left">
            {/* Controls row */}
            <div className="controls-bar card">
              <div className="control-group">
                <label className="ctrl-label">Issue Date</label>
                <input
                  type="date"
                  className="ctrl-input"
                  value={issueDate}
                  onChange={e => setIssueDate(e.target.value)}
                />
              </div>
              <div className="control-group">
                <label className="ctrl-label">Lead Day</label>
                <div className="lead-day-pills">
                  {LEAD_DAYS.map(d => (
                    <button
                      key={d}
                      className={`lead-pill ${leadDay === d ? 'active' : ''}`}
                      onClick={() => setLeadDay(d)}
                    >
                      D{d}
                    </button>
                  ))}
                </div>
              </div>
              <div className="ctrl-spacer" />
              {mapLoading && (
                <div className="loading-badge">
                  <div className="spin" /> Loading
                </div>
              )}
            </div>

            {/* Summary stats bar */}
            {mapStats && (
              <div className="stats-row">
                <StatChip color="#ef4444" label="High Risk"    value={mapStats.highRisk} total={cells.length} />
                <StatChip color="#f97316" label="Elevated"     value={mapStats.elevRisk}  total={cells.length} />
                <StatChip color="#f59e0b" label="Moderate"     value={mapStats.modRisk}  total={cells.length} />
                <StatChip color="#22c55e" label="High Conf."   value={mapStats.safe}     total={cells.length} />
                <div className="avg-prob-chip">
                  <span className="avg-label">Avg. Bust Prob.</span>
                  <span className="avg-value" style={{ color: bandMeta(mapStats.avgProb).color }}>
                    {formatProb(mapStats.avgProb)}
                  </span>
                </div>
              </div>
            )}

            {/* Legend */}
            <div className="legend-row">
              {[
                ['< 18% High Confidence', '#22c55e'],
                ['18–35% Moderate Risk',  '#f59e0b'],
                ['35–55% Elevated Risk',  '#f97316'],
                ['> 55% Low Confidence',  '#ef4444'],
              ].map(([label, color]) => (
                <span key={label} className="legend-item">
                  <span className="legend-dot" style={{ background: color }} />
                  {label}
                </span>
              ))}
            </div>

            {/* Map */}
            <div className="map-container card">
              <RegionMap cells={cells} onCellClick={handleCellClick} selectedCell={selectedCell} />
            </div>
          </div>

          {/* ── RIGHT PANEL ── */}
          <div className="side-panel">
            {selectedCell ? (
              <>
                {/* Cell header */}
                <div className="panel-location">
                  <div className="loc-coords">
                    <span className="mono">{selectedCell.lat}°N, {selectedCell.lon}°E</span>
                    <span className="loc-lead">Day {leadDay}</span>
                  </div>
                  {selectedCell.bust_probability != null && (
                    <div
                      className="loc-prob badge"
                      style={{
                        background: bandMeta(selectedCell.bust_probability).color + '22',
                        color: bandMeta(selectedCell.bust_probability).color,
                      }}
                    >
                      {formatProb(selectedCell.bust_probability)}
                    </div>
                  )}
                </div>

                {/* 10-day trajectory mini chart */}
                {reliability?.forecasts && (
                  <div className="trajectory-section">
                    <div className="section-title">10-Day Bust Probability Trajectory</div>
                    <TrajectoryChart forecasts={reliability.forecasts} activeDay={leadDay} />
                  </div>
                )}

                {/* Why panel */}
                {explLoading ? (
                  <div className="panel-loading">
                    <div className="shimmer" style={{ height: 80, borderRadius: 8, margin: '1rem' }} />
                  </div>
                ) : (
                  <WhyPanel
                    explanation={explanation}
                    ragAnswer={ragAnswer}
                    onRagQuery={handleRagQuery}
                    loading={ragLoading}
                  />
                )}
              </>
            ) : (
              <div className="panel-empty">
                <div className="empty-icon">◈</div>
                <div className="empty-title">Select a grid cell</div>
                <div className="empty-sub">Click any point on the map to view<br/>bust risk details and SHAP drivers</div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'replay' && (
        <div className="tab-page"><ReplayPanel /></div>
      )}
      {activeTab === 'metrics' && (
        <div className="tab-page"><MetricsPanel /></div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────

function StatChip({ color, label, value, total }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="stat-chip">
      <div className="stat-dot" style={{ background: color }} />
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
      <div className="stat-bar">
        <div className="stat-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function TrajectoryChart({ forecasts, activeDay }) {
  const maxProb = Math.max(...forecasts.map(f => f.bust_probability), 0.1);
  return (
    <div className="traj-chart">
      {forecasts.map(f => {
        const meta = bandMeta(f.bust_probability);
        const pct = (f.bust_probability / maxProb) * 100;
        const isActive = f.lead_day === activeDay;
        return (
          <div key={f.lead_day} className={`traj-bar-wrap ${isActive ? 'traj-active' : ''}`}>
            <div className="traj-prob mono" style={{ color: meta.color }}>
              {formatProb(f.bust_probability)}
            </div>
            <div className="traj-col">
              <div
                className="traj-fill"
                style={{
                  height: `${Math.max(pct, 6)}%`,
                  background: meta.color,
                  opacity: isActive ? 1 : 0.55,
                  boxShadow: isActive ? `0 0 8px ${meta.color}60` : 'none',
                }}
              />
            </div>
            <div className="traj-label mono">D{f.lead_day}</div>
          </div>
        );
      })}
    </div>
  );
}
