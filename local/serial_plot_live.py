"""Visualizador en vivo de la señal EMG con filtros notch + bandpass.

Reemplaza al Serial Plotter de Arduino mostrando tres paneles simultáneos:
  1. Señal cruda (lo que ves hoy).
  2. Señal filtrada (notch 60 Hz + bandpass 20-450 Hz).
  3. Espectro FFT en vivo (para verificar que el pico de 60 Hz desaparece).

Uso:
    python serial_plot_live.py                    # auto-detecta puerto
    python serial_plot_live.py --puerto COM3
    python serial_plot_live.py --notch off        # desactiva el notch para comparar
    python serial_plot_live.py --bandpass off     # desactiva el bandpass

Requiere matplotlib. Si no está: pip install matplotlib
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from collections import deque

import numpy as np
import serial
import serial.tools.list_ports
from scipy.signal import butter, filtfilt, iirnotch

try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
except ImportError:
    print("[ERROR] matplotlib no está instalado. Ejecuta: pip install matplotlib")
    sys.exit(2)


BAUD_RATE = 115200
FS = 500.0  # Hz — debe coincidir con el firmware del Arduino
VENTANA_S = 4.0  # segundos visibles en pantalla
N_VENTANA = int(VENTANA_S * FS)


def detectar_puerto() -> str | None:
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if any(k in desc for k in ("arduino", "ch340", "cp210", "ftdi")):
            return p.device
    return None


class CapturaSerial(threading.Thread):
    """Hilo que lee del puerto serial y mete muestras en un buffer thread-safe."""

    def __init__(self, puerto: str, buffer: deque, lock: threading.Lock):
        super().__init__(daemon=True)
        self.puerto = puerto
        self.buffer = buffer
        self.lock = lock
        self.detener = threading.Event()
        self.ser: serial.Serial | None = None

    def run(self) -> None:
        try:
            self.ser = serial.Serial(self.puerto, BAUD_RATE, timeout=0.1)
        except serial.SerialException as exc:
            print(f"[ERROR] No se pudo abrir {self.puerto}: {exc}")
            return
        time.sleep(2.0)  # reset del Arduino
        self.ser.reset_input_buffer()

        while not self.detener.is_set():
            try:
                linea = self.ser.readline().decode("ascii", errors="ignore").strip()
            except serial.SerialException:
                break
            if "," in linea:
                partes = linea.split(",")
                if len(partes) >= 2:
                    try:
                        valor = float(partes[1])
                    except ValueError:
                        continue
                    with self.lock:
                        self.buffer.append(valor)
        if self.ser:
            self.ser.close()


def construir_filtros(usar_notch: bool, usar_bandpass: bool):
    """Devuelve función `filtrar(señal) -> señal_filtrada`."""
    notch_b, notch_a = iirnotch(60.0, Q=30, fs=FS)
    band_b, band_a = butter(4, [20, min(245, FS / 2 - 5)], btype="band", fs=FS)

    def filtrar(x: np.ndarray) -> np.ndarray:
        if len(x) < 30:  # filtfilt requiere suficiente data
            return x
        y = x.astype(np.float64)
        y = y - y.mean()  # quitar DC
        if usar_notch:
            y = filtfilt(notch_b, notch_a, y)
        if usar_bandpass:
            y = filtfilt(band_b, band_a, y)
        return y

    return filtrar


def fraccion_60hz(señal: np.ndarray) -> float:
    if len(señal) < 64:
        return 0.0
    s = señal - señal.mean()
    pwr = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(len(s), d=1.0 / FS)
    total = pwr.sum()
    if total == 0:
        return 0.0
    mask = (f >= 58) & (f <= 62)
    return float(pwr[mask].sum() / total)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument("--puerto", default=None)
    parser.add_argument("--notch", choices=["on", "off"], default="on")
    parser.add_argument("--bandpass", choices=["on", "off"], default="on")
    args = parser.parse_args()

    puerto = args.puerto or detectar_puerto()
    if not puerto:
        print("[ERROR] No se detectó Arduino. Usa --puerto COMx")
        return 2

    print(f"Conectando a {puerto} @ {BAUD_RATE} baud...")
    print(f"Notch 60 Hz: {args.notch.upper()} | Bandpass 20-245 Hz: {args.bandpass.upper()}")
    print("Cierra la ventana o presiona Ctrl+C para terminar.\n")

    buffer: deque = deque(maxlen=N_VENTANA)
    lock = threading.Lock()
    captura = CapturaSerial(puerto, buffer, lock)
    captura.start()

    filtrar = construir_filtros(args.notch == "on", args.bandpass == "on")

    fig, (ax_raw, ax_filt, ax_fft) = plt.subplots(3, 1, figsize=(11, 8))
    fig.canvas.manager.set_window_title("EMG Live — VigilanceAI")

    t_eje = np.linspace(-VENTANA_S, 0, N_VENTANA)
    line_raw, = ax_raw.plot(t_eje, np.zeros(N_VENTANA), lw=0.8, color="tab:blue")
    line_filt, = ax_filt.plot(t_eje, np.zeros(N_VENTANA), lw=0.8, color="tab:green")
    line_fft, = ax_fft.plot([], [], lw=0.8, color="tab:red")
    band_60, = ax_fft.plot([], [], lw=0.0, marker="o", color="black", markersize=4)

    ax_raw.set_title("Señal cruda (ADC)")
    ax_raw.set_ylabel("µV (cruda)")
    ax_raw.grid(alpha=0.3)

    ax_filt.set_title(f"Señal filtrada (notch={args.notch}, bandpass={args.bandpass})")
    ax_filt.set_ylabel("µV (filtrada)")
    ax_filt.set_xlabel("tiempo (s)")
    ax_filt.grid(alpha=0.3)

    ax_fft.set_title("Espectro FFT — pico en 60 Hz indica ruido de red")
    ax_fft.set_xlabel("Frecuencia (Hz)")
    ax_fft.set_ylabel("Potencia (log)")
    ax_fft.set_xlim(0, 250)
    ax_fft.set_yscale("log")
    ax_fft.grid(alpha=0.3, which="both")
    ax_fft.axvspan(58, 62, alpha=0.15, color="red", label="banda 60 Hz")
    ax_fft.legend(loc="upper right")

    info_text = ax_raw.text(
        0.02, 0.95, "", transform=ax_raw.transAxes, fontsize=9,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )

    def actualizar(_frame):
        with lock:
            datos = np.array(buffer, dtype=np.float64)
        if len(datos) < 50:
            return line_raw, line_filt, line_fft, band_60, info_text

        # Padding para mantener largo de ventana
        if len(datos) < N_VENTANA:
            datos_pad = np.concatenate([np.zeros(N_VENTANA - len(datos)), datos])
        else:
            datos_pad = datos[-N_VENTANA:]

        filtrada = filtrar(datos_pad)

        line_raw.set_ydata(datos_pad)
        line_filt.set_ydata(filtrada)

        margen_raw = max(50.0, np.std(datos_pad) * 4)
        ax_raw.set_ylim(datos_pad.mean() - margen_raw, datos_pad.mean() + margen_raw)

        margen_filt = max(20.0, np.std(filtrada) * 4)
        ax_filt.set_ylim(-margen_filt, margen_filt)

        # FFT
        s = filtrada - filtrada.mean()
        pwr = np.abs(np.fft.rfft(s)) ** 2
        f = np.fft.rfftfreq(len(s), d=1.0 / FS)
        line_fft.set_data(f, np.maximum(pwr, 1e-3))
        ax_fft.set_ylim(1e-1, max(1e2, pwr.max() * 2))

        # Indicador 60 Hz
        frac_raw = fraccion_60hz(datos_pad)
        frac_filt = fraccion_60hz(filtrada)
        rms_raw = float(np.std(datos_pad))
        rms_filt = float(np.std(filtrada))

        info_text.set_text(
            f"RMS cruda:    {rms_raw:7.1f}  µV\n"
            f"RMS filtrada: {rms_filt:7.1f}  µV\n"
            f"Pot. 60Hz cruda:    {frac_raw*100:5.1f} %\n"
            f"Pot. 60Hz filtrada: {frac_filt*100:5.1f} %"
        )

        return line_raw, line_filt, line_fft, band_60, info_text

    ani = FuncAnimation(fig, actualizar, interval=100, blit=False, cache_frame_data=False)

    try:
        plt.tight_layout()
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        captura.detener.set()
        captura.join(timeout=1.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
