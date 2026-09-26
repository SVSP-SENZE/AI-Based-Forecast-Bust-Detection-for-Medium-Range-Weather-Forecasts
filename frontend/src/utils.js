/* confidence band color mapping */
export function bandColor(band) {
  if (band === 'High')     return '#22c55e';   // green
  if (band === 'Moderate') return '#f59e0b';   // amber
  if (band === 'Low')      return '#ef4444';   // red
  return '#94a3b8';
}

export function probColor(prob) {
  if (prob < 0.20) return '#22c55e';
  if (prob < 0.45) return '#f59e0b';
  return '#ef4444';
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}
