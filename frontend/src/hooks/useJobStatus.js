import { useEffect, useRef, useState } from 'react';

const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
  .replace(/^http/, 'ws') + '/ws/jobs';

const RECONNECT_DELAY_MS = 3000;

export function useJobStatus() {
  const [jobs, setJobs] = useState({ ETL: null, KPIs: null });
  const wsRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (Array.isArray(data)) {
            // Historial inicial: tomar el más reciente por tipo
            const latest = {};
            for (const job of data) {
              if (!latest[job.job_type] || job.id > latest[job.job_type].id) {
                latest[job.job_type] = job;
              }
            }
            setJobs((prev) => ({
              ETL: latest['ETL'] ?? prev.ETL,
              KPIs: latest['KPIs'] ?? prev.KPIs,
            }));
          } else {
            // Update en tiempo real
            setJobs((prev) => ({ ...prev, [data.type]: data }));
          }
        } catch {
          // mensaje malformado — ignorar
        }
      };

      ws.onclose = () => {
        retryRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();
    return () => {
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, []);

  return jobs;
}
