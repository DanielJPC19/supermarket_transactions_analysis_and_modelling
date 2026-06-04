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

// ETL
export const fetchEtlStatus = () => get('/etl/status');
export const triggerRollback = () =>
  fetch(`${BASE}/etl/rollback`, { method: 'POST' }).catch(() => null);

// K-Means
export const fetchKmeansStatus = () => get('/kmeans/status');
export const fetchKmeansAssignments = () => get('/kmeans/cluster-assignments');
export const fetchKmeansProfiles = () => get('/kmeans/cluster-profiles');
export const fetchKmeansMetrics = () => get('/kmeans/evaluation-metrics');
export const fetchKmeansChart = (name) => get(`/kmeans/charts/${name}`);
export const triggerKmeans = () =>
  fetch(`${BASE}/kmeans/trigger`, { method: 'POST' }).catch(() => null);
