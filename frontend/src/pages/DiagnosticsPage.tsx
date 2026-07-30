import { useEffect, useState } from 'react';
import { PageHeader, Card, Badge, Skeleton, Button } from '../components/ui';
import { systemApi } from '../services';
import { Activity, Server, Database, Code, RefreshCcw } from 'lucide-react';
import { getErrorMessage } from '../services/apiClient';
import toast from 'react-hot-toast';

interface HealthData {
  status: string;
  environment: string;
  pid: string;
  executable: string;
  database: string;
  port: string;
}

export function DiagnosticsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHealth = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const data = await systemApi.health();
      setHealth(data as unknown as HealthData);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to fetch system diagnostics'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void fetchHealth();
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between">
        <PageHeader title="System Diagnostics" subtitle="Check the application and database health" />
        <Button
          variant="secondary"
          onClick={() => fetchHealth(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCcw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {loading ? (
        <Skeleton className="h-64 mt-6" />
      ) : (
        <div className="mt-6 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {/* Main Status */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-brand-100 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400 rounded-lg">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-ink-900 dark:text-ink-50">System Status</h3>
                <p className="text-sm text-ink-500">Overall health</p>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-ink-50 dark:bg-ink-900/50 rounded border border-ink-200 dark:border-ink-800">
              <span className="text-sm font-medium">Backend Connectivity</span>
              {health ? (
                <Badge tone="green">Online</Badge>
              ) : (
                <Badge tone="rose">Offline</Badge>
              )}
            </div>
            <div className="flex items-center justify-between p-3 mt-2 bg-ink-50 dark:bg-ink-900/50 rounded border border-ink-200 dark:border-ink-800">
              <span className="text-sm font-medium">App Environment</span>
              <span className="text-sm">{health?.environment || 'Unknown'}</span>
            </div>
          </Card>

          {/* Database */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-ink-900 dark:text-ink-50">Database</h3>
                <p className="text-sm text-ink-500">SQLite Storage</p>
              </div>
            </div>
            
            <div className="p-3 bg-ink-50 dark:bg-ink-900/50 rounded border border-ink-200 dark:border-ink-800 overflow-hidden">
              <span className="text-xs font-medium text-ink-500 block mb-1">Path</span>
              <span className="text-sm font-mono break-all">{health?.database || 'Not connected'}</span>
            </div>
          </Card>

          {/* Backend Service */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 rounded-lg">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-ink-900 dark:text-ink-50">Backend Server</h3>
                <p className="text-sm text-ink-500">Sidecar process</p>
              </div>
            </div>
            
            <div className="grid gap-2">
              <div className="flex items-center justify-between p-2 text-sm bg-ink-50 dark:bg-ink-900/50 rounded border border-ink-200 dark:border-ink-800">
                <span className="text-ink-500">Port</span>
                <span className="font-mono">{health?.port || 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between p-2 text-sm bg-ink-50 dark:bg-ink-900/50 rounded border border-ink-200 dark:border-ink-800">
                <span className="text-ink-500">Process ID</span>
                <span className="font-mono">{health?.pid || 'N/A'}</span>
              </div>
              <div className="p-2 text-sm bg-ink-50 dark:bg-ink-900/50 rounded border border-ink-200 dark:border-ink-800 overflow-hidden">
                <span className="text-ink-500 block mb-1">Executable</span>
                <span className="font-mono text-xs break-all">{health?.executable || 'N/A'}</span>
              </div>
            </div>
          </Card>

          {/* About / Versions */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400 rounded-lg">
                <Code className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-ink-900 dark:text-ink-50">About Application</h3>
                <p className="text-sm text-ink-500">Version info</p>
              </div>
            </div>
            
            <div className="grid gap-2">
              <div className="flex items-center justify-between p-2 text-sm">
                <span className="font-medium text-ink-500">App Version</span>
                <span>1.0.0</span>
              </div>
              <div className="flex items-center justify-between p-2 text-sm">
                <span className="font-medium text-ink-500">Backend API</span>
                <span>v1</span>
              </div>
              <div className="flex items-center justify-between p-2 text-sm">
                <span className="font-medium text-ink-500">Build Date</span>
                <span>{new Date().toLocaleDateString()}</span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
