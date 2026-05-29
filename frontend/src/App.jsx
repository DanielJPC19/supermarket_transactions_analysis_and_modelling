import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box, Button, Container, createTheme, CssBaseline, Grid, ThemeProvider, Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import './App.css';

import Sidebar, { DRAWER_WIDTH } from './components/Sidebar';
import KpiCard from './components/KpiCard';
import PlotlyChart from './components/PlotlyChart';
import { useJobStatus } from './hooks/useJobStatus';
import { fetchStatus, fetchKpiVentas, fetchKpiTransacciones } from './api/analytics';

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

function StatusCard({ title, job }) {
  const Row = ({ label, value }) => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.6 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" fontWeight={500}>{value ?? '—'}</Typography>
    </Box>
  );
  return (
    <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2.5, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', height: '100%' }}>
      <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5, color: 'text.primary' }}>
        {title}
      </Typography>
      <Row label="Estado" value={job?.status ?? 'Sin datos'} />
      <Row label="Inicio" value={job?.started_at ? new Date(job.started_at).toLocaleString('es-CO') : null} />
      <Row label="Fin"    value={job?.finished_at ? new Date(job.finished_at).toLocaleString('es-CO') : null} />
      {job?.message && <Row label="Mensaje" value={job.message} />}
    </Box>
  );
}

function EtlPanel({ jobStatus, onTriggerEtl }) {
  const etlRunning = jobStatus?.ETL?.status === 'running';
  return (
    <Box sx={{ maxWidth: 860, mx: 'auto' }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
        Gestión del ETL
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <StatusCard title="Estado del ETL" job={jobStatus?.ETL} />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <StatusCard title="Estado del cómputo de KPIs" job={jobStatus?.KPIs} />
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
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
      </Box>
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
  const [activeSection, setActiveSection] = useState('eda');
  const [cacheWarm, setCacheWarm]         = useState(false);
  const [kpiVentas, setKpiVentas]         = useState(null);
  const [kpiTx, setKpiTx]                 = useState(null);
  const [refreshKey, setRefreshKey]       = useState(0);
  const retryCount  = useRef(0);
  const timeoutRef  = useRef(null);
  const jobStatus   = useJobStatus();

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

  const handleTriggerEtl = useCallback(async () => {
    await fetch(`${API_BASE}/etl/trigger`, { method: 'POST' });
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
    return () => clearTimeout(timeoutRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Refrescar charts automáticamente cuando un job KPIs completa via WebSocket
  useEffect(() => {
    if (jobStatus?.KPIs?.status === 'completed') {
      checkStatus().then((warm) => { if (warm) setRefreshKey((k) => k + 1); });
    }
  }, [jobStatus?.KPIs?.status]); // eslint-disable-line react-hooks/exhaustive-deps

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
            <EtlPanel jobStatus={jobStatus} onTriggerEtl={handleTriggerEtl} />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}
