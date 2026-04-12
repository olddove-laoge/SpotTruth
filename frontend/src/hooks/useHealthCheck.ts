import { useEffect, useState } from 'react';
import { healthCheck, readyCheck } from '../services/api';

interface HealthStatus {
  isHealthy: boolean;
  isReady: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useHealthCheck(pollInterval = 30000) {
  const [status, setStatus] = useState<HealthStatus>({
    isHealthy: false,
    isReady: false,
    isLoading: true,
    error: null,
  });

  const checkHealth = async () => {
    try {
      setStatus((prev) => ({ ...prev, isLoading: true, error: null }));

      const [health, ready] = await Promise.all([healthCheck(), readyCheck()]);

      setStatus({
        isHealthy: health.status === 'ok',
        isReady: ready.status === 'ready',
        isLoading: false,
        error: null,
      });
    } catch (err) {
      setStatus({
        isHealthy: false,
        isReady: false,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Health check failed',
      });
    }
  };

  useEffect(() => {
    checkHealth();

    const interval = setInterval(checkHealth, pollInterval);
    return () => clearInterval(interval);
  }, [pollInterval]);

  return { ...status, recheck: checkHealth };
}
