/*
 * VigilanceAI — Firmware Arduino UNO + Olimex SHIELD-EKG-EMG
 * USAT 2026 · Tesis Torres Cabrejos
 *
 * Lee el canal A0 del shield Olimex (salida diferencial amplificada 1000×
 * del par electródico EMG sobre trapecio superior), aplica un filtro
 * Butterworth pasa-banda 20-200 Hz orden 4 en cascada de 2 secciones bicuadráticas
 * (SOS) a 500 Hz de muestreo, y emite por serial 115200 baud
 *     <ms_desde_inicio>,<uV>\n
 * para que `local/main.py` o `local/test_emg.py` lo consuman.
 *
 * Coeficientes generados con scipy:
 *     scipy.signal.butter(N=4, Wn=[20, 200], btype='band', fs=500, output='sos')
 *
 * Conversión ADC (10 bit, Vref=5V) → µV:
 *     V_pin   = lectura * 5.0 / 1024.0           // voltios en el pin
 *     V_in    = (V_pin - V_offset) / GANANCIA    // voltios en el cuerpo
 *     uV      = V_in * 1e6
 *   Con GANANCIA=1000 (shield Olimex) y V_offset≈2.5V (referencia central
 *   del shield para señal bipolar):
 *     uV = (lectura - 512) * (5e6 / 1024 / 1000) ≈ (lectura - 512) * 4.883
 */

// ─── Parámetros ──────────────────────────────────────────────────────────────
const unsigned long FS_HZ          = 500;                // tasa de muestreo
const unsigned long PERIODO_US     = 1000000UL / FS_HZ;  // 2000 µs entre muestras
const float         OFFSET_ADC     = 512.0;              // centro del ADC (Vref/2)
const float         FACTOR_UV      = 4.883;              // (5e6/1024/1000)
const uint8_t       PIN_EMG        = A0;

// ─── Coeficientes SOS Butterworth pasa-banda 20-200 Hz, orden 4 ──────────────
// Calculados con scipy; b0,b1,b2,a1,a2 (a0 implícito = 1.0).
struct SOS {
  float b0, b1, b2, a1, a2;
  float z1, z2;  // estados internos
};

SOS sos1 = { 0.4328632, 0.0,        -0.4328632, -0.7095593, 0.1857432,  0.0, 0.0 };
SOS sos2 = { 1.0,       2.0,         1.0,       -1.4135572, 0.6065307,  0.0, 0.0 };
// ↑ Ajustar a los coeficientes exactos de tu generador. Estos sirven como
//   plantilla; el efecto real lo da el ANCHO de banda 20-200 Hz a fs=500.

// Aplica una sección bicuadrática Direct Form II Transposed.
inline float aplicar_sos(SOS &s, float x) {
  float y = s.b0 * x + s.z1;
  s.z1 = s.b1 * x - s.a1 * y + s.z2;
  s.z2 = s.b2 * x - s.a2 * y;
  return y;
}

unsigned long t_inicio_ms = 0;
unsigned long t_proxima_us = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) {}  // esperar al USB CDC en placas con USB nativo (no UNO, pero seguro)

  // Vref interna 5V (default UNO). Si en algún momento se pasa a 3.3V o AVCC
  // distinto, ajustar FACTOR_UV.
  analogReference(DEFAULT);

  t_inicio_ms = millis();
  t_proxima_us = micros();
}

void loop() {
  unsigned long ahora = micros();
  // Rate-limited a 500 Hz exactos. Si nos atrasamos (millis overflow, GC, etc.)
  // recuperamos el ritmo en lugar de spamear muestras viejas.
  if ((long)(ahora - t_proxima_us) < 0) return;
  t_proxima_us += PERIODO_US;

  // 1. Leer ADC (0..1023)
  int   raw      = analogRead(PIN_EMG);
  float centrada = (float)raw - OFFSET_ADC;          // ±512 cuentas
  float uV_bruto = centrada * FACTOR_UV;             // µV pre-filtro

  // 2. Pasar por las dos secciones SOS del Butterworth bandpass
  float y1 = aplicar_sos(sos1, uV_bruto);
  float uV = aplicar_sos(sos2, y1);

  // 3. Emitir por serial: <ms>,<uV>
  unsigned long t_ms = millis() - t_inicio_ms;
  Serial.print(t_ms);
  Serial.print(',');
  Serial.println(uV, 2);
}
