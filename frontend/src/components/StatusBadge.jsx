import { Chip } from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';

const STATUS_MAP = {
  running:   { label: 'Ejecutando...', color: 'warning' },
  completed: { label: 'Completado',    color: 'success' },
  failed:    { label: 'Error',         color: 'error'   },
};

export default function StatusBadge({ status, size = 'small' }) {
  if (!status) return null;
  const { label, color } = STATUS_MAP[status] ?? { label: status, color: 'default' };
  return (
    <Chip
      size={size}
      label={label}
      color={color}
      icon={<CircleIcon sx={{ fontSize: '0.6rem !important' }} />}
      sx={{ fontWeight: 500 }}
    />
  );
}
