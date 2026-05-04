"""
Diagnóstico de cámara para el Módulo 1 (visión + rPPG) — VigilanceAI.

Qué hace:
  1. Escanea índices de VideoCapture 0..5 con backend DSHOW (Windows / USB).
  2. Para la cámara elegida, intenta varios modos (1920x1200@90, 1280x720@60,
     640x480@30, etc.) y reporta los que el driver acepta.
  3. Mide el FPS real observando frames durante ~5 s en el modo elegido.
  4. Muestra preview para que confirmes visualmente que es la AR0234.
  5. Imprime un veredicto:
       - ¿FPS real ≥ 30?     → mínimo aceptable para rPPG (HRV).
       - ¿FPS real ≥ 60?     → buena resolución temporal de RR.
       - ¿FPS real ≈ 90?     → óptimo para AR0234 (config actual del código).
     Y te indica si hay que ajustar CAM_FPS en m1_vision.py:69.

Uso (desde la carpeta local/):
    python diagnostico_camara.py                  # auto-escanea y usa la 1ª que abra
    python diagnostico_camara.py --index 1        # forzar índice
    python diagnostico_camara.py --no-preview     # sin ventana

Diagnóstico de FPS bajo (< 25 fps):
    # 1) Forzar formato MJPG (10x menos ancho de banda que YUY2 — clave en USB 2.0)
    python diagnostico_camara.py --index 1 --fourcc MJPG

    # 2) Forzar exposición manual corta (descarta problema de iluminación)
    #    Valores típicos en OpenCV/DSHOW: -6 = 1/64 s, -7 = 1/128 s, -8 = 1/256 s
    python diagnostico_camara.py --index 1 --fourcc MJPG --exposure -7

    # 3) Bajar resolución para descartar bottleneck de USB
    python diagnostico_camara.py --index 1 --fourcc MJPG --width 640 --height 480

Requisitos:
    pip install opencv-python  (ya está en requirements.txt)
"""
from __future__ import annotations

import argparse
import time

import cv2

# Mapa de backends de OpenCV.
# DSHOW (DirectShow) es el legacy de Windows; rápido para abrir pero suele
# ignorar CAP_PROP_FOURCC y deja todo en YUY2 (saturando USB 2.0).
# MSMF (Media Foundation) es el moderno; respeta MJPG y desbloquea fps altos.
BACKENDS = {
    "DSHOW": cv2.CAP_DSHOW,
    "MSMF":  cv2.CAP_MSMF,
    "ANY":   cv2.CAP_ANY,
}

# Modos a probar (W, H, fps). El driver UVC reportará si los soporta.
MODOS = [
    (1920, 1200, 90),   # AR0234 nativo, USB 3.0, máximo
    (1920, 1200, 60),
    (1920, 1200, 30),
    (1600, 1200, 90),   # 1200P 1:1 (lo que usa m1_vision.py hoy)
    (1280, 720,  90),
    (1280, 720,  60),
    (1280, 720,  30),
    (640,  480,  60),
    (640,  480,  30),
]

DURACION_MEDICION_S = 5.0


def escanear_indices(max_idx: int = 5,
                     backend: int = cv2.CAP_DSHOW,
                     backend_name: str = "DSHOW") -> list[int]:
    disponibles = []
    print(f"[1] Escaneando índices 0..{max_idx} con CAP_{backend_name}...")
    for i in range(max_idx + 1):
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                disponibles.append(i)
                print(f"    OK  índice {i}")
            else:
                print(f"    ??  índice {i} abre pero no entrega frames")
            cap.release()
        else:
            print(f"    --  índice {i} no abre")
    return disponibles


def probar_modos(idx: int, backend: int = cv2.CAP_DSHOW) -> list[tuple[int, int, float]]:
    print(f"\n[2] Probando modos en cámara {idx}...")
    aceptados = []
    for w, h, fps in MODOS:
        cap = cv2.VideoCapture(idx, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        cap.set(cv2.CAP_PROP_FPS, fps)
        rw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        rh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        rfps = cap.get(cv2.CAP_PROP_FPS)
        ret, _ = cap.read()
        cap.release()
        marca = "OK" if ret else "  "
        print(f"    [{marca}] solicitado {w}x{h}@{fps:>3} → driver reporta "
              f"{rw}x{rh}@{rfps:>5.1f}")
        if ret:
            aceptados.append((rw, rh, rfps))
    return aceptados


def medir_fps_real(idx: int, w: int, h: int, fps_solicitado: int,
                   mostrar_preview: bool = True,
                   fourcc: str | None = None,
                   exposure: float | None = None,
                   backend: int = cv2.CAP_DSHOW,
                   backend_name: str = "DSHOW") -> tuple[float, int]:
    print(f"\n[3] Midiendo FPS real durante {DURACION_MEDICION_S} s "
          f"con backend CAP_{backend_name} "
          f"a {w}x{h}@{fps_solicitado}"
          f"{' fourcc=' + fourcc if fourcc else ''}"
          f"{' exposure=' + str(exposure) if exposure is not None else ''}...")
    cap = cv2.VideoCapture(idx, backend)

    # Importante: el FOURCC debe fijarse ANTES que ancho/alto/fps,
    # porque cambiar de YUY2 a MJPG redefine los modos disponibles.
    if fourcc:
        code = cv2.VideoWriter_fourcc(*fourcc)
        cap.set(cv2.CAP_PROP_FOURCC, code)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, fps_solicitado)

    if exposure is not None:
        # Apagar auto-exposure (DSHOW: 0.25 = manual, 0.75 = auto)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure)

    # Reportar formato realmente activo
    real_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join(chr((real_fourcc >> 8 * i) & 0xFF) for i in range(4))
    print(f"    formato activo: {fourcc_str}")

    if not cap.isOpened():
        print("    !! cámara no abre")
        return 0.0, 0

    # Calentar (algunas cámaras tardan en estabilizar)
    for _ in range(10):
        cap.read()

    n_frames = 0
    t0 = time.time()
    while (time.time() - t0) < DURACION_MEDICION_S:
        ret, frame = cap.read()
        if not ret:
            break
        n_frames += 1
        if mostrar_preview:
            cv2.putText(frame, f"frame {n_frames}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("VigilanceAI — diagnostico (q para salir)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    elapsed = time.time() - t0
    cap.release()
    if mostrar_preview:
        cv2.destroyAllWindows()

    fps_real = n_frames / elapsed if elapsed > 0 else 0.0
    print(f"    capturados {n_frames} frames en {elapsed:.2f} s "
          f"→ FPS real = {fps_real:.2f}")
    return fps_real, n_frames


def veredicto(fps_real: float) -> None:
    print("\n[4] Veredicto:")
    if fps_real >= 75:
        print("    OPTIMO  ≥ 75 fps. Compatible con CAM_FPS=90 actual.")
        print("    Acción: ninguna. Puedes correr m1_vision.py tal cual.")
    elif fps_real >= 50:
        print("    BUENO   ≥ 50 fps. rPPG estable; HRV con buena resolución temporal.")
        print(f"    Acción: ajustar CAM_FPS en local/modules/m1_vision.py:69 "
              f"a {int(fps_real)}.")
    elif fps_real >= 25:
        print("    MINIMO  ≥ 25 fps. M1 (somnolencia) opera perfecto.")
        print("    rPPG funciona pero con resolución de RR limitada — los")
        print("    valores de HRV deben interpretarse como aproximados.")
        print(f"    Acción: ajustar CAM_FPS en m1_vision.py:69 a {int(fps_real)}.")
    else:
        print("    INSUFICIENTE  < 25 fps.")
        print("    Diagnóstico: probable USB 2.0, driver UVC genérico, o iluminación")
        print("    forzando exposición larga. Revisar puerto USB 3.0 azul, encender luz")
        print("    blanca, y reintentar.")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=int, default=None,
                   help="Índice de cámara (omitir para auto-escanear).")
    p.add_argument("--no-preview", action="store_true",
                   help="No mostrar ventana de preview.")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=60,
                   help="FPS a solicitar (la cámara puede caer a uno menor).")
    p.add_argument("--fourcc", type=str, default=None,
                   help="Formato de píxel: MJPG (recomendado en USB 2.0) o YUY2.")
    p.add_argument("--exposure", type=float, default=None,
                   help="Exposición manual (DSHOW: -6=1/64s, -7=1/128s, -8=1/256s). "
                        "Si se da, apaga auto-exposure.")
    p.add_argument("--backend", type=str, default="DSHOW",
                   choices=list(BACKENDS.keys()),
                   help="Backend de OpenCV. MSMF respeta MJPG; DSHOW suele ignorarlo.")
    args = p.parse_args()

    backend = BACKENDS[args.backend]
    backend_name = args.backend

    print("=" * 60)
    print("Diagnóstico cámara — VigilanceAI M1")
    print("=" * 60)

    if args.index is None:
        disponibles = escanear_indices(backend=backend, backend_name=backend_name)
        if not disponibles:
            print("\n!! No se detectó ninguna cámara con CAP_DSHOW.")
            print("   Verifica el cable USB y que ningún otro programa la esté usando.")
            return
        idx = disponibles[0]
        print(f"\nUsando cámara índice {idx} (la primera disponible).")
        print("Si no es la AR0234, vuelve a correr con --index N.")
    else:
        idx = args.index

    probar_modos(idx, backend=backend)

    fps_real, _ = medir_fps_real(
        idx, args.width, args.height, args.fps,
        mostrar_preview=not args.no_preview,
        fourcc=args.fourcc,
        exposure=args.exposure,
        backend=backend,
        backend_name=backend_name,
    )

    veredicto(fps_real)

    print("\n" + "=" * 60)
    print("Resumen para anotar en el informe:")
    print(f"   Cámara índice usada: {idx}")
    print(f"   Modo solicitado:     {args.width}x{args.height}@{args.fps}")
    print(f"   FPS real medido:     {fps_real:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
