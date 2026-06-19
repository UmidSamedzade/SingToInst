import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QProgressBar,
    QFrame, QTabWidget, QFormLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon

import sounddevice as sd

from audio_analyzer import AudioAnalyzer
from timeline_widget import TimelineWidget

class SingToInstApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Internal State
        self.analyzer = None
        self.recognition_mode = 'new'  # default mode
        self.selected_input_device_id = sd.default.device[0]  # Default input
        self.selected_output_device_id = sd.default.device[1]  # Default output
        self.silence_threshold = 0.015
        
        # Playback Timer State
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.advance_playback)
        self.play_start_time = 0.0
        self.current_playhead = 0.0
        self.is_playing = False
        self.is_recording = False
        


        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SingToInst - Multi-Track Vocal Studio")
        self.resize(800, 600)
        self.setMinimumSize(700, 500)

        # Style sheet for dark mode with window tab styling matching aesthetics
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F0F11;
            }
            QWidget {
                color: #E2E8F0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #2D2D37;
                background-color: #0F0F11;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #1E1E24;
                border: 1px solid #2D2D37;
                border-bottom-color: transparent;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 20px;
                color: #94A3B8;
                font-size: 13px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #0F0F11;
                color: #F8FAFC;
                border-bottom: 2px solid #8B5CF6;
            }
            QTabBar::tab:hover {
                background-color: #2D2D37;
                color: #F8FAFC;
            }
            QFrame#ControlCard, QFrame#SettingsCard {
                background-color: #1E1E24;
                border-radius: 12px;
                border: 1px solid #2D2D37;
                padding: 16px;
            }
            QLabel#TitleLabel {
                font-size: 28px;
                font-weight: 800;
                color: #A78BFA;
            }
            QLabel#SubtitleLabel {
                font-size: 13px;
                color: #94A3B8;
            }
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: #F8FAFC;
                margin-bottom: 10px;
            }
            QPushButton#RecordButton {
                background-color: #EF4444;
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                min-height: 36px;
                padding: 0px 18px;
            }
            QPushButton#RecordButton:hover {
                background-color: #DC2626;
            }
            QPushButton#PlayButton {
                background-color: #10B981;
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                min-height: 36px;
                padding: 0px 18px;
            }
            QPushButton#PlayButton:hover {
                background-color: #059669;
            }
            QPushButton#ClearButton {
                background-color: #3F3F46;
                border: none;
                border-radius: 6px;
                color: #E2E8F0;
                font-weight: bold;
                font-size: 13px;
                min-height: 36px;
                padding: 0px 18px;
            }
            QPushButton#ClearButton:hover {
                background-color: #52525B;
            }
            QComboBox {
                background-color: #0F0F11;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 24px 6px 12px;
                color: #E2E8F0;
                font-size: 13px;
                min-height: 36px;
                min-width: 250px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E24;
                border: 1px solid #2D2D37;
                color: #E2E8F0;
                font-size: 13px;
                selection-background-color: #8B5CF6;
                selection-color: #FFFFFF;
                outline: 0px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #2D2D37;
                height: 6px;
                background: #0F0F11;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #8B5CF6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #A78BFA;
                border: 1px solid #8B5CF6;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QProgressBar#MicLevelBar {
                background-color: #0F0F11;
                border: 1px solid #2D2D37;
                border-radius: 4px;
                text-align: center;
                height: 10px;
            }
            QProgressBar#MicLevelBar::chunk {
                background-color: #10B981;
                border-radius: 3px;
            }
            QLabel#StatusLabel {
                font-size: 13px;
                color: #A1A1AA;
            }
        """)

        # Set up Tab System
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Tab 1: Studio Workspace
        self.studio_tab = QWidget()
        self.init_studio_tab()
        self.tab_widget.addTab(self.studio_tab, "Studio Workspace")

        # Tab 2: Settings
        self.settings_tab = QWidget()
        self.init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Settings")

    def init_studio_tab(self):
        layout = QVBoxLayout(self.studio_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        

        # Controls Card
        control_card = QFrame()
        control_card.setObjectName("ControlCard")
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(16, 12, 16, 12)
        control_layout.setSpacing(15)

        # Instrument Selector Dropdown
        self.instrument_combo = QComboBox()
        self.instrument_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        instruments = [
            "🎤 Vocals", "🎹 Piano", "🎸 Guitar", "🎷 Saxophone",
            "🎺 Trumpet", "🎻 Violin", "🥁 Drums", "🪈 Flute",
            "🎵 Synth", "🪗 Accordion", "🪕 Banjo", "🎶 Bass"
        ]
        for inst in instruments:
            self.instrument_combo.addItem(inst)
        control_layout.addWidget(self.instrument_combo)

        # Transport Buttons
        self.rec_btn = QPushButton("🔴 RECORD LIVE")
        self.rec_btn.setObjectName("RecordButton")
        self.rec_btn.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.rec_btn)

        self.play_btn = QPushButton("▶ PLAYBACK")
        self.play_btn.setObjectName("PlayButton")
        self.play_btn.clicked.connect(self.toggle_playback)
        control_layout.addWidget(self.play_btn)

        self.clear_btn = QPushButton("🧹 CLEAR")
        self.clear_btn.setObjectName("ClearButton")
        self.clear_btn.clicked.connect(self.clear_workspace)
        control_layout.addWidget(self.clear_btn)

        # Volume / Mic Input Level Meter
        level_vbox = QVBoxLayout()
        level_vbox.setSpacing(4)
        level_lbl = QLabel("Mic Input Level")
        level_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; font-weight: bold;")
        self.mic_level = QProgressBar()
        self.mic_level.setObjectName("MicLevelBar")
        self.mic_level.setMinimum(0)
        self.mic_level.setMaximum(100)
        self.mic_level.setValue(0)
        self.mic_level.setTextVisible(False)
        level_vbox.addWidget(level_lbl)
        level_vbox.addWidget(self.mic_level)
        control_layout.addLayout(level_vbox, stretch=1)

        # Active Track Indicator Info
        track_info_vbox = QVBoxLayout()
        track_info_vbox.setSpacing(2)
        active_lbl_title = QLabel("Recording To:")
        active_lbl_title.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.active_track_lbl = QLabel("🎤 Vocals")
        self.active_track_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #A78BFA;")
        track_info_vbox.addWidget(active_lbl_title)
        track_info_vbox.addWidget(self.active_track_lbl)
        control_layout.addLayout(track_info_vbox)

        layout.addWidget(control_card)

        # Timeline Container
        self.timeline = TimelineWidget(self)
        layout.addWidget(self.timeline, stretch=1)

        # Status / Feedback label
        self.status_lbl = QLabel("Ready to record. Click REC to start.")
        self.status_lbl.setObjectName("StatusLabel")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_lbl)

    def init_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        settings_card = QFrame()
        settings_card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(settings_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)



        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignRight)

        # Query devices and filter by host API to avoid MME's 31-character limit
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        
        # Check if WASAPI is available on Windows (provides full device names and low latency)
        has_wasapi = any(hostapis[d['hostapi']]['name'] == 'Windows WASAPI' for d in devices)
        target_api = 'Windows WASAPI' if has_wasapi else None

        input_devices = []
        output_devices = []
        for i, d in enumerate(devices):
            api_name = hostapis[d['hostapi']]['name']
            if target_api and api_name != target_api:
                continue
                
            if d['max_input_channels'] > 0:
                input_devices.append((i, d['name']))
            if d['max_output_channels'] > 0:
                output_devices.append((i, d['name']))

        # Input Combo
        self.input_combo = QComboBox()
        self.input_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.input_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for idx, name in input_devices:
            self.input_combo.addItem(name, idx)
        
        # Select default input by matching the name prefix (since default might be MME)
        try:
            default_in_idx = sd.default.device[0]
            if default_in_idx >= 0:
                default_in_name = devices[default_in_idx]['name']
                # Look for a match in our filtered input list
                matched_idx = -1
                for combobox_idx in range(self.input_combo.count()):
                    item_name = self.input_combo.itemText(combobox_idx)
                    if default_in_name in item_name or item_name in default_in_name:
                        matched_idx = combobox_idx
                        break
                if matched_idx >= 0:
                    self.input_combo.setCurrentIndex(matched_idx)
                else:
                    self.selected_input_device_id = self.input_combo.currentData()
        except Exception:
            pass
        self.input_combo.currentIndexChanged.connect(self.input_device_changed)
        form.addRow("Recording Device:", self.input_combo)

        # Output Combo
        self.output_combo = QComboBox()
        self.output_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.output_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for idx, name in output_devices:
            self.output_combo.addItem(name, idx)
            
        # Select default output by matching the name prefix
        try:
            default_out_idx = sd.default.device[1]
            if default_out_idx >= 0:
                default_out_name = devices[default_out_idx]['name']
                # Look for a match in our filtered output list
                matched_idx = -1
                for combobox_idx in range(self.output_combo.count()):
                    item_name = self.output_combo.itemText(combobox_idx)
                    if default_out_name in item_name or item_name in default_out_name:
                        matched_idx = combobox_idx
                        break
                if matched_idx >= 0:
                    self.output_combo.setCurrentIndex(matched_idx)
                else:
                    self.selected_output_device_id = self.output_combo.currentData()
        except Exception:
            pass
        self.output_combo.currentIndexChanged.connect(self.output_device_changed)
        form.addRow("Output Device:", self.output_combo)

        # Threshold Slider
        threshold_vbox = QVBoxLayout()
        self.thresh_label = QLabel(f"Noise Gate Threshold ({int(self.silence_threshold * 1000)}):")
        self.thresh_label.setStyleSheet("color: #E2E8F0; font-size: 13px;")
        
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setMinimum(2)      # 0.002
        self.thresh_slider.setMaximum(100)    # 0.100
        self.thresh_slider.setValue(int(self.silence_threshold * 1000))
        self.thresh_slider.valueChanged.connect(self.threshold_changed)
        
        threshold_vbox.addWidget(self.thresh_label)
        threshold_vbox.addWidget(self.thresh_slider)
        form.addRow("Mic Sensitivity:", threshold_vbox)

        # Recognition Mode Slider
        mode_vbox = QVBoxLayout()
        self.mode_label = QLabel(f"Recognition Mode: New")
        self.mode_label.setStyleSheet("color: #E2E8F0; font-size: 13px;")
        
        self.mode_slider = QSlider(Qt.Horizontal)
        self.mode_slider.setMinimum(0)
        self.mode_slider.setMaximum(1)
        self.mode_slider.setTickInterval(1)
        self.mode_slider.setTickPosition(QSlider.TicksBelow)
        self.mode_slider.setValue(1)  # 1 = New (default)
        self.mode_slider.valueChanged.connect(self.recognition_mode_changed)
        
        mode_vbox.addWidget(self.mode_label)
        mode_vbox.addWidget(self.mode_slider)
        form.addRow("Recognition Mode:", mode_vbox)

        card_layout.addLayout(form)
        
        # Info box
        info_lbl = QLabel(
            "Note: Sing clearly near your microphone. Higher sensitivity gates out background hum.\n"
            "The pitch-to-note analyzer maps vocal frequency inputs to standard MIDI coordinates in real-time."
        )
        info_lbl.setStyleSheet("color: #64748B; font-size: 12px; line-height: 1.5; margin-top: 10px;")
        card_layout.addWidget(info_lbl)

        layout.addWidget(settings_card)
        layout.addStretch()

    def update_active_track_label(self, track_idx):
        if track_idx < len(self.timeline.headers.track_names):
            self.active_track_lbl.setText(self.timeline.headers.track_names[track_idx])

    def input_device_changed(self):
        self.selected_input_device_id = self.input_combo.currentData()

    def output_device_changed(self):
        self.selected_output_device_id = self.output_combo.currentData()

    def threshold_changed(self, value):
        self.silence_threshold = value / 1000.0
        self.thresh_label.setText(f"Noise Gate Threshold ({value}):")
        if self.analyzer:
            self.analyzer.silence_threshold = self.silence_threshold

    def toggle_recording(self):
        if self.is_playing:
            self.stop_playback()

        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.rec_btn.setText("⏹ STOP RECORDING")
        self.rec_btn.setStyleSheet("""
            QPushButton#RecordButton {
                background-color: #3F3F46;
                border: 1px solid #EF4444;
            }
        """)
        self.play_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.status_lbl.setText("Recording live audio... Sing or hum now!")
        self.status_lbl.setStyleSheet("color: #EF4444; font-weight: bold;")

        # Reset playhead
        self.timeline.set_playhead_time(0.0)

        # Ensure track exists for the selected instrument
        instrument_name = self.instrument_combo.currentText()
        track_idx = self.timeline.ensure_track(instrument_name)
        self.active_track_lbl.setText(instrument_name)

        # Start live audio analyzer
        self.analyzer = AudioAnalyzer(
            device_id=self.selected_input_device_id,
            silence_threshold=self.silence_threshold,
            mode=self.recognition_mode
        )
        
        # Connect signals
        self.analyzer.note_started.connect(lambda midi, name, start: self.timeline.update_active_note(track_idx, midi, name, start, 0.1))
        self.analyzer.note_updated.connect(lambda midi, name, start, duration: self.timeline.update_active_note(track_idx, midi, name, start, duration))
        self.analyzer.note_ended.connect(lambda midi, name, start, duration: self.on_note_ended(track_idx, midi, name, start, duration))
        
        self.analyzer.level_updated.connect(self.update_mic_level)
        self.analyzer.time_updated.connect(self.timeline.set_playhead_time)
        self.analyzer.finished_recording.connect(self.recording_thread_finished)
        
        self.analyzer.start()

    def stop_recording(self):
        if self.analyzer:
            self.analyzer.stop()

        self.is_recording = False
        self.rec_btn.setText("🔴 RECORD LIVE")
        self.rec_btn.setStyleSheet("")
        self.play_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.status_lbl.setText("Recording stopped. Notes added to timeline.")
        self.status_lbl.setStyleSheet("color: #10B981;")
        self.mic_level.setValue(0)

    def on_note_ended(self, track_idx, midi, name, start, duration):
        self.timeline.clear_active_note()
        self.timeline.add_note_to_timeline(track_idx, midi, name, start, duration)

    def recognition_mode_changed(self, value):
        # 0 = Legacy (autocorrelation), 1 = New (YIN)
        self.recognition_mode = 'legacy' if value == 0 else 'new'
        mode_name = "Legacy" if value == 0 else "New"
        self.mode_label.setText(f"Recognition Mode: {mode_name}")

    def recording_thread_finished(self):
        self.analyzer = None



    def update_mic_level(self, level):
        # Scale RMS level (0.0 to approx 0.15 for normal speech) to 0-100%
        scaled = min(int(level * 600), 100)
        self.mic_level.setValue(scaled)

    def toggle_playback(self):
        if self.is_recording:
            return

        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        self.is_playing = True
        self.play_btn.setText("⏹ STOP PLAY")
        self.play_btn.setStyleSheet("""
            QPushButton#PlayButton {
                background-color: #3F3F46;
                border: 1px solid #10B981;
            }
        """)
        self.rec_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.status_lbl.setText("Playing timeline notes...")
        self.status_lbl.setStyleSheet("color: #10B981; font-weight: bold;")
        
        # Advance playhead from 0
        self.current_playhead = 0.0
        self.timeline.set_playhead_time(0.0)
        self.playback_timer.start(50)  # tick every 50ms

    def stop_playback(self):
        self.playback_timer.stop()
        self.is_playing = False
        self.play_btn.setText("▶ PLAYBACK")
        self.play_btn.setStyleSheet("")
        self.rec_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.status_lbl.setText("Playback stopped.")
        self.status_lbl.setStyleSheet("color: #94A3B8;")

    def advance_playback(self):
        self.current_playhead += 0.05
        self.timeline.set_playhead_time(self.current_playhead)
        
        # Check if playhead has reached the end of the timeline
        if self.current_playhead >= self.timeline.grid.timeline_duration:
            self.stop_playback()

    def clear_workspace(self):
        self.timeline.clear_timeline()
        self.status_lbl.setText("Timeline cleared.")
        self.status_lbl.setStyleSheet("color: #94A3B8;")
        self.mic_level.setValue(0)

def main():
    app = QApplication(sys.argv)
    window = SingToInstApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
