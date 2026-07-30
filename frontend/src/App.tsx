import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AppProvider } from './context/AppProvider'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { AttendancePage } from './pages/AttendancePage'
import { EmployeesPage } from './pages/EmployeesPage'
import { PayrollPage } from './pages/PayrollPage'
import { SalariesPage } from './pages/SalariesPage'
import { SalaryImportPage } from './pages/SalaryImportPage'
import { ReportsPage } from './pages/ReportsPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { AIInsightsPage } from './pages/AIInsightsPage'
import { SettingsPage } from './pages/SettingsPage'
import { DiagnosticsPage } from './pages/DiagnosticsPage'

import { useEffect } from 'react'
import { StartupScreen } from './components/StartupScreen'

export default function App() {
  useEffect(() => {
    // Maintain a persistent connection. When this tab closes, the backend detects the drop and shuts down.
    const evtSource = new EventSource('/api/v1/system/events')
    return () => evtSource.close()
  }, [])
  return (
    <StartupScreen>
      <AppProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/attendance" element={<AttendancePage />} />
              <Route path="/payroll" element={<PayrollPage />} />
              <Route path="/payroll/salaries" element={<SalariesPage />} />
              <Route path="/payroll/salaries/import" element={<SalaryImportPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/ai-insights" element={<AIInsightsPage />} />
              <Route path="/employees" element={<EmployeesPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/diagnostics" element={<DiagnosticsPage />} />
              
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" toastOptions={{ className: 'text-sm' }} />
      </AppProvider>
    </StartupScreen>
  )
}
