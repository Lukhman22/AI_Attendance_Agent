import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Loader2 } from 'lucide-react';

export function StartupScreen({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<'initializing' | 'waiting' | 'ready' | 'error'>('initializing');
  const [logPath, setLogPath] = useState<string>('');

  useEffect(() => {
    let mounted = true;
    
    // Attempt to grab the backend log path early for debugging
    invoke<string>('get_backend_log_path').then(path => {
      if (mounted) setLogPath(path);
    }).catch(() => {});

    if (!(window as any).__TAURI_INTERNALS__) {
      // Running in browser, skip healthcheck block
      setStatus('ready');
      return;
    }

    const checkHealth = async () => {
      try {
        const port = await invoke<number>('get_backend_port');
        try {
          const res = await fetch(`http://127.0.0.1:${port}/health`);
          if (res.ok) {
            if (mounted) setStatus('ready');
            return true;
          }
        } catch (e) {
          // fetch failed, backend not up yet
        }
      } catch (e) {
         // port not available yet
      }
      return false;
    };

    let attempts = 0;
    const poll = async () => {
      if (!mounted) return;
      attempts++;
      
      if (attempts > 5) {
        setStatus('waiting');
      }

      const isReady = await checkHealth();
      if (!isReady && mounted) {
        setTimeout(poll, 1000);
      }
    };

    poll();
    
    return () => { mounted = false };
  }, []);

  if (status === 'ready') {
    return <>{children}</>;
  }

  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center bg-ink-50 dark:bg-ink-950 text-ink-900 dark:text-ink-50">
      <div className="flex flex-col items-center max-w-md text-center">
        <Loader2 className="w-12 h-12 text-brand-600 animate-spin mb-6" />
        <h1 className="text-2xl font-bold font-display mb-2">Starting Application</h1>
        <p className="text-ink-600 dark:text-ink-400 mb-8">
          {status === 'initializing' 
            ? 'Initializing local environment...' 
            : 'Waiting for local backend service to become ready...'}
        </p>

        {status === 'waiting' && logPath && (
          <div className="text-sm p-4 bg-ink-100 dark:bg-ink-900 rounded-lg text-left w-full border border-ink-200 dark:border-ink-800">
            <p className="font-semibold mb-1 text-ink-700 dark:text-ink-300">Taking longer than expected?</p>
            <p className="text-ink-500 dark:text-ink-500 mb-3">If the application does not start, inspect the startup logs:</p>
            <code className="block p-2 bg-ink-950 text-ink-200 rounded break-all select-all text-xs">
              {logPath}
            </code>
          </div>
        )}
      </div>
    </div>
  );
}
