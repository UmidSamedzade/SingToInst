import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox, QSlider, QProgressBar,
    QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QPalette

class SingToInstApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SingToInst - Vocal to Instrument Converter")
        self.resize(600, 520)
        self.setMinimumSize(500, 480)

        # Style sheet for dark mode high aesthetic look
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F0F11;
            }
            QWidget {
                color: #E2E8F0;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
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
            QFrame#UploadCard, QFrame#SettingsCard {
                background-color: #1E1E24;
                border-radius: 12px;
                border: 1px solid #2D2D37;
            }
            QLabel#SectionTitle {
                font-size: 15px;
                font-weight: 600;
                color: #F8FAFC;
                margin-bottom: 5px;
            }
            QPushButton#UploadButton {
                background-color: #2D2D37;
                border: 2px dashed #4B5563;
                border-radius: 8px;
                color: #94A3B8;
                font-size: 14px;
                min-height: 60px;
                text-align: center;
            }
            QPushButton#UploadButton:hover {
                background-color: #374151;
                border-color: #A78BFA;
                color: #F8FAFC;
            }
            QPushButton#ConvertButton {
                background-color: #8B5CF6;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 600;
                min-height: 44px;
            }
            QPushButton#ConvertButton:hover {
                background-color: #7C3AED;
            }
            QPushButton#ConvertButton:pressed {
                background-color: #6D28D9;
            }
            QComboBox {
                background-color: #0F0F11;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 12px;
                color: #E2E8F0;
                font-size: 13px;
                min-height: 36px;
            }
            QSlider {
                min-height: 30px;
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
            QProgressBar {
                background-color: #0F0F11;
                border: 1px solid #2D2D37;
                border-radius: 6px;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #8B5CF6;
                border-radius: 5px;
            }
            QLabel#StatusLabel {
                font-size: 13px;
                color: #A1A1AA;
            }
        """)

        # Main Layout container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header Section
        header_layout = QVBoxLayout()
        title_label = QLabel("SingToInst")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("Convert your vocal singing into synthetic instrument tracks in seconds.")
        subtitle_label.setObjectName("SubtitleLabel")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # Upload Card
        upload_card = QFrame()
        upload_card.setObjectName("UploadCard")
        upload_layout = QVBoxLayout(upload_card)
        upload_layout.setContentsMargins(20, 20, 20, 20)
        upload_layout.setSpacing(12)
        
        upload_title = QLabel("Vocal Audio Input")
        upload_title.setObjectName("SectionTitle")
        upload_layout.addWidget(upload_title)

        self.upload_btn = QPushButton("Drag & Drop or Click to Select Audio (.wav, .mp3)")
        self.upload_btn.setObjectName("UploadButton")
        self.upload_btn.clicked.connect(self.select_audio_file)
        upload_layout.addWidget(self.upload_btn)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #64748B; font-size: 12px; margin-top: 5px;")
        upload_layout.addWidget(self.file_label)
        
        main_layout.addWidget(upload_card)

        # Settings Card
        settings_card = QFrame()
        settings_card.setObjectName("SettingsCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(12)

        settings_title = QLabel("Conversion Parameters")
        settings_title.setObjectName("SectionTitle")
        settings_layout.addWidget(settings_title)

        # Form Layout fields
        fields_layout = QHBoxLayout()
        fields_layout.setSpacing(20)
        
        # Instrument selector
        inst_vbox = QVBoxLayout()
        inst_vbox.setSpacing(6)
        inst_label = QLabel("Target Instrument:")
        inst_label.setStyleSheet("font-size: 12px; color: #94A3B8;")
        self.inst_combo = QComboBox()
        self.inst_combo.addItems(["Synthesizer (Sine Wave)", "Grand Piano", "Violin", "Classic Flute", "808 Bass"])
        inst_vbox.addWidget(inst_label)
        inst_vbox.addWidget(self.inst_combo)
        fields_layout.addLayout(inst_vbox)

        # Sensitivity Slider
        sens_vbox = QVBoxLayout()
        sens_vbox.setSpacing(6)
        sens_label = QLabel("Pitch Sensitivity (50%):")
        sens_label.setStyleSheet("font-size: 12px; color: #94A3B8;")
        self.sens_slider = QSlider(Qt.Horizontal)
        self.sens_slider.setMinimum(10)
        self.sens_slider.setMaximum(100)
        self.sens_slider.setValue(50)
        self.sens_slider.valueChanged.connect(self.update_slider_label)
        self.sens_label_ref = sens_label # Keep reference to update text
        
        sens_vbox.addWidget(sens_label)
        sens_vbox.addWidget(self.sens_slider)
        fields_layout.addLayout(sens_vbox)

        settings_layout.addLayout(fields_layout)
        main_layout.addWidget(settings_card)

        # Convert Action Button
        self.convert_btn = QPushButton("Convert Singing to Instrument")
        self.convert_btn.setObjectName("ConvertButton")
        self.convert_btn.clicked.connect(self.start_conversion)
        main_layout.addWidget(self.convert_btn)

        # Progress / Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # Add a stretch to push everything to top if resized
        main_layout.addStretch()

    def select_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Vocal Audio File", "", "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a)"
        )
        if file_path:
            self.file_label.setText(file_path)
            self.status_label.setText("Audio loaded successfully.")
            self.status_label.setStyleSheet("color: #10B981;") # Green for success

    def update_slider_label(self, value):
        self.sens_label_ref.setText(f"Pitch Sensitivity ({value}%):")

    def start_conversion(self):
        # Verify file is selected
        if self.file_label.text() == "No file selected":
            self.status_label.setText("Error: Please select a vocal audio file first.")
            self.status_label.setStyleSheet("color: #EF4444;") # Red for error
            return

        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Analyzing pitch and converting...")
        self.status_label.setStyleSheet("color: #A78BFA;")

        # A simple simulated timer for visual progress
        from PySide6.QtCore import QTimer
        self.progress_value = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.advance_progress)
        self.timer.start(50) # Every 50ms

    def advance_progress(self):
        self.progress_value += 2
        self.progress_bar.setValue(self.progress_value)
        if self.progress_value >= 100:
            self.timer.stop()
            self.convert_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            instrument = self.inst_combo.currentText()
            self.status_label.setText(f"Successfully converted to {instrument}!")
            self.status_label.setStyleSheet("color: #10B981;")

def main():
    app = QApplication(sys.argv)
    window = SingToInstApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
