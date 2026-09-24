"""Microphone input and whistle pitch detection.

  mic = Microphone()
  detector = PitchDetector()
  for samples in mic.read_available():
      db, peak_freq = detector.analyze(samples)   # peak_freq is None when no whistle
  mic.close()
"""

import numpy as np
import pyaudio

from config import CHUNK, F_MAX, F_MIN, RATE, WHISTLE_THRESHOLD_DB


class Microphone:
    """Mono 16-bit mic stream, read in frames of CHUNK samples."""

    def __init__(self, rate=RATE, chunk=CHUNK):
        self.rate = rate
        self.chunk = chunk
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(format=pyaudio.paInt16, channels=1, rate=rate,
                                        input=True, frames_per_buffer=chunk)

    def read_available(self):
        """Yield every frame waiting in the buffer so callers never fall behind.

        Blocks for one frame if none is waiting yet. Frames are float32 arrays.
        """
        available = max(self._stream.get_read_available() // self.chunk, 1)
        for _ in range(available):
            raw = self._stream.read(self.chunk, exception_on_overflow=False)
            yield np.frombuffer(raw, dtype=np.int16).astype(np.float32)

    def close(self):
        self._stream.stop_stream()
        self._stream.close()
        self._audio.terminate()


class PitchDetector:
    """Finds the loudest frequency in [f_min, f_max] and decides if it is a whistle."""

    def __init__(self, threshold=WHISTLE_THRESHOLD_DB, f_min=F_MIN, f_max=F_MAX, rate=RATE, chunk=CHUNK):
        self.threshold = threshold  # dB the peak must be above the band median
        freqs = np.fft.rfftfreq(chunk, 1 / rate)
        self.band = (freqs >= f_min) & (freqs <= f_max)
        self.band_freqs = freqs[self.band]
        self.window = np.hanning(chunk)

    def analyze(self, samples):
        """FFT one frame. Returns (db, peak_freq).

        db is the band spectrum in dB (one value per entry of band_freqs).
        peak_freq is the loudest frequency in Hz, or None if it isn't a whistle.
        """
        spectrum = np.abs(np.fft.rfft(samples * self.window))[self.band]
        db = 20 * np.log10(spectrum + 1e-9)

        peak_idx = int(np.argmax(db))
        is_whistle = db[peak_idx] - np.median(db) >= self.threshold
        peak_freq = float(self.band_freqs[peak_idx]) if is_whistle else None
        return db, peak_freq
