# Tutorial React para defensa de tesis

> Objetivo: que puedas leer, modificar y **reescribir desde cero** los componentes de tu propia tesis. No es un curso completo de React — es lo mínimo que tu proyecto usa, en orden de importancia.

---

## 0. Mentalidad correcta antes de empezar

Tú vienes de **jQuery + AJAX**. Tu cerebro funciona así:
1. La página carga → el HTML ya está.
2. Yo busco un elemento (`$('#x')`) y lo modifico (`.text(...)`, `.html(...)`).
3. Cuando llega un evento (click), yo busco otro elemento y lo modifico.
4. Si quiero datos, hago `$.ajax` y dentro del callback modifico el DOM.

**React invierte la lógica:** tú no tocas el DOM. Declaras "cómo se ve la página en función del estado". React se encarga de actualizar el DOM cuando el estado cambia.

Regla de oro:

> **Si un dato cambia y la pantalla debe reflejarlo → ese dato vive en `useState`.**
> **Si algo debe pasar al cargar la página → va dentro de `useEffect(() => {...}, [])`.**
> **Nunca hagas `document.getElementById(...)` ni mutes variables.**

Con esas tres ideas dominas el 80% de React.

---

## 1. Tu primer componente

Un componente es **una función que devuelve JSX** (HTML mezclado con JavaScript).

```tsx
function Saludo() {
  return <h1>Hola mundo</h1>;
}
```

Para usarlo, lo escribes como una etiqueta HTML:

```tsx
<Saludo />
```

**Reglas de los componentes:**
- El nombre debe empezar con **mayúscula** (`Saludo`, no `saludo`). Es la única forma en que React diferencia un componente de una etiqueta HTML normal.
- Solo puede devolver **un único elemento raíz**. Si necesitas devolver varios, los envuelves en un `<div>` o en un fragmento `<>...</>`.

```tsx
// Mal: dos elementos raíz
function Mal() {
  return <h1>Hola</h1><p>Mundo</p>;  // ERROR
}

// Bien: envuelto en fragmento
function Bien() {
  return <><h1>Hola</h1><p>Mundo</p></>;
}
```

---

## 2. JSX: HTML con esteroides

JSX se ve como HTML pero **es JavaScript**. Diferencias clave:

| HTML | JSX |
|---|---|
| `class="rojo"` | `className="rojo"` |
| `for="email"` | `htmlFor="email"` |
| `onclick="..."` | `onClick={...}` |
| `<input>` | `<input />` (autocerrado obligatorio) |
| Atributos en kebab-case | Atributos en camelCase |

**Insertar JavaScript dentro de JSX:** usa llaves `{}`.

```tsx
const nombre = "Jorge";
const edad = 23;

return (
  <div>
    <h1>Hola {nombre}</h1>
    <p>Tienes {edad} años</p>
    <p>El año que viene tendrás {edad + 1}</p>
  </div>
);
```

Lo que va dentro de `{}` debe ser una **expresión** (algo que produce un valor). No puede ser un `if` ni un `for`.

---

## 3. `useState`: el dato que cambia

`useState` es el reemplazo mental de "variables que cuando cambian, actualizan la UI".

```tsx
import { useState } from 'react';

function Contador() {
  const [n, setN] = useState(0);  // valor inicial: 0

  return (
    <div>
      <p>Has clickeado {n} veces</p>
      <button onClick={() => setN(n + 1)}>+1</button>
    </div>
  );
}
```

**Las dos reglas inviolables:**
1. **NUNCA modifiques la variable directamente.** `n = n + 1` no hace nada visible. Siempre `setN(...)`.
2. **NUNCA muteas objetos/arrays existentes.** Crea uno nuevo.

```tsx
// MAL — React no detecta el cambio
const [lista, setLista] = useState([1, 2, 3]);
lista.push(4);
setLista(lista);

// BIEN — array nuevo
setLista([...lista, 4]);
```

```tsx
// MAL
const [user, setUser] = useState({ nombre: 'Jorge', edad: 23 });
user.edad = 24;
setUser(user);

// BIEN
setUser({ ...user, edad: 24 });
```

**Mapeo desde jQuery:**

| jQuery | React |
|---|---|
| `$('#contador').text(n)` | `{n}` en JSX |
| `n++` y volver a pintar | `setN(n + 1)` |
| Variable global `let n = 0` | `const [n, setN] = useState(0)` |

---

## 4. Eventos

```tsx
function Boton() {
  const handleClick = () => {
    console.log('me clickearon');
  };

  return <button onClick={handleClick}>Click</button>;
}
```

O inline:

```tsx
<button onClick={() => console.log('hola')}>Click</button>
```

Eventos típicos: `onClick`, `onChange`, `onSubmit`, `onMouseEnter`, `onKeyDown`.

**`onChange` en inputs** es lo que más vas a usar en formularios:

```tsx
function Formulario() {
  const [email, setEmail] = useState('');

  return (
    <input
      type="email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
    />
  );
}
```

Esto se llama **input controlado**: el valor del input siempre refleja el estado. Es el patrón estándar.

---

## 5. Renderizado condicional

No hay `v-if` ni `*ngIf`. Usas JavaScript puro.

```tsx
function Saludo({ logueado }) {
  if (logueado) {
    return <h1>Bienvenido</h1>;
  }
  return <h1>Por favor inicia sesión</h1>;
}
```

Inline con operador ternario:

```tsx
return (
  <div>
    {logueado ? <h1>Bienvenido</h1> : <h1>Inicia sesión</h1>}
  </div>
);
```

Inline con `&&` (mostrar solo si es verdad):

```tsx
return (
  <div>
    {error && <p style={{ color: 'red' }}>{error}</p>}
  </div>
);
```

---

## 6. Listas: `.map()`

Para renderizar una lista, usas `.map()` de JavaScript.

```tsx
function ListaEvaluaciones({ evaluaciones }) {
  return (
    <ul>
      {evaluaciones.map(e => (
        <li key={e.id}>{e.fecha} — {e.resultado}</li>
      ))}
    </ul>
  );
}
```

**`key` es OBLIGATORIO** en cada elemento de la lista. Debe ser único y estable. Casi siempre es el `id` del backend. **Nunca uses el índice** (`map((e, i) => ... key={i})`) si la lista puede reordenarse o cambiar.

---

## 7. `props`: pasar datos a un hijo

Los componentes reciben datos por **props** (parámetros de la función).

```tsx
function Saludo({ nombre, edad }) {
  return <p>Hola {nombre}, tienes {edad} años</p>;
}

// Uso
<Saludo nombre="Jorge" edad={23} />
```

Las props son **read-only**: el hijo no puede modificarlas. Si necesita avisar al padre que algo cambió, el padre le pasa una **función callback** como prop:

```tsx
function Boton({ onClick, texto }) {
  return <button onClick={onClick}>{texto}</button>;
}

function Padre() {
  const [n, setN] = useState(0);
  return (
    <>
      <p>{n}</p>
      <Boton texto="+1" onClick={() => setN(n + 1)} />
    </>
  );
}
```

Patrón mental: **props bajan, eventos suben.**

---

## 8. `useEffect`: cosas que pasan en el ciclo de vida

`useEffect` ejecuta código en respuesta a cambios. Es el reemplazo de:
- `$(document).ready(...)` → `useEffect(() => {...}, [])`
- "Ejecuta esto cuando cambie X" → `useEffect(() => {...}, [x])`

```tsx
import { useEffect, useState } from 'react';

function ListaEvaluaciones() {
  const [datos, setDatos] = useState([]);

  useEffect(() => {
    // Esto se ejecuta UNA VEZ cuando el componente se monta
    fetch('/api/evaluaciones')
      .then(r => r.json())
      .then(setDatos);
  }, []);  // <-- array de dependencias vacío = "solo al montar"

  return (
    <ul>
      {datos.map(e => <li key={e.id}>{e.fecha}</li>)}
    </ul>
  );
}
```

**El array de dependencias es la regla más importante de `useEffect`:**
- `[]` → corre una sola vez al montar el componente.
- `[x]` → corre al montar, y cada vez que `x` cambie.
- (sin array) → corre en CADA render. **Casi nunca quieres esto** — causa loops infinitos si dentro haces `setX`.

---

## 9. TypeScript en 5 minutos (porque tu proyecto usa `.tsx`)

TypeScript es JavaScript con tipos. Te avisa errores antes de ejecutar.

```tsx
// Tipo de un objeto
type Evaluacion = {
  id: number;
  fecha: string;
  resultado: 'APTO' | 'NO_APTO';
  p_total: number;
};

// Variable tipada
const e: Evaluacion = { id: 1, fecha: '2026-05-10', resultado: 'APTO', p_total: 0.3 };

// useState tipado
const [datos, setDatos] = useState<Evaluacion[]>([]);

// Props tipadas
type Props = {
  evaluacion: Evaluacion;
  onEliminar: (id: number) => void;
};

function Item({ evaluacion, onEliminar }: Props) {
  return (
    <li>
      {evaluacion.fecha}
      <button onClick={() => onEliminar(evaluacion.id)}>Eliminar</button>
    </li>
  );
}
```

Tipos comunes:
- `string`, `number`, `boolean`
- `string[]` (array de strings), `Evaluacion[]`
- `string | null` (uno u otro)
- `'APTO' | 'NO_APTO'` (literal — solo esos valores)
- `() => void` (función sin parámetros que no devuelve nada)
- `(id: number) => Promise<void>` (función async que recibe un id)

---

## 10. La plantilla universal (memorízala)

Esta plantilla cubre el 80% de las páginas de tu tesis.

```tsx
import { useEffect, useState } from 'react';
import { miApi } from '../api/mi.api';

type Item = {
  id: number;
  nombre: string;
};

export default function MiPagina() {
  const [items, setItems] = useState<Item[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCargando(true);
    miApi.listar()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, []);

  if (cargando) return <p>Cargando...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;

  return (
    <div>
      <h1>Mi página</h1>
      <ul>
        {items.map(i => (
          <li key={i.id}>{i.nombre}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## 11. Llamadas al backend (axios)

Tu proyecto usa axios. El patrón es:

```ts
// frontend/src/api/evaluacion.api.ts
import axios from 'axios';

const API = 'http://localhost:8000';

export const evaluacionApi = {
  listar: async (): Promise<Evaluacion[]> => {
    const res = await axios.get(`${API}/evaluaciones`);
    return res.data.data;  // <-- ojo: envelope ApiResponse
  },

  crear: async (datos: NuevaEvaluacion): Promise<Evaluacion> => {
    const res = await axios.post(`${API}/evaluaciones`, datos);
    return res.data.data;
  },
};
```

**Importante en tu proyecto:** todas las respuestas vienen envueltas en `{status, message, data}`. Por eso desempacas con `.data.data` (el primer `.data` es de axios, el segundo es del envelope).

Uso desde un componente:

```tsx
useEffect(() => {
  evaluacionApi.listar().then(setEvaluaciones);
}, []);
```

---

## 12. Formularios completos

```tsx
function FormularioCalibracion() {
  const [duracion, setDuracion] = useState(30);
  const [camara, setCamara] = useState(0);
  const [enviando, setEnviando] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();  // evita el reload del browser
    setEnviando(true);
    try {
      await calibracionApi.iniciar({ duracion, camara });
      alert('Calibración exitosa');
    } catch (err) {
      alert('Error: ' + (err as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Duración (s):
        <input
          type="number"
          value={duracion}
          onChange={(e) => setDuracion(Number(e.target.value))}
        />
      </label>
      <label>
        Índice de cámara:
        <input
          type="number"
          value={camara}
          onChange={(e) => setCamara(Number(e.target.value))}
        />
      </label>
      <button type="submit" disabled={enviando}>
        {enviando ? 'Enviando...' : 'Iniciar calibración'}
      </button>
    </form>
  );
}
```

---

## 13. Routing (react-router-dom)

Tu proyecto usa rutas. El patrón:

```tsx
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import Calibracion from './pages/Calibracion';
import Evaluaciones from './pages/Evaluaciones';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/calibracion" element={<Calibracion />} />
        <Route path="/evaluaciones" element={<Evaluaciones />} />
        <Route path="/evaluaciones/:id" element={<EvaluacionDetalle />} />
      </Routes>
    </BrowserRouter>
  );
}
```

Para navegar programáticamente:

```tsx
import { useNavigate } from 'react-router-dom';

function MiComponente() {
  const navigate = useNavigate();
  return <button onClick={() => navigate('/evaluaciones')}>Ver evaluaciones</button>;
}
```

Para leer parámetros de la URL (`/evaluaciones/:id`):

```tsx
import { useParams } from 'react-router-dom';

function EvaluacionDetalle() {
  const { id } = useParams<{ id: string }>();
  // ahora id es "1", "42", etc. (string)
}
```

---

## 14. Errores que vas a cometer (anticípalos)

1. **Olvidar `key` en `.map()`** → React te grita en consola.
2. **Mutar estado en lugar de crear nuevo** → la UI no se actualiza. Siempre `[...arr, x]` y `{...obj, k: v}`.
3. **`useEffect` sin dependencias correctas** → loop infinito si dentro haces `setX(...)` y `x` no está en el array.
4. **Llamar a un hook dentro de un `if`** → PROHIBIDO. Los hooks (`useState`, `useEffect`) van siempre al inicio del componente, sin condicionales.
5. **Pensar en términos de DOM** ("voy a agregar un `<li>` al `<ul>`"). NO. Cambias el array en el estado y dejas que React renderee.

---

## 15. Plan de práctica para 7 días (defensa)

| Día | Qué haces | Tiempo |
|---|---|---|
| 1 | Lees este tutorial completo + tutorial oficial de react.dev (Tic-Tac-Toe) | 3h |
| 2 | Abres `frontend/src/pages/Calibracion.tsx` y comentas línea por línea en un cuaderno | 2h |
| 3 | Borras `Calibracion.tsx` y lo reescribes mirando el tutorial. Que funcione. | 3h |
| 4 | Lo reescribes de nuevo SIN mirar nada. 2 veces. | 2h |
| 5 | Lo mismo con un componente más simple (ej. `Login.tsx`) | 2h |
| 6 | Practicas modificaciones en vivo: "agrega un campo", "cambia el título", "agrega validación" | 2h |
| 7 | Práctica oral: explicas en voz alta qué hace cada línea mientras tipeas | 2h |

Si haces esto, no hay jurado que te tumbe.

---

## 16. Frases para defenderte si el jurado se pasa

> "Reescribir un componente de UI desde cero en 5 minutos es un ejercicio de memoria, no de evaluación de ingeniería. Puedo explicar la arquitectura, modificar lógica, y reescribir con tiempo razonable."

> "El alcance del proyecto es la integración multimodal de los tres módulos. La capa de UI es un cliente del backend; lo importante es que la API funciona y los flujos están demostrados."

> "Si me permite 10 minutos, lo reescribo. El patrón es el mismo que [otro componente que ya saben que existe]."

---

## 17. Cheatsheet final (imprime esta sección)

```tsx
// IMPORTS
import { useState, useEffect } from 'react';

// COMPONENTE
function MiPagina() {
  // ESTADO
  const [datos, setDatos] = useState<Tipo[]>([]);
  const [cargando, setCargando] = useState(false);

  // EFECTO AL MONTAR
  useEffect(() => {
    fetch('/api/x').then(r => r.json()).then(setDatos);
  }, []);

  // MANEJADOR
  const handleClick = (id: number) => {
    setDatos(datos.filter(d => d.id !== id));
  };

  // RENDER CONDICIONAL
  if (cargando) return <p>Cargando...</p>;

  // RENDER
  return (
    <div>
      <h1>Título</h1>
      {datos.map(d => (
        <div key={d.id}>
          {d.nombre}
          <button onClick={() => handleClick(d.id)}>X</button>
        </div>
      ))}
    </div>
  );
}

export default MiPagina;
```

Memoriza esta estructura. Es **toda** la app.
