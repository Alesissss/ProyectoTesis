import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import EvaluacionAuto from './pages/EvaluacionAuto'
import EvaluacionDetalle from './pages/EvaluacionDetalle'
import MisEvaluaciones from './pages/MisEvaluaciones'
import Administracion from './pages/Administracion'
import Calibracion from './pages/Calibracion'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route
              path="/evaluaciones/iniciar"
              element={
                <ProtectedRoute requiredPermiso="evaluacion:registrar" />
              }
            >
              <Route index element={<EvaluacionAuto />} />
            </Route>
            <Route path="/evaluaciones/:id" element={<EvaluacionDetalle />} />
            <Route
              path="/calibracion"
              element={
                <ProtectedRoute requiredPermiso="baseline_somnolencia:registrar" />
              }
            >
              <Route index element={<Calibracion />} />
            </Route>
            <Route
              path="/evaluaciones"
              element={
                <ProtectedRoute requiredPermiso="evaluacion:ver_propias" />
              }
            >
              <Route index element={<MisEvaluaciones />} />
            </Route>
            <Route
              path="/administracion"
              element={
                <ProtectedRoute requiredPermiso="usuario:gestionar" />
              }
            >
              <Route index element={<Administracion />} />
            </Route>
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
