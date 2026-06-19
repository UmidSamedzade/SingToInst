import sys
import queue
import numpy as np
from PySide6.QtCore import QThread, Signal
import sounddevice as sd

class AudioAnalyzer(QThread):
    # Signals for real-time UI updates
    note_started = Signal(int, str, float)  # midi_num, note_name, start_time
    note_updated = Signal(int, str, float, float)  # midi_num, note_name, start_time, duration
    note_ended = Signal(int, str, float, float)  # midi_num, note_name, start_time, duration
    level_updated = Signal(float)  # current RMS level (for volume meter)
    time_updated = Signal(float)  # current audio timestamp (for synced playhead)
    finished_recording = Signal()

    def __init__(self, device_id=None, samplerate=44100, blocksize=2048, silence_threshold=0.015, mode='new'):
        super().__init__()
        self.device_id = device_id
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.silence_threshold = silence_threshold
        self.mode = mode
        
        self.audio_queue = queue.Queue()
        self.is_running = False
        
        # Note tracking state
        self.current_midi = None
        self.current_note_name = None
        self.current_start_time = None
        
        # Debounce/smoothing buffer
        self.note_history = []
        self.history_len = 3

    def run(self):
        self.is_running = True
        self.audio_queue.queue.clear()
        
        # Clear note state
        self.current_midi = None
        self.current_note_name = None
        self.current_start_time = None
        self.note_history = []
        
        start_timestamp = 0.0
        time_per_block = self.blocksize / self.samplerate

        # sounddevice callback to capture microphone data
        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status warning: {status}", file=sys.stderr)
            self.audio_queue.put(indata.copy())

        # Start low-latency stream
        try:
            with sd.InputStream(
                device=self.device_id,
                channels=1,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                callback=callback
            ):
                while self.is_running:
                    try:
                        # Fetch next audio block (timeout to check for is_running flag)
                        block = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    # Process the block
                    signal = block[:, 0]
                    
                    # Compute RMS level and send to UI
                    rms = np.sqrt(np.mean(signal**2))
                    self.level_updated.emit(float(rms))

                    # Perform pitch detection based on mode
                    if self.mode == 'new':
                        f0 = self.detect_pitch_yin(signal, self.samplerate)
                    else:
                        f0 = self.detect_pitch(signal, self.samplerate)
                    midi_num, note_name = self.freq_to_note(f0)

                    # Debounce pitch changes (smooth out single-frame errors)
                    if midi_num is not None:
                        self.note_history.append(midi_num)
                    else:
                        self.note_history.append(-1) # -1 represents silence

                    if len(self.note_history) > self.history_len:
                        self.note_history.pop(0)

                    # Determine dominant note in recent history
                    dominant_midi = self.get_dominant_note()
                    
                    # Check state changes
                    elapsed_time = start_timestamp
                    
                    if dominant_midi != -1:
                        # We have an active note
                        note_name_dom = self.get_note_name(dominant_midi)
                        
                        if self.current_midi is None:
                            # Start new note
                            self.current_midi = dominant_midi
                            self.current_note_name = note_name_dom
                            self.current_start_time = elapsed_time
                            self.note_started.emit(self.current_midi, self.current_note_name, self.current_start_time)
                        elif self.current_midi != dominant_midi:
                            # Note changed: end old one and start new one
                            duration = elapsed_time - self.current_start_time
                            self.note_ended.emit(self.current_midi, self.current_note_name, self.current_start_time, duration)
                            
                            self.current_midi = dominant_midi
                            self.current_note_name = note_name_dom
                            self.current_start_time = elapsed_time
                            self.note_started.emit(self.current_midi, self.current_note_name, self.current_start_time)
                        else:
                            # Note continues: update duration
                            duration = (elapsed_time + time_per_block) - self.current_start_time
                            self.note_updated.emit(self.current_midi, self.current_note_name, self.current_start_time, duration)
                    else:
                        # Silence detected
                        if self.current_midi is not None:
                            # End active note
                            duration = elapsed_time - self.current_start_time
                            self.note_ended.emit(self.current_midi, self.current_note_name, self.current_start_time, duration)
                            self.current_midi = None
                            self.current_note_name = None
                            self.current_start_time = None

                    start_timestamp += time_per_block
                    self.time_updated.emit(start_timestamp)

        except Exception as e:
            print(f"Error in audio stream: {e}", file=sys.stderr)
        
        # End any final hanging notes
        if self.current_midi is not None:
            duration = start_timestamp - self.current_start_time
            self.note_ended.emit(self.current_midi, self.current_note_name, self.current_start_time, duration)
            
        self.is_running = False
        self.finished_recording.emit()

    def stop(self):
        self.is_running = False

    def get_dominant_note(self):
        """Finds the most frequent note in history. Returns -1 if mostly silence."""
        if not self.note_history:
            return -1
        # Count occurrences of notes in the debounce buffer
        vals, counts = np.unique(self.note_history, return_counts=True)
        dominant = vals[np.argmax(counts)]
        return dominant

    def detect_pitch(self, signal, fs, min_freq=70, max_freq=800):
        """Autocorrelation based pitch tracking method."""
        rms = np.sqrt(np.mean(signal**2))
        if rms < self.silence_threshold:
            return None

        # Zero-center
        signal = signal - np.mean(signal)

        # Autocorrelation
        corr = np.correlate(signal, signal, mode='full')
        corr = corr[len(corr)//2:]

        # Period search bounds (in samples)
        min_period = int(fs / max_freq)
        max_period = int(fs / min_freq)

        if min_period >= len(corr) or min_period >= max_period:
            return None

        search_area = corr[min_period:max_period]
        if len(search_area) == 0:
            return None

        peak_idx = np.argmax(search_area) + min_period

        # Check peak strength ratio relative to zero-lag correlation
        zero_lag = corr[0]
        if zero_lag > 0 and (corr[peak_idx] / zero_lag) > 0.35:
            # Interpolate peak for higher frequency resolution
            if 0 < peak_idx < len(corr) - 1:
                alpha = corr[peak_idx - 1]
                beta = corr[peak_idx]
                gamma = corr[peak_idx + 1]
                denom = (alpha - 2 * beta + gamma)
                if abs(denom) > 1e-5:
                    p = 0.5 * (alpha - gamma) / denom
                    return fs / (peak_idx + p)
            return fs / peak_idx
        return None

    def freq_to_note(self, freq):
        """Converts frequency to MIDI note number and string representation."""
        if freq is None or freq <= 0:
            return None, None
        midi_num = int(round(12 * np.log2(freq / 440.0) + 69))
        if 0 <= midi_num <= 127:
            return midi_num, self.get_note_name(midi_num)
        return None, None

    def get_note_name(self, midi_num):
        NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        note_name = NOTE_NAMES[midi_num % 12]
        octave = (midi_num // 12) - 1
        return f"{note_name}{octave}"

    def detect_pitch_yin(self, signal, fs, min_freq=70, max_freq=800, threshold=0.15):
        """YIN algorithm for highly accurate pitch detection."""
        rms = np.sqrt(np.mean(signal**2))
        if rms < self.silence_threshold:
            return None

        W = len(signal) // 2
        tau_max = int(fs / min_freq)
        tau_min = int(fs / max_freq)

        if tau_max >= W:
            tau_max = W - 1

        # 1. Difference function
        diff = np.zeros(tau_max)
        for tau in range(1, tau_max):
            diff[tau] = np.sum((signal[:W] - signal[tau:W+tau])**2)

        # 2. Cumulative mean normalized difference function
        running_sum = 0.0
        yin_buffer = np.ones(tau_max)
        for tau in range(1, tau_max):
            running_sum += diff[tau]
            if running_sum > 0:
                yin_buffer[tau] = diff[tau] / (running_sum / tau)
            else:
                yin_buffer[tau] = 1.0

        # 3. Absolute thresholding / Peak picking
        tau = -1
        for t in range(tau_min, tau_max):
            if yin_buffer[t] < threshold:
                tau = t
                break

        if tau == -1:
            if tau_min < tau_max:
                tau = np.argmin(yin_buffer[tau_min:tau_max]) + tau_min
            else:
                return None

        # 4. Parabolic interpolation
        if 0 < tau < tau_max - 1:
            alpha = yin_buffer[tau - 1]
            beta = yin_buffer[tau]
            gamma = yin_buffer[tau + 1]
            denom = (alpha - 2 * beta + gamma)
            if abs(denom) > 1e-5:
                p = 0.5 * (alpha - gamma) / denom
                best_tau = tau + p
            else:
                best_tau = tau
        else:
            best_tau = tau

        f0 = fs / best_tau

        # Check if periodicity is strong enough
        if yin_buffer[tau] < 0.45:
            return f0
        return None
