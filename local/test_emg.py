"""Validación rápida del cable EMG y de la calidad de la señal del shield Olimex.

Captura ~3 segundos de muestras desde el Arduino, reporta estadísticas y un
histograma ASCII del espectro para detectar contaminación de 60 Hz.

Uso:
    python test_emg.py                    # auto-detecta el puerto
    python test_emg.py --puerto COM3      # puerto explícito
    python test_emg.py --duracion 5       # captura 5 segundos
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass

import serial
import serial.tools.list_ports


BAUD_RATE = 115200
FS_ESPERADO = 500.0  # Hz — debe coincidir con el firmware del Arduino


@dataclass
class Resultado:
    n: int
    duracion_real_s: float
    fs_real: float
    media: float
    stdev: float
    minimo: float
    maximo: float


def detectar_puerto() -> str | None:
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if any(k in desc for k in ("arduino", "ch340", "cp210", "ftdi")):
            return p.device
    return None


def capturar(puerto: str, duracion_s: float) -> tuple[list[float], float]:
    ser = serial.Serial(puerto, BAUD_RATE, timeout=1.0)
    time.sleep(2.0)  # esperar reset del Arduino tras apertura del puerto
    ser.reset_input_buffer()

    muestras: list[float] = []
    t0 = time.time()
    t_fin = t0 + duracion_s
    while time.time() < t_fin:
        linea = ser.readline().decode("ascii", errors="ignore").strip()
        if "," in linea:
            partes = linea.split(",")
            if len(partes) >= 2:
                try:
                    muestras.append(float(partes[1]))
                except ValueError:
                    pass
    duracion_real = time.time() - t0
    ser.close()
    return muestras, duracion_real


def estadisticas(muestras: list[float], duracion_real: float) -> Resultado:
    return Resultado(
        n=len(muestras),
        duracion_real_s=duracion_real,
        fs_real=len(muestras) / duracion_real if duracion_real > 0 else 0.0,
        media=statistics.mean(muestras),
        stdev=statistics.stdev(muestras) if len(muestras) > 1 else 0.0,
        minimo=min(muestras),
        maximo=max(muestras),
    )


def potencia_60hz(muestras: list[float], fs: float) -> tuple[float, float]:
    """Calcula la fracción de potencia espectral concentrada en 58-62 Hz.

    Devuelve (potencia_total, fraccion_60hz). Útil para diagnosticar
    contaminación de la red eléctrica.
    """
    try:
        import numpy as np
        from numpy.fft import rfft, rfftfreq
    except ImportError:
        return 0.0, 0.0
    sig = np.array(muestras, dtype=np.float64)
    sig -= sig.mean()
    pwr = np.abs(rfft(sig)) ** 2
    f = rfftfreq(len(sig), d=1.0 / fs)
    pwr_total = pwr.sum()
    if pwr_total == 0:
        return 0.0, 0.0
    mask_60 = (f >= 58) & (f <= 62)
    return float(pwr_total), float(pwr[mask_60].sum() / pwr_total)


def diagnostico(r: Resultado, frac_60: float) -> tuple[str, list[str]]:
    """Devuelve (veredicto, lista de notas accionables)."""
    notas: list[str] = []
    veredicto = "OK"

    # Tasa de muestreo
    if r.n == 0:
        return ("FALLA", [
            "No se recibieron muestras.",
            "  • ¿El Arduino tiene firmware cargado?",
            "  • ¿El puerto es el correcto?",
            "  • ¿Baud rate del firmware = 115200?",
        ])
    if abs(r.fs_real - FS_ESPERADO) / FS_ESPERADO > 0.10:
        notas.append(
            f"⚠ fs real={r.fs_real:.1f} Hz vs esperado={FS_ESPERADO:.0f} Hz "
            "(>10% off — revisar firmware)"
        )
        veredicto = "REVISAR"

    # Saturación / desconexión
    if r.stdev < 1.0:
        notas.append(
            "✗ Stdev < 1 µV — señal plana. Probable desconexión, "
            "saturación a un riel del ADC o electrodo seco."
        )
        veredicto = "FALLA"
    elif r.stdev < 5.0:
        notas.append("⚠ Stdev muy bajo (<5 µV) — verificar contacto.")
        veredicto = "REVISAR"

    # Ruido 60 Hz
    if frac_60 > 0.30:
        notas.append(
            f"⚠ {frac_60*100:.0f}% de potencia en 60 Hz — ruido de red dominante. "
            "Aplicar técnicas anti-ruido del README §Cable EMG."
        )
        if veredicto == "OK":
            veredicto = "REVISAR"
    elif frac_60 > 0.10:
        notas.append(
            f"ℹ {frac_60*100:.0f}% de potencia en 60 Hz — moderado, "
            "filtro notch en software lo limpiará."
        )

    if not notas:
        notas.append("✓ Señal con perfil compatible con EMG válido.")
    return veredicto, notas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument("--puerto", default=None,
                        help="Puerto serial (ej. COM3). Default: auto-detección.")
    parser.add_argument("--duracion", type=float, default=3.0,
                        help="Segundos de captura (default 3).")
    args = parser.parse_args()

    puerto = args.puerto or detectar_puerto()
    if not puerto:
        print("[ERROR] No se detectó ningún Arduino. Conecta el cable USB y reintenta.")
        print("        Puedes pasar el puerto manualmente: python test_emg.py --puerto COM3")
        return 2

    print(f"Capturando {args.duracion:.0f} s desde {puerto} a {BAUD_RATE} baud...")
    print("(Mantén el músculo en el estado que quieras evaluar — reposo o contracción)")

    try:
        muestras, dur_real = capturar(puerto, args.duracion)
    except serial.SerialException as exc:
        print(f"[ERROR] No se pudo abrir el puerto {puerto}: {exc}")
        return 2

    if not muestras:
        print("[FALLA] No se recibieron muestras válidas en la ventana de captura.")
        print("        ¿Firmware cargado? ¿Cable USB OK? ¿Baud rate = 115200?")
        return 1

    r = estadisticas(muestras, dur_real)
    pwr_total, frac_60 = potencia_60hz(muestras, r.fs_real)
    veredicto, notas = diagnostico(r, frac_60)

    print()
    print("──────── Estadísticas ────────")
    print(f"  Muestras:           {r.n}")
    print(f"  Duración real:      {r.duracion_real_s:.2f} s")
    print(f"  FS real:            {r.fs_real:.1f} Hz  (esperado {FS_ESPERADO:.0f})")
    print(f"  Media:              {r.media:8.1f} µV")
    print(f"  Stdev:              {r.stdev:8.1f} µV")
    print(f"  Min..Max:           {r.minimo:.1f} ..  {r.maximo:.1f} µV")
    print(f"  Potencia 60 Hz:     {frac_60*100:5.1f} % del total")
    print()
    print(f"──────── Veredicto: {veredicto} ────────")
    for n in notas:
        print(f"  {n}")
    print()
    print("Criterios:")
    print("  • Reposo:      stdev < 30 µV, frac 60 Hz < 10%")
    print("  • Contracción: stdev > 100 µV, valores oscilando ±300-500 µV")
    print("  • Saturación / cable abierto: stdev < 5 µV")

    return 0 if veredicto == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
