import axios, { AxiosError } from 'axios'
import type { ApiErrorBody } from '../types/api'

let backendPort: number | null = null;
let portPromise: Promise<number> | null = null;

async function getPort() {
  if (backendPort) return backendPort;
  if (!portPromise) {
    portPromise = new Promise(async (resolve) => {
      if (!(window as any).__TAURI_INTERNALS__) {
         resolve(0);
         return;
      }
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const poll = async () => {
          try {
             const port = await invoke<number>('get_backend_port');
             
             // Now wait for backend to be actually healthy
             try {
                const response = await fetch(`http://127.0.0.1:${port}/health`);
                if (response.ok) {
                   const healthData = await response.json();
                   console.log('✅ Backend Connected Successfully!');
                   console.table({
                       'Backend Port': healthData.port,
                       'Backend PID': healthData.pid,
                       'Backend Executable': healthData.executable,
                       'Database Path': healthData.database,
                       'Environment': healthData.environment,
                   });
                   backendPort = port;
                   resolve(port);
                   return;
                }
             } catch (e) {
                // Not healthy yet, keep polling
                console.log('Waiting for backend health check...');
             }
             
             setTimeout(poll, 1000);
          } catch (e) {
             setTimeout(poll, 500);
          }
        };
        poll();
      } catch (e) {
        resolve(0);
      }
    });
  }
  return portPromise;
}

export const api = axios.create({
  baseURL: '/api/v1',
})

api.interceptors.request.use(async (config) => {
  const port = await getPort();
  if (port > 0) {
    config.baseURL = `http://127.0.0.1:${port}/api/v1`;
  }
  return config;
});

export function getErrorMessage(error: unknown, fallback = 'Something went wrong') {
  if (axios.isAxiosError(error)) {
    const ax = error as AxiosError<ApiErrorBody>
    if (!ax.response && ax.message === 'Network Error') {
        return 'Unable to connect to the backend server. The service might be starting up or has stopped unexpectedly.'
    }
    return ax.response?.data?.error?.message || ax.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}
