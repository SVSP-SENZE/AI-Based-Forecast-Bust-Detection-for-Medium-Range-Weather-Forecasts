// Shared utility functions
export function bandMeta(prob) {
  if (prob < 0.18)  return { label: 'High Confidence', cls: 'badge-green',  color: '#22c55e', barColor: '#22c55e' };
  if (prob < 0.35)  return { label: 'Moderate Risk',   cls: 'badge-amber',  color: '#f59e0b', barColor: '#f59e0b' };
  if (prob < 0.55)  return { label: 'Elevated Risk',   cls: 'badge-orange', color: '#f97316', barColor: '#f97316' };
  return              { label: 'Low Confidence',  cls: 'badge-red',   color: '#ef4444', barColor: '#ef4444' };
}

export function bandColor(bandOrProb) {
  if (typeof bandOrProb === 'number') return bandMeta(bandOrProb).color;
  if (bandOrProb === 'High')     return '#22c55e';
  if (bandOrProb === 'Moderate') return '#f59e0b';
  if (bandOrProb === 'Low')      return '#ef4444';
  return '#8b93a8';
}

export function probColor(prob) {
  return bandMeta(prob).color;
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

export function formatProb(p) {
  return `${(p * 100).toFixed(1)}%`;
}
