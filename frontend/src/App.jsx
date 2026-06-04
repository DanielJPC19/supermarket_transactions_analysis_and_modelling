import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box, Button, Container, createTheme, CssBaseline, Grid, ThemeProvider, Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import HistoryIcon from '@mui/icons-material/History';
import './App.css';

import Sidebar, { DRAWER_WIDTH } from './components/Sidebar';
import StatusBadge from './components/StatusBadge';
import KpiCard from './components/KpiCard';
import PlotlyChart from './components/PlotlyChart';
import KmeansSection from './components/KmeansSection';
import { useJobStatus } from './hooks/useJobStatus';
import { fetchStatus, fetchKpiVentas, fetchKpiTransacciones, fetchEtlStatus, triggerRollback } from './api/analytics';

const POLL_INTERVAL = Number(import.meta.env.VITE_POLL_INTERVAL_MS) || 15000;
const MAX_RETRIES   = Number(import.meta.env.VITE_MAX_RETRIES)       || 30;
const API_BASE      = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const theme = createTheme({
  palette: {
    mode: 'light',
    background: { default: '#f4f6f8' },
    primary: { main: '#1976d2' },
  },
  shape: { borderRadius: 12 },
  typography: { fontFamily: "'Segoe UI', Arial, sans-serif" },
  components: {
    MuiCard: { styleOverrides: { root: { boxShadow: '0 1px 4px rgba(0,0,0,0.08)' } } },
  },
});

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

function InfoRow({ label, value }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" fontWeight={500} sx={{ maxWidth: '60%', textAlign: 'right', wordBreak: 'break-word' }}>
        {value ?? '—'}
      </Typography>
    </Box>
  );
}

function StatusCard({ title, job, lastSuccessful }) {
  const fmt = (ts) => ts ? new Date(ts).toLocaleString('es-CO') : null;
  return (
    <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', height: '100%' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="subtitle2" fontWeight={700}>{title}</Typography>
        <StatusBadge status={job?.status ?? null} />
      </Box>
      <InfoRow label="Inicio"       value={fmt(job?.started_at)} />
      <InfoRow label="Fin"          value={fmt(job?.finished_at)} />
      <InfoRow label="Último éxito" value={fmt(lastSuccessful?.finished_at)} />
      {job?.message && <InfoRow label="Error" value={job.message.slice(0, 120)} />}
    </Box>
  );
}

function EtlPanel({ jobStatus, lastSuccessful, onTriggerEtl, rollbackAvailable, onTriggerRollback }) {
  const etlRunning = jobStatus?.ETL?.status === 'running';

  const CARDS = [
    { key: 'ETL',          title: 'Estado del ETL'        },
    { key: 'KPIs',         title: 'Estado de KPIs'        },
    { key: 'KMeans',       title: 'Estado de K-Means'     },
    { key: 'Recomendador', title: 'Estado del Recomendador' },
  ];

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
        Gestión del Pipeline
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {CARDS.map(({ key, title }) => (
          <Grid key={key} size={{ xs: 12, sm: 6, lg: 3 }}>
            <StatusCard
              title={title}
              job={jobStatus?.[key]}
              lastSuccessful={lastSuccessful?.[key]}
            />
          </Grid>
        ))}
      </Grid>

      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={<PlayArrowIcon />}
          disabled={etlRunning}
          onClick={onTriggerEtl}
          size="large"
          sx={{ px: 4, borderRadius: 2 }}
        >
          {etlRunning ? 'Ejecutando...' : 'Ejecutar ETL'}
        </Button>
        {rollbackAvailable && !etlRunning && (
          <Button
            variant="outlined"
            color="warning"
            startIcon={<HistoryIcon />}
            onClick={onTriggerRollback}
            size="large"
            sx={{ px: 3, borderRadius: 2 }}
          >
            Rollback a versión anterior
          </Button>
        )}
      </Box>
      {rollbackAvailable && (
        <Typography variant="caption" color="text.secondary" display="block" align="center" sx={{ mt: 1 }}>
          Hay una versión anterior de los datos disponible para restaurar.
        </Typography>
      )}
    </Box>
  );
}

function DashboardContent({ refreshKey, kpiVentas, kpiTx }) {
  return (
    <Container maxWidth="xl">
      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, sm: 3 }}>
          <KpiCard label="Total Unidades Vendidas" value={kpiVentas} />
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <KpiCard label="Total Transacciones" value={kpiTx} />
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <KpiCard label="Clientes Únicos" value={131186} color="#2ca02c" />
        </Grid>
        <Grid size={{ xs: 6, sm: 3 }}>
          <KpiCard label="Productos Únicos" value={449} color="#ff7f0e" />
        </Grid>
      </Grid>

      <SectionTitle>Resumen Ejecutivo</SectionTitle>

      {/* Serie de tiempo */}
      <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, mb: 2.5 }}>
        <PlotlyChart chartName="serie-tiempo" minHeight={440} refreshKey={refreshKey} />
      </Box>

      {/* Top 10 */}
      <Grid container spacing={2} sx={{ mb: 2.5 }}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
            <PlotlyChart chartName="top10-productos" minHeight={400} refreshKey={refreshKey} />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
            <PlotlyChart chartName="top10-clientes" minHeight={400} refreshKey={refreshKey} />
          </Box>
        </Grid>
      </Grid>

      {/* Días pico + Categorías */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
            <PlotlyChart chartName="dias-pico" minHeight={380} refreshKey={refreshKey} />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
            <PlotlyChart chartName="categorias" minHeight={480} refreshKey={refreshKey} />
          </Box>
        </Grid>
      </Grid>

      <SectionTitle>Visualizaciones Analíticas</SectionTitle>

      {/* Boxplot + Heatmap */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
            <PlotlyChart chartName="boxplot" minHeight={440} refreshKey={refreshKey} />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, height: '100%' }}>
            <PlotlyChart chartName="heatmap" minHeight={460} refreshKey={refreshKey} />
          </Box>
        </Grid>
      </Grid>

      <Typography variant="caption" color="text.disabled" display="block" align="center" sx={{ pb: 2 }}>
        Datos: Transacciones 2013 · 4 Sucursales · Procesamiento distribuido con Apache Spark
      </Typography>
    </Container>
  );
}

export default function App() {
  const [activeSection,     setActiveSection]     = useState('eda');
  const [cacheWarm,         setCacheWarm]          = useState(false);
  const [kpiVentas,         setKpiVentas]          = useState(null);
  const [kpiTx,             setKpiTx]              = useState(null);
  const [refreshKey,        setRefreshKey]         = useState(0);
  const [rollbackAvailable, setRollbackAvailable]  = useState(false);
  const retryCount  = useRef(0);
  const timeoutRef  = useRef(null);
  const { jobStatus, lastSuccessful } = useJobStatus();

  const loadKpis = useCallback(async () => {
    const [v, tx] = await Promise.all([fetchKpiVentas(), fetchKpiTransacciones()]);
    if (v)  setKpiVentas(v.value);
    if (tx) setKpiTx(tx.value);
  }, []);

  const checkStatus = useCallback(async () => {
    const st = await fetchStatus();
    if (!st) return false;
    setCacheWarm(st.cache_warm);
    if (st.cache_warm) await loadKpis();
    return st.cache_warm;
  }, [loadKpis]);

  const poll = useCallback(async () => {
    const warm = await checkStatus();
    if (!warm && retryCount.current < MAX_RETRIES) {
      retryCount.current += 1;
      timeoutRef.current = setTimeout(async () => {
        const nowWarm = await checkStatus();
        if (nowWarm) setRefreshKey((k) => k + 1);
        else poll();
      }, POLL_INTERVAL);
    }
  }, [checkStatus]);

  const checkRollback = useCallback(async () => {
    const st = await fetchEtlStatus();
    if (st) setRollbackAvailable(st.rollback_available ?? false);
  }, []);

  const handleTriggerEtl = useCallback(async () => {
    await fetch(`${API_BASE}/etl/trigger`, { method: 'POST' });
  }, []);

  const handleTriggerRollback = useCallback(async () => {
    await triggerRollback();
    setRollbackAvailable(false);
  }, []);

  const handleRefresh = useCallback(async () => {
    clearTimeout(timeoutRef.current);
    retryCount.current = 0;
    await checkStatus();
    setRefreshKey((k) => k + 1);
    poll();
  }, [checkStatus, poll]);

  useEffect(() => {
    poll();
    checkRollback();
    return () => clearTimeout(timeoutRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Refrescar charts automáticamente cuando un job KPIs completa via WebSocket
  useEffect(() => {
    if (jobStatus?.KPIs?.status === 'completed') {
      checkStatus().then((warm) => { if (warm) setRefreshKey((k) => k + 1); });
    }
  }, [jobStatus?.KPIs?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Actualizar disponibilidad de rollback cuando el ETL cambia de estado
  useEffect(() => {
    const st = jobStatus?.ETL?.status;
    if (st === 'completed' || st === 'failed' || st === 'rolled_back') {
      checkRollback();
    }
  }, [jobStatus?.ETL?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar
          activeSection={activeSection}
          onNavChange={setActiveSection}
          jobStatus={jobStatus}
          cacheWarm={cacheWarm}
        />
        <Box
          component="main"
          sx={{ flexGrow: 1, p: 3, ml: `${DRAWER_WIDTH}px`, bgcolor: 'background.default', minHeight: '100vh' }}
        >
          {activeSection === 'eda' && (
            <DashboardContent
              refreshKey={refreshKey}
              kpiVentas={kpiVentas}
              kpiTx={kpiTx}
            />
          )}
          {activeSection === 'etl' && (
            <EtlPanel
              jobStatus={jobStatus}
              lastSuccessful={lastSuccessful}
              onTriggerEtl={handleTriggerEtl}
              rollbackAvailable={rollbackAvailable}
              onTriggerRollback={handleTriggerRollback}
            />
          )}
          {activeSection === 'kmeans' && (
            <KmeansSection jobStatus={jobStatus} />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}
