# Colocación de electrodos EMG — Guía SENIAM para fatiga muscular

> Estándar internacional citable: **SENIAM (Surface ElectroMyoGraphy for the Non-Invasive Assessment of Muscles)**, Hermens et al. 2000. Es lo que esperan ver los jurados.

---

## Decisión: ¿qué músculo elegir?

**Caso de uso del sistema:** evaluación de fatiga mental en personal de salud (cirujanos, médicos) **antes de ingresar al quirófano**, en formato de "peaje" — el sujeto se sienta frente a la cámara con los electrodos conectados durante ~30 segundos. **NO es conducción**, no hay movimiento sostenido, no se requiere activación voluntaria del músculo.

Para este caso de uso, el músculo de elección es el **trapecio superior**, sin duda.

### Por qué el trapecio (literatura específica)

El trapecio superior es el músculo más estudiado para **fatiga ocupacional por carga mental sostenida**, no por movimiento. Fenómenos relevantes:

- **"Cinderella hypothesis"** (Hägg, 1991): las fibras musculares de bajo umbral del trapecio permanecen activadas durante horas de tarea cognitiva sin oportunidad de descanso, acumulando fatiga medible incluso en reposo aparente.
- **Activación trapecio durante estrés mental** (Lundberg et al., 1994): el estrés mental induce actividad EMG sostenida del trapecio detectable sin contracción voluntaria.
- **Fatiga en trabajadores de pantalla / personal hospitalario** (Sjøgaard et al., 2000): mismo fenómeno aplicado a personal con jornadas largas frente a estaciones de trabajo.

**Manifestación medible en tu sistema:**
- **RMS-EMG elevado vs baseline personal** → tensión muscular residual.
- **MDF/MNF desplazado a frecuencias bajas** → fatiga del músculo (clásico marcador electrofisiológico).

El cirujano sentado quieto durante 30s frente a la cámara es exactamente el **escenario validado por esta literatura**, no una limitación del sistema.

### Tabla comparativa (descartados)

| Músculo | ¿Aplica a tu caso? | Razón |
|---|---|---|
| **Trapecio superior** | ✅ **SÍ** | Fatiga ocupacional / estrés mental sostenido, validado en personal médico y trabajo prolongado |
| Flexor carpi radialis (antebrazo) | ❌ No es óptimo | Su literatura es de manejo/agarre. En cirujano sentado sin actividad manual sostenida → poca señal útil |
| Extensor digitorum | ❌ No es óptimo | Mismo razonamiento que el anterior |

---

## Trapecio superior — ubicación SENIAM

### Anatomía de referencia

```
                    [oreja]
                       |
                       |
              C7 ●─────┼─────● Acromion
                       |       (punta del hombro)
                       |
                  [columna]
```

- **C7**: vértebra cervical 7. Es **la más prominente** que sientes al inclinar la cabeza hacia adelante. Pásate los dedos por la nuca hacia abajo — la última vértebra que destaca antes de que la espalda se aplane.
- **Acromion**: el punto óseo más alto del hombro. Sigue la clavícula desde el cuello hacia el hombro hasta llegar al final óseo.

### Ubicación de los electrodos

1. **Marca el punto medio** entre C7 y el acromion. Mídelo con regla o cinta métrica.
2. **Electrodo positivo (+)** y **electrodo negativo (−)** van **alineados sobre la línea C7-acromion**, separados **2 cm entre centros**, ambos centrados en el punto medio.
3. **Electrodo de referencia / DRL (blanco)** va sobre **hueso**: la mejor opción es directamente sobre **C7** o sobre el **acromion**. Hueso = poca actividad eléctrica = referencia limpia.

```
             C7 ●  ←  DRL (blanco) aquí
                 ╲
                  ╲
                   ●  ←  electrodo (+)
                   ●  ←  electrodo (−)   (separación 2 cm)
                  ╱
                 ╱
        ●Acromion
```

### Test de activación

Para confirmar que el electrodo está bien:
- **Encoge el hombro hacia la oreja** (eleva el hombro). Debes ver picos claros de actividad en el Serial Plotter.
- **Relaja completamente**. La señal debe bajar a línea base.
- **Repite 5 veces**. Si los picos son consistentes, está bien colocado.

---

## Flexor carpi radialis — alternativa (antebrazo)

Es lo que ya estuviste usando. Si te quedas con este:

### Ubicación

```
[Codo] ●──────────────────────● [Muñeca]
       <-- 1/3 de la longitud -->
                      ●  ←  electrodos aquí
                      ●     (cara palmar / interna)
       
       ●  ←  DRL aquí (sobre hueso del codo: epicóndilo medial)
```

1. Estira el brazo con la **palma hacia arriba**.
2. Mide la distancia entre el **pliegue del codo** y el **pliegue de la muñeca**.
3. Marca el punto a **1/3 desde el codo**.
4. Electrodos **(+) y (−)** sobre el vientre muscular, alineados con la fibra (paralelos al brazo), separación **2 cm**.
5. **DRL (blanco)** sobre el **epicóndilo medial** (hueso del codo, lado interno) o sobre la muñeca (hueso).

### Test de activación

- **Cierra el puño con fuerza** o **flexiona la muñeca hacia adentro**. Debe haber picos.
- Relaja → línea base.

---

## Procedimiento de colocación (CRÍTICO — lo más subestimado)

El **80% de los problemas de ruido EMG vienen de la preparación de la piel**, no del cable ni del Arduino.

### Materiales

- Alcohol isopropílico (70% mínimo).
- **Gel electrolítico/conductor** (NO gel de ducha, NO agua). Marca: Signa Gel, Spectra 360, o equivalente. En Lima/Chiclayo se consigue en tiendas médicas o farmacias grandes.
- Algodón o gasa.
- Cinta médica o esparadrapo.
- Electrodos pregelificados de Ag/AgCl (los desechables redondos blancos).

### Pasos

1. **Rasura** la zona si tiene vello (incluye trapecio en hombre adulto). El vello entre electrodo y piel = impedancia altísima.
2. **Limpia con alcohol** — frota fuerte 30 segundos. No es por higiene, es para **remover células muertas** que aíslan eléctricamente.
3. **Espera a que seque** (30 s). Piel mojada con alcohol ≠ piel preparada.
4. **Aplica una gota de gel electrolítico** sobre el electrodo (si no es pregelificado) o directamente sobre la piel.
5. **Pega los electrodos** con presión durante 10 segundos para asegurar contacto.
6. Refuerza con cinta médica si el electrodo se despega con el movimiento.

### Antes de cada prueba

- Verifica con multímetro o con el Serial Plotter que la **línea base está estable** durante 5 segundos sin contracción.
- Si la línea base oscila constantemente → mal contacto. Vuelve a empezar.

---

## Imágenes de referencia (descárgalas tú)

No puedo descargar imágenes con licencia desde aquí. Estas fuentes son **gratuitas y citables**:

1. **SENIAM oficial**: http://www.seniam.org/ — Sección "Sensor location" para cada músculo.
2. **Wikimedia Commons — Trapezius**: buscar "Trapezius muscle anatomy" en https://commons.wikimedia.org/ — todas las imágenes son licencia libre.
3. **Wikimedia Commons — Flexor carpi radialis**: misma búsqueda en Commons.
4. **Atlas de Gray's Anatomy**: dominio público completo, en Wikimedia.

Para tu informe de tesis: descárgalas, citas la fuente en pie de imagen, listo.

---

## Citas bibliográficas para el Pre Informe

**Procedimiento de colocación (estándar SENIAM):**
> Hermens HJ, Freriks B, Disselhorst-Klug C, Rau G. **Development of recommendations for SEMG sensors and sensor placement procedures.** *Journal of Electromyography and Kinesiology*. 2000;10(5):361-374.

**Justificación del trapecio para fatiga mental ocupacional:**
> Lundberg U, Kadefors R, Melin B, et al. **Psychophysiological stress and EMG activity of the trapezius muscle.** *International Journal of Behavioral Medicine*. 1994;1(4):354-370.

> Sjøgaard G, Lundberg U, Kadefors R. **The role of muscle activity and mental load in the development of pain and degenerative processes at the muscle cell level during computer work.** *European Journal of Applied Physiology*. 2000;83(2-3):99-105.

> Hägg GM. **Static work loads and occupational myalgia — a new explanation model.** En: Anderson PA, Hobart DJ, Danoff JV, eds. *Electromyographical Kinesiology*. Elsevier; 1991:141-144. (Cinderella hypothesis)

Estas tres referencias **blindan tu caso de uso** (cirujano sentado, sin movimiento, evaluación tipo peaje). La de Hermens es para el procedimiento técnico.

---

## Checklist antes de cada captura EMG (imprime)

- [ ] Piel limpia con alcohol y seca
- [ ] Gel electrolítico aplicado
- [ ] Electrodos pegados con presión 10s
- [ ] Cable apantallado conectado correctamente (positivo/negativo no invertidos)
- [ ] DRL (blanco) sobre hueso
- [ ] Línea base estable durante 5s sin contracción
- [ ] Test de contracción voluntaria genera picos visibles
- [ ] Laptop a batería O Arduino con barrel jack independiente (ver guía Arduino)
- [ ] Sin cargador, sin celular cerca, sin fluorescentes encima
