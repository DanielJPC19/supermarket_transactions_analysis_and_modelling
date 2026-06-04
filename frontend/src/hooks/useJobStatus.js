import { useEffect, useRef, useState } from 'react';

const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
  .replace(/^http/, 'ws') + '/ws/jobs';

const RECONNECT_DELAY_MS = 3000;

export function useJobStatus() {
  const [jobStatus,      setJobStatus]      = useState({});
  const [lastSuccessful, setLastSuccessful] = useState({});
  const wsRef   = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (Array.isArray(data)) {
            // Historial inicial: extraer más reciente y último exitoso por tipo
            const latestByType = {};
            const lastSuccByType = {};
            for (const job of data) {
              if (!latestByType[job.job_type] || job.id > latestByType[job.job_type].id)
                latestByType[job.job_type] = job;
              if (job.status === 'completed')
                if (!lastSuccByType[job.job_type] || job.id > lastSuccByType[job.job_type].id)
                  lastSuccByType[job.job_type] = job;
            }
            setJobStatus(prev => ({ ...prev, ...latestByType }));
            setLastSuccessful(prev => ({ ...prev, ...lastSuccByType }));
          } else {
            // Update en tiempo real
            setJobStatus(prev => ({ ...prev, [data.type]: data }));
            if (data.status === 'completed')
              setLastSuccessful(prev => ({ ...prev, [data.type]: data }));
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

  return { jobStatus, lastSuccessful };
}
