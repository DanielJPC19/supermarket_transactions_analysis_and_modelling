import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress,
  Container, Divider, Grid, InputAdornment, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow,
  TextField, Typography,
} from '@mui/material';
import RecommendIcon from '@mui/icons-material/Recommend';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SearchIcon from '@mui/icons-material/Search';
import PersonIcon from '@mui/icons-material/Person';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import StatusBadge from './StatusBadge';
import PlotlyChart from './PlotlyChart';
import {
  fetchRecommenderStatus,
  triggerRecommender,
  fetchRecommendationsForCustomer,
  fetchRecommendationsForProduct,
  fetchRecommenderChart,
} from '../api/analytics';

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

function MetricCard({ label, value, color = 'primary.main' }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ textAlign: 'center', py: 3 }}>
        <Typography variant="h4" fontWeight={700} sx={{ color }}>
          {value !== null && value !== undefined ? (value * 100).toFixed(4) + '%' : '—'}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {label}
        </Typography>
      </CardContent>
    </Card>
  );
}

function RecommendationTable({ rows, columns }) {
  if (!rows || rows.length === 0) return null;
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col.key} sx={{ fontWeight: 600 }}>{col.label}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i} hover>
              {columns.map((col) => (
                <TableCell key={col.key}>
                  {col.format ? col.format(row[col.key]) : row[col.key]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function CustomerSearch({ disabled }) {
  const [customerId, setCustomerId] = useState('');
  const [result,     setResult]     = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  const handleSearch = async () => {
    if (!customerId.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    const data = await fetchRecommendationsForCustomer(customerId.trim());
    if (!data) {
      setError(`Cliente "${customerId}" no encontrado en las recomendaciones.`);
    } else {
      setResult(data);
    }
    setLoading(false);
  };

  const columns = [
    { key: 'rank',        label: '#' },
    { key: 'producto_id', label: 'Producto ID' },
    { key: 'score',       label: 'Score', format: (v) => (v * 100).toFixed(2) + '%' },
  ];

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <PersonIcon color="primary" />
          <Typography variant="subtitle2" fontWeight={700}>
            Recomendaciones por Cliente
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            size="small"
            label="ID de Cliente"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !disabled && handleSearch()}
            disabled={disabled}
            sx={{ flexGrow: 1 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            onClick={handleSearch}
            disabled={disabled || loading || !customerId.trim()}
            sx={{ borderRadius: 2, minWidth: 80 }}
          >
            {loading ? <CircularProgress size={18} color="inherit" /> : 'Buscar'}
          </Button>
        </Box>

        {error && <Alert severity="warning" sx={{ mb: 1 }}>{error}</Alert>}

        {result && (
          <>
            <Box sx={{ display: 'flex', gap: 1, mb: 1.5, flexWrap: 'wrap' }}>
              <Chip size="small" label={`Cliente: ${result.cliente_id}`} color="primary" variant="outlined" />
              <Chip size="small" label={`Cluster ${result.cluster}`} color="secondary" variant="outlined" />
              <Chip size="small" label={`${result.recommendations.length} recomendaciones`} color="success" variant="outlined" />
            </Box>
            <RecommendationTable rows={result.recommendations} columns={columns} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ProductSearch({ disabled }) {
  const [productId, setProductId] = useState('');
  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);

  const handleSearch = async () => {
    if (!productId.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    const data = await fetchRecommendationsForProduct(productId.trim());
    if (!data) {
      setError(`Producto "${productId}" no encontrado en la base de co-ocurrencias.`);
    } else {
      setResult(data);
    }
    setLoading(false);
  };

  const columns = [
    { key: 'producto_id', label: 'Producto ID' },
    { key: 'confidence',  label: 'Confianza', format: (v) => (v * 100).toFixed(2) + '%' },
    { key: 'support',     label: 'Soporte' },
  ];

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <ShoppingCartIcon color="secondary" />
          <Typography variant="subtitle2" fontWeight={700}>
            Productos Similares (Co-ocurrencia)
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            size="small"
            label="ID de Producto"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !disabled && handleSearch()}
            disabled={disabled}
            sx={{ flexGrow: 1 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            color="secondary"
            onClick={handleSearch}
            disabled={disabled || loading || !productId.trim()}
            sx={{ borderRadius: 2, minWidth: 80 }}
          >
            {loading ? <CircularProgress size={18} color="inherit" /> : 'Buscar'}
          </Button>
        </Box>

        {error && <Alert severity="warning" sx={{ mb: 1 }}>{error}</Alert>}

        {result && (
          <>
            <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
              <Chip size="small" label={`Producto: ${result.producto_id}`} color="secondary" variant="outlined" />
              <Chip size="small" label={`${result.similar_products.length} productos similares`} color="success" variant="outlined" />
            </Box>
            <RecommendationTable rows={result.similar_products} columns={columns} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function RecomendadorSection({ jobStatus }) {
  const [recInfo,    setRecInfo]    = useState(null);   // {cached, kmeans_ready, precision_at_10, ...}
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading,    setLoading]    = useState(false);

  const recJob = jobStatus?.Recomendador;

  const loadStatus = useCallback(async () => {
    const st = await fetchRecommenderStatus();
    if (st) setRecInfo(st);
  }, []);

  useEffect(() => {
    loadStatus();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (recJob?.status === 'completed') {
      loadStatus().then(() => setRefreshKey((k) => k + 1));
    }
  }, [recJob?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = async () => {
    setLoading(true);
    await triggerRecommender();
    setLoading(false);
  };

  const isRunning  = recJob?.status === 'running' || loading;
  const hasCached  = recInfo?.cached;
  const kmeansReady = recInfo?.kmeans_ready;

  return (
    <Container maxWidth="xl">
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <RecommendIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight={700}>
          Recomendador de Productos
        </Typography>
        {recJob && <StatusBadge status={recJob.status} />}
      </Box>

      {/* Chips de estado */}
      <Box sx={{ display: 'flex', gap: 1.5, mb: 3, flexWrap: 'wrap' }}>
        {hasCached && recInfo.num_customers && (
          <Chip
            label={`${recInfo.num_customers.toLocaleString('es-CO')} clientes con recomendaciones`}
            color="success"
            variant="outlined"
          />
        )}
        {!kmeansReady && (
          <Chip label="K-Means requerido" color="warning" variant="outlined" />
        )}
      </Box>

      {/* Botón de ejecución */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          startIcon={isRunning ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />}
          disabled={isRunning || !kmeansReady}
          onClick={handleRun}
          sx={{ px: 3, borderRadius: 2 }}
        >
          {isRunning
            ? 'Ejecutando Recomendador...'
            : hasCached
              ? 'Re-ejecutar Recomendador'
              : 'Ejecutar Recomendador'}
        </Button>
        {!kmeansReady && (
          <Typography variant="caption" color="warning.main" sx={{ ml: 2 }}>
            Ejecuta K-Means primero para habilitar el recomendador.
          </Typography>
        )}
        {kmeansReady && !hasCached && !isRunning && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
            El análisis puede tardar varios minutos (PySpark).
          </Typography>
        )}
      </Box>

      {/* Alertas de estado */}
      {recJob?.status === 'failed' && (
        <Alert severity="error" sx={{ mb: 3 }}>
          El Recomendador falló: {recJob.message || 'Error desconocido.'}
        </Alert>
      )}

      {!hasCached && !isRunning && kmeansReady && (
        <Alert severity="info" sx={{ mb: 3 }}>
          No hay resultados. Haz click en &quot;Ejecutar Recomendador&quot; para generar las recomendaciones.
        </Alert>
      )}

      {isRunning && (
        <Alert severity="info" sx={{ mb: 3 }}>
          El Recomendador está corriendo en Spark. Los resultados aparecerán automáticamente al completar.
        </Alert>
      )}

      {/* Métricas de evaluación */}
      {hasCached && (
        <>
          <SectionTitle>Métricas de Evaluación (split temporal 80/20)</SectionTitle>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <MetricCard
                label="Precision@10"
                value={recInfo.precision_at_10}
                color="primary.main"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <MetricCard
                label="Recall@10"
                value={recInfo.recall_at_10}
                color="secondary.main"
              />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 3 }} />

          {/* Búsquedas interactivas */}
          <SectionTitle>Explorar Recomendaciones</SectionTitle>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, lg: 6 }}>
              <CustomerSearch disabled={!hasCached || isRunning} />
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <ProductSearch disabled={!hasCached || isRunning} />
            </Grid>
          </Grid>

          <Divider sx={{ mb: 3 }} />

          {/* Gráficas */}
          <SectionTitle>Visualizaciones del Recomendador</SectionTitle>

          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, mb: 2.5 }}>
            <PlotlyChart
              chartName="evaluation-metrics"
              minHeight={400}
              refreshKey={refreshKey}
              fetchFn={fetchRecommenderChart}
            />
          </Box>

          <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2, mb: 3 }}>
            <PlotlyChart
              chartName="top-products-heatmap"
              minHeight={420}
              refreshKey={refreshKey}
              fetchFn={fetchRecommenderChart}
            />
          </Box>

          <Typography variant="caption" color="text.disabled" display="block" align="center" sx={{ pb: 2 }}>
            Filtrado Colaborativo por Clusters · PySpark · Precision@10 & Recall@10 · Co-ocurrencia de productos
          </Typography>
        </>
      )}
    </Container>
  );
}
