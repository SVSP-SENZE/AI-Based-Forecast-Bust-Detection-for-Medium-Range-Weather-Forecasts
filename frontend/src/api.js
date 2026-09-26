const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchHealth() {
  const r = await fetch(`${API}/health`);
  return r.json();
}

export async function fetchReliability(lat, lon, issueDate) {
  const r = await fetch(`${API}/forecast-reliability?lat=${lat}&lon=${lon}&issue_date=${issueDate}`);
  return r.json();
}

export async function fetchRegion(leadDay, issueDate) {
  const r = await fetch(`${API}/region?lead_day=${leadDay}&issue_date=${issueDate}`);
  return r.json();
}

export async function fetchExplanation(lat, lon, leadDay, issueDate) {
  const r = await fetch(`${API}/explanation?lat=${lat}&lon=${lon}&lead_day=${leadDay}&issue_date=${issueDate}`);
  return r.json();
}

export async function fetchMetrics() {
  const r = await fetch(`${API}/metrics`);
  return r.json();
}

export async function fetchReplay(issueDate) {
  const r = await fetch(`${API}/replay?issue_date=${issueDate}`);
  return r.json();
}

export async function postRagQuery(question, context = null) {
  const r = await fetch(`${API}/rag-query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, context }),
  });
  return r.json();
}
