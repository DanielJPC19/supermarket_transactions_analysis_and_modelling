import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress,
  Container, Grid, Typography,
} from '@mui/material';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StatusBadge from './StatusBadge';
import PlotlyChart from './PlotlyChart';
import { fetchKmeansStatus, fetchKmeansProfiles, triggerKmeans, fetchKmeansChart } from '../api/analytics';

function SectionTitle({ children }) {
  return (
    <Typography
      variant="subtitle1"
      fontWeight={600}
      sx={{ borderLeft: '4px solid', borderColor: 'primary.main', pl: 1.5, mb: 2, mt: 1 }}
    >
      {children}
    </Typography>
  );
}

function ClusterCard({ profile }) {
  const rows = [
    { label: 'Clientes',          value: profile.size.toLocaleString('es-CO') },
    { label: 'Frecuencia media',  value: profile.mean_frequency.toFixed(1) },
    { label: 'Unidades media',    value: profile.mean_total_units.toFixed(1) },
    { label: 'Prod. distintos',   value: profile.mean_unique_products.toFixed(1) },
    { label: 'Cat. distintas',    value: profile.mean_unique_categories.toFixed(1) },
    { label: 'Tamaño canasta',    value: profile.mean_avg_basket_size.toFixed(2) },
  ];

  const COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'];
  const color  = COLORS[profile.cluster % COLORS.length];

  return (
    <Card sx={{ height: '100%', borderTop: `4px solid ${color}` }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
          <ScatterPlotIcon sx={{ color, fontSize: 20 }} />
          <Typography variant="subtitle2" fontWeight={700}>
            Cluster {profile.cluster}
          </Typography>
        </Box>
        {rows.map(({ label, value }) => (
          <Box key={label} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.4 }}>
            <Typography variant="body2" color="text.secondary">{label}</Typography>
            <Typography variant="body2" fontWeight={500}>{value}</Typography>
          </Box>
        ))}
      </CardContent>
    </Card>
  );
}

export default function KmeansSection({ jobStatus }) {
  const [kmeansInfo, setKmeansInfo] = useState(null);   // {cached, best_k}
  const [profiles,   setProfiles]   = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading,    setLoading]    = useState(false);

  const kmeansJob = jobStatus?.KMeans;

  const loadStatus = useCallback(async () => {
    const st = await fetchKmeansStatus();
    if (!st) return;
    setKmeansInfo(st);
    if (st.cached) {
      const profs = await fetchKmeansProfiles();
      if (profs) setProfiles(profs);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Refrescar cuando el job KMeans completa via WebSocket
  useEffect(() => {
    if (kmeansJob?.status === 'completed') {
      loadStatus().then(() => setRefreshKey((k) => k + 1));
    }
  }, [kmeansJob?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = async () => {
    setLoading(true);
    await triggerKmeans();
    setLoading(false);
  };

  const isRunning = kmeansJob?.status === 'running' || loading;
  const hasCached  = kmeansInfo?.cached;

  return (
    <Container maxWidth="xl">
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>
          Segmentación de Clientes — K-Means
        </Typography>
        {kmeansJob && <StatusBadge status={kmeansJob.status} />}
      </Box>

      {/* Info chips */}
      <Box sx={{ display: 'flex', gap: 1.5, mb: 3, flexWrap: 'wrap' }}>
        {hasCached && kmeansInfo.best_k && (
          <Chip label={`Mejor K = ${kmeansInfo.best_k}`} color="primary" variant="outlined" />
        )}
        {profiles && (
          <Chip label={`${profiles.reduce((a, p) => a + p.size, 0).toLocaleString('es-CO')} clientes segmentados`} color="success" variant="outlined" />
        )}
      </Box>

      {/* Botón de ejecución */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          startIcon={isRunning ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
          disabled={isRunning}
          onClick={handleRun}
          sx={{ px: 3, borderRadius: 2 }}
        >
          {isRunning ? 'Ejecutando K-Means...' : hasCached ? 'Re-ejecutar K-Means' : 'Ejecutar K-Means'}
        </Button>
        {!hasCached && !isRunning && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
            El análisis puede tardar varios minutos (PySpark + MLlib).
          </Typography>
        )}
      </Box>

      {/* Estado del job */}
      {kmeansJob?.status === 'failed' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          El job K-Means falló: {kmeansJob.message || 'Error desconocido.'}
        </Alert>
      )}

      {!hasCached && !isRunning && (
        <Alert severity="info" sx={{ mb: 3 }}>
          No hay resultados de segmentación. Haz click en &quot;Ejecutar K-Means&quot; para iniciar el análisis.
        </Alert>
      )}

      {isRunning && (
        <Alert severity="info" sx={{ mb: 3 }}>
          El job K-Means está corriendo en Spark. Los resultados aparecerán automáticamente al completar.
        </Alert>
      )}

      {/* Cluster Cards */}
      {profiles && profiles.length > 0 && (
        <>
          <SectionTitle>Perfiles de Clusters</SectionTitle>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            {profiles.map((p) => (
              <Grid key={p.cluster} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
                <ClusterCard profile={p} />
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* Gráficos */}
      {hasCached && (
        <>
          <SectionTitle>Visualización del Clustering</SectionTitle>

          {/* Scatter PCA */}
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, mb: 2.5 }}>
            <PlotlyChart
              chartName="scatter-clusters"
              minHeight={520}
              refreshKey={refreshKey}
              fetchFn={fetchKmeansChart}
            />
          </Box>

          {/* Perfiles + Evaluación lado a lado */}
          <Grid container spacing={2} sx={{ mb: 2.5 }}>
            <Grid size={{ xs: 12, lg: 7 }}>
              <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
                <PlotlyChart
                  chartName="cluster-profiles"
                  minHeight={460}
                  refreshKey={refreshKey}
                  fetchFn={fetchKmeansChart}
                />
              </Box>
            </Grid>
            <Grid size={{ xs: 12, lg: 5 }}>
              <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
                <PlotlyChart
                  chartName="cluster-sizes"
                  minHeight={420}
                  refreshKey={refreshKey}
                  fetchFn={fetchKmeansChart}
                />
              </Box>
            </Grid>
          </Grid>

          {/* Curva del codo */}
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, mb: 3 }}>
            <PlotlyChart
              chartName="evaluation-metrics"
              minHeight={420}
              refreshKey={refreshKey}
              fetchFn={fetchKmeansChart}
            />
          </Box>

          <Typography variant="caption" color="text.disabled" display="block" align="center" sx={{ pb: 2 }}>
            Segmentación via PySpark MLlib KMeans · StandardScaler · PCA 2D · Silhouette Score
          </Typography>
        </>
      )}
    </Container>
  );
}
