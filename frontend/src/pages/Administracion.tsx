import { useEffect, useState } from 'react'
import {
  getUsuarios,
  createUsuario,
  updateUsuario,
  deleteUsuario,
} from '../api/usuarios.api'
import { getRoles } from '../api/roles.api'
import type { Usuario, UsuarioCreate, UsuarioUpdate, Rol } from '../types'

interface FormState {
  nombre: string
  apellido: string
  email: string
  password: string
  id_rol: number | ''
}

const emptyForm: FormState = {
  nombre: '',
  apellido: '',
  email: '',
  password: '',
  id_rol: '',
}

export default function Administracion() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [roles, setRoles] = useState<Rol[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [refreshKey, setRefreshKey] = useState(0)
  const fetchData = () => setRefreshKey((k) => k + 1)

  useEffect(() => {
    let alive = true
    Promise.all([getUsuarios(), getRoles()])
      .then(([u, r]) => {
        if (!alive) return
        setUsuarios(u)
        setRoles(r)
        setLoading(false)
      })
      .catch(() => {
        if (!alive) return
        setError('No se pudieron cargar los datos')
        setLoading(false)
      })
    return () => { alive = false }
  }, [refreshKey])

  const openCreate = () => {
    setEditingId(null)
    setForm({ ...emptyForm, id_rol: roles[0]?.id_rol ?? '' })
    setFormError(null)
    setShowModal(true)
  }

  const openEdit = (u: Usuario) => {
    setEditingId(u.id_usuario)
    setForm({
      nombre: u.nombre,
      apellido: u.apellido,
      email: u.email,
      password: '',
      id_rol: '',
    })
    setFormError(null)
    setShowModal(true)
  }

  const handleSave = async () => {
    setFormError(null)
    setSaving(true)
    try {
      if (editingId) {
        const update: UsuarioUpdate = {
          nombre: form.nombre || undefined,
          apellido: form.apellido || undefined,
          email: form.email || undefined,
          password: form.password || undefined,
        }
        await updateUsuario(editingId, update)
      } else {
        if (!form.id_rol) {
          setFormError('Selecciona un rol')
          setSaving(false)
          return
        }
        const payload: UsuarioCreate = {
          nombre: form.nombre,
          apellido: form.apellido,
          email: form.email,
          password: form.password,
          id_rol: Number(form.id_rol),
        }
        await createUsuario(payload)
      }
      setShowModal(false)
      fetchData()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Error al guardar'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string, nombre: string) => {
    if (!confirm(`¿Desactivar al usuario ${nombre}?`)) return
    try {
      await deleteUsuario(id)
      fetchData()
    } catch {
      alert('No se pudo desactivar el usuario')
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Administración</h1>
          <p className="text-slate-500 text-sm mt-1">Gestión de usuarios del sistema</p>
        </div>
        <button
          onClick={openCreate}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          + Nuevo usuario
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="text-center py-10 text-slate-400 text-sm">Cargando...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Nombre</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Correo</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Rol</th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Estado</th>
                <th className="text-right px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {usuarios.map((u) => (
                <tr key={u.id_usuario} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3 font-medium text-slate-800">
                    {u.nombre} {u.apellido}
                  </td>
                  <td className="px-5 py-3 text-slate-500">{u.email}</td>
                  <td className="px-5 py-3">
                    <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 capitalize">
                      {u.nombre_rol}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${u.estado_registro ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400'}`}>
                      {u.estado_registro ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right space-x-3">
                    <button
                      onClick={() => openEdit(u)}
                      className="text-blue-600 hover:underline text-xs font-medium"
                    >
                      Editar
                    </button>
                    {u.estado_registro && (
                      <button
                        onClick={() => handleDelete(u.id_usuario, u.nombre)}
                        className="text-red-500 hover:underline text-xs font-medium"
                      >
                        Desactivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4">
              {editingId ? 'Editar usuario' : 'Nuevo usuario'}
            </h2>

            <div className="space-y-3">
              {[
                { label: 'Nombre', key: 'nombre' as const, type: 'text', required: true },
                { label: 'Apellido', key: 'apellido' as const, type: 'text', required: true },
                { label: 'Correo electrónico', key: 'email' as const, type: 'email', required: true },
                {
                  label: editingId ? 'Nueva contraseña (dejar vacío para mantener)' : 'Contraseña',
                  key: 'password' as const,
                  type: 'password',
                  required: !editingId,
                },
              ].map(({ label, key, type, required }) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
                  <input
                    type={type}
                    value={form[key] as string}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    required={required}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}

              {!editingId && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Rol</label>
                  <select
                    value={form.id_rol}
                    onChange={(e) => setForm((f) => ({ ...f, id_rol: Number(e.target.value) }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">— Seleccionar —</option>
                    {roles.map((r) => (
                      <option key={r.id_rol} value={r.id_rol}>
                        {r.nombre_rol}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {formError && (
              <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {formError}
              </div>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 rounded-lg transition-colors"
              >
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
