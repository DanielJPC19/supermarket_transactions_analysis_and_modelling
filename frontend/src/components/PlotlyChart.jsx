import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js/dist/plotly';
import { fetchChart } from '../api/analytics';

const PLOTLY_CONFIG = { responsive: true, displayModeBar: true, scrollZoom: false };

export default function PlotlyChart({ chartName, minHeight = 400, refreshKey }) {
  const divRef = useRef(null);
  const [fig, setFig] = useState(null);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    setFig(null);
    setStatus('loading');
    fetchChart(chartName).then((data) => {
      if (cancelled) return;
      if (!data) { setStatus('unavailable'); return; }
      try {
        const parsed = typeof data === 'string' ? JSON.parse(data) : data;
        setFig(parsed);
        setStatus('ready');
      } catch { setStatus('error'); }
    });
    return () => { cancelled = true; };
  }, [chartName, refreshKey]);

  useEffect(() => {
    if (!fig || !divRef.current) return;
    Plotly.newPlot(divRef.current, fig.data, { ...fig.layout, autosize: true }, PLOTLY_CONFIG);
    const node = divRef.current;
    return () => { Plotly.purge(node); };
  }, [fig]);

  if (status !== 'ready') {
    return (
      <div className="loading-placeholder" style={{ height: minHeight }}>
        {status === 'loading' && <span className="spinner-border text-primary" />}
        {status === 'unavailable' && (
          <span className="text-muted">Datos no disponibles aún. El cómputo puede tardar ~5 minutos.</span>
        )}
        {status === 'error' && (
          <span className="text-muted">Error al procesar el chart.</span>
        )}
      </div>
    );
  }

  return <div ref={divRef} style={{ width: '100%', minHeight }} />;
}
