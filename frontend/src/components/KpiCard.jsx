import { Card, CardContent, CircularProgress, Typography } from '@mui/material';

export default function KpiCard({ label, value, color = 'primary.main' }) {
  const formatted =
    value !== null && value !== undefined
      ? value.toLocaleString('es-CO')
      : null;

  return (
    <Card elevation={1} sx={{ borderRadius: 3, height: '100%' }}>
      <CardContent sx={{ textAlign: 'center', py: 3 }}>
        {formatted !== null ? (
          <Typography variant="h4" fontWeight={700} sx={{ color }}>
            {formatted}
          </Typography>
        ) : (
          <CircularProgress size={28} />
        )}
        <Typography
          variant="caption"
          display="block"
          color="text.secondary"
          sx={{ mt: 1, textTransform: 'uppercase', letterSpacing: '0.05em' }}
        >
          {label}
        </Typography>
      </CardContent>
    </Card>
  );
}
