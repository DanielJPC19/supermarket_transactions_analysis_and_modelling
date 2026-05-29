import {
  Box, Chip, Divider, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Tooltip, Typography,
} from '@mui/material';
import StorageIcon from '@mui/icons-material/Storage';
import BarChartIcon from '@mui/icons-material/BarChart';
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot';
import RecommendIcon from '@mui/icons-material/Recommend';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StatusBadge from './StatusBadge';

export const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { id: 'etl',          label: 'ETL',           icon: <StorageIcon />,     enabled: true  },
  { id: 'eda',          label: 'EDA + KPIs',    icon: <BarChartIcon />,    enabled: true  },
  { id: 'kmeans',       label: 'K-Means',       icon: <ScatterPlotIcon />, enabled: false },
  { id: 'recomendador', label: 'Recomendador',  icon: <RecommendIcon />,   enabled: false },
];

export default function Sidebar({ activeSection, onNavChange, jobStatus, cacheWarm, onTriggerEtl }) {
  const etlStatus = jobStatus?.ETL?.status ?? null;
  const kpiStatus = jobStatus?.KPIs?.status ?? null;

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          bgcolor: '#1a1a2e',
          color: 'white',
          borderRight: 'none',
        },
      }}
    >
      {/* Header */}
      <Box sx={{ px: 2.5, py: 2.5 }}>
        <Typography variant="subtitle1" fontWeight={700} sx={{ color: 'white', letterSpacing: '0.02em' }}>
          Supermercado
        </Typography>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
          Analytics Platform
        </Typography>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />

      <List sx={{ px: 1, pt: 1, flexGrow: 1 }}>
        {NAV_ITEMS.map(({ id, label, icon, enabled }) => {
          const isActive = activeSection === id;
          const statusNode =
            id === 'etl' ? <StatusBadge status={etlStatus} /> :
            id === 'eda' ? (cacheWarm
              ? <Chip size="small" label="Listo" color="success" sx={{ fontWeight: 500 }} />
              : <Chip size="small" label="Computando" color="warning" sx={{ fontWeight: 500 }} />
            ) : null;

          return (
            <Tooltip
              key={id}
              title={enabled ? '' : 'Próximamente'}
              placement="right"
              disableHoverListener={enabled}
            >
              <span>
                <ListItemButton
                  disabled={!enabled}
                  selected={isActive}
                  onClick={() => enabled && onNavChange(id)}
                  sx={{
                    borderRadius: 2,
                    mb: 0.5,
                    color: enabled ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.3)',
                    '&.Mui-selected': {
                      bgcolor: 'rgba(255,255,255,0.12)',
                      color: 'white',
                    },
                    '&:hover': { bgcolor: 'rgba(255,255,255,0.08)' },
                    '&.Mui-disabled': { opacity: 0.4 },
                  }}
                >
                  <ListItemIcon sx={{ color: 'inherit', minWidth: 36 }}>{icon}</ListItemIcon>
                  <ListItemText
                    primary={label}
                    primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: isActive ? 600 : 400 }}
                  />
                  {!enabled && (
                    <Chip size="small" label="Soon" sx={{ fontSize: '0.65rem', height: 18, bgcolor: 'rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.5)' }} />
                  )}
                  {enabled && statusNode}
                </ListItemButton>
              </span>
            </Tooltip>
          );
        })}
      </List>

      {/* ETL trigger en la parte inferior de la sidebar cuando la sección activa es ETL */}
      {activeSection === 'etl' && (
        <>
          <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
          <Box sx={{ p: 2 }}>
            <IconButton
              onClick={onTriggerEtl}
              disabled={etlStatus === 'running'}
              size="small"
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                width: '100%',
                borderRadius: 2,
                py: 0.8,
                gap: 1,
                '&:hover': { bgcolor: 'primary.dark' },
                '&.Mui-disabled': { bgcolor: 'rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.3)' },
              }}
            >
              <PlayArrowIcon fontSize="small" />
              <Typography variant="caption" fontWeight={600}>
                {etlStatus === 'running' ? 'Ejecutando...' : 'Ejecutar ETL'}
              </Typography>
            </IconButton>
          </Box>
        </>
      )}
    </Drawer>
  );
}
