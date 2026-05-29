const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function get(path) {
  try {
    const r = await fetch(`${BASE}${path}`);
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export const fetchStatus = () => get('/analytics/status');
export const fetchKpiVentas = () => get('/analytics/kpis/total-ventas');
export const fetchKpiTransacciones = () => get('/analytics/kpis/total-transacciones');
export const fetchChart = (name) => get(`/analytics/charts/${name}`);
