from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
    QScrollArea, QPushButton, QButtonGroup
)
from PySide6.QtCore import Qt, QSize, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont

class TimelineGridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixels_per_second = 80
        self.timeline_duration = 30  # seconds
        self.track_height = 90
        self.num_tracks = 3
        self.ruler_height = 25
        
        # Note range for vertical mapping within each track (C3 to C6)
        self.min_midi = 48  # C3
        self.max_midi = 84  # C6
        
        # Notes storage: track_index -> list of dicts
        # dict: {'midi': int, 'name': str, 'start': float, 'duration': float}
        self.notes = {0: [], 1: [], 2: []}
        
        # Active recording note
        # Dict: {'track': int, 'midi': int, 'name': str, 'start': float, 'duration': float}
        self.active_note = None
        
        # Playhead location in seconds
        self.playhead_time = 0.0
        
        self.update_widget_size()

    def update_widget_size(self):
        width = self.timeline_duration * self.pixels_per_second + 50
        height = self.num_tracks * self.track_height + self.ruler_height
        self.setFixedSize(width, height)

    def set_duration(self, seconds):
        if seconds > self.timeline_duration:
            self.timeline_duration = seconds
            self.update_widget_size()
            self.update()

    def clear_timeline(self):
        self.notes = {0: [], 1: [], 2: []}
        self.active_note = None
        self.playhead_time = 0.0
        self.timeline_duration = 30
        self.update_widget_size()
        self.update()

    def add_note(self, track_idx, midi, name, start, duration):
        note = {'midi': midi, 'name': name, 'start': start, 'duration': duration}
        self.notes[track_idx].append(note)
        
        # Expand timeline if note exceeds current duration
        end_time = start + duration
        if end_time > self.timeline_duration:
            self.set_duration(int(end_time) + 5)
        self.update()

    def set_active_note(self, track_idx, midi, name, start, duration):
        self.active_note = {
            'track': track_idx,
            'midi': midi,
            'name': name,
            'start': start,
            'duration': duration
        }
        end_time = start + duration
        if end_time > self.timeline_duration:
            self.set_duration(int(end_time) + 5)
        self.update()

    def clear_active_note(self):
        self.active_note = None
        self.update()

    def set_playhead_time(self, seconds):
        self.playhead_time = seconds
        if self.playhead_time > self.timeline_duration:
            self.set_duration(int(self.playhead_time) + 5)
        self.update()

    def get_note_coordinates(self, track_idx, midi, start, duration):
        # Horizontal positioning
        x = start * self.pixels_per_second
        w = max(duration * self.pixels_per_second, 3.0)  # Min width 3px to see short notes
        
        # Vertical positioning inside the track
        track_top = self.ruler_height + track_idx * self.track_height
        
        # Clamp MIDI to our range
        clamped_midi = max(self.min_midi, min(self.max_midi, midi))
        
        # Calculate vertical percent (0.0 to 1.0)
        pitch_range = self.max_midi - self.min_midi
        percent = (clamped_midi - self.min_midi) / pitch_range
        
        # Position note block inside the track (leave 10px margins top/bottom)
        margin = 12
        usable_height = self.track_height - (margin * 2)
        note_height = 16
        
        # Inverse percent because y=0 is at the top
        y = track_top + margin + (1.0 - percent) * (usable_height - note_height)
        
        return x, y, w, note_height

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw backgrounds
        width = self.width()
        # Keep grid drawing bounded by track heights instead of stretched widget height
        height = self.num_tracks * self.track_height + self.ruler_height
        
        # Main background
        painter.fillRect(0, 0, width, height, QColor("#121214"))
        
        # Draw ruler background
        painter.fillRect(0, 0, width, self.ruler_height, QColor("#18181B"))
        painter.setPen(QPen(QColor("#27272A"), 1))
        painter.drawLine(0, self.ruler_height - 1, width, self.ruler_height - 1)

        # Draw grid & ruler labels
        # Vertical grid lines (every 1 second)
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        
        for sec in range(int(self.timeline_duration) + 1):
            x = sec * self.pixels_per_second
            
            # Minor lines (every 0.25s)
            painter.setPen(QPen(QColor("#1F1F23"), 1, Qt.DashLine))
            for i in range(1, 4):
                minor_x = x + i * (self.pixels_per_second / 4)
                painter.drawLine(minor_x, self.ruler_height, minor_x, height)
                
            # Major lines (every 1s)
            painter.setPen(QPen(QColor("#2D2D35"), 1))
            painter.drawLine(x, self.ruler_height, x, height)
            
            # Ruler label
            painter.setPen(QColor("#71717A"))
            painter.drawText(x + 4, self.ruler_height - 6, f"{sec}s")

        # Draw horizontal track separators
        for i in range(self.num_tracks + 1):
            y = self.ruler_height + i * self.track_height
            painter.setPen(QPen(QColor("#27272A"), 1 if i < self.num_tracks else 2))
            painter.drawLine(0, y, width, y)

        # Draw recorded notes
        for track_idx, note_list in self.notes.items():
            for note in note_list:
                self.draw_note_block(painter, track_idx, note['midi'], note['name'], note['start'], note['duration'], is_active=False)

        # Draw active note
        if self.active_note:
            self.draw_note_block(
                painter, 
                self.active_note['track'], 
                self.active_note['midi'], 
                self.active_note['name'], 
                self.active_note['start'], 
                self.active_note['duration'], 
                is_active=True
            )

        # Draw playhead
        playhead_x = self.playhead_time * self.pixels_per_second
        painter.setPen(QPen(QColor("#EF4444"), 2))
        painter.drawLine(playhead_x, 0, playhead_x, height)
        
        # Playhead triangle handle at the top
        painter.setBrush(QBrush(QColor("#EF4444")))
        painter.setPen(Qt.NoPen)
        points = [
            QRectF(playhead_x - 5, 0, 10, 8)
        ]
        painter.drawPolygon([
            self.map_point(playhead_x, 10),
            self.map_point(playhead_x - 6, 0),
            self.map_point(playhead_x + 6, 0)
        ])

    def map_point(self, x, y):
        from PySide6.QtCore import QPointF
        return QPointF(x, y)

    def draw_note_block(self, painter, track_idx, midi, name, start, duration, is_active=False):
        x, y, w, h = self.get_note_coordinates(track_idx, midi, start, duration)
        
        rect = QRectF(x, y, w, h)
        radius = 4.0
        
        # Define gradient for the note block
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if is_active:
            # Pulsing bright purple/magenta for live recording note
            gradient.setColorAt(0.0, QColor("#F472B6"))
            gradient.setColorAt(1.0, QColor("#EC4899"))
            border_color = QColor("#F472B6")
        else:
            # Rich violet/purple for completed notes
            gradient.setColorAt(0.0, QColor("#A78BFA"))
            gradient.setColorAt(1.0, QColor("#7C3AED"))
            border_color = QColor("#8B5CF6")
            
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, radius, radius)
        
        # Draw Note Name Text inside or next to the block
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        text_rect = QRectF(x + 4, y, w - 8, h)
        # Only draw if block is wide enough
        if w > 25:
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, name)
        else:
            # Draw above the block if it's too small
            painter.drawText(x, y - 2, name)


class TrackHeaderWidget(QWidget):
    record_track_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.track_names = ["Vocal Input", "Synth Track", "Piano Track"]
        self.track_height = 90
        self.ruler_height = 25
        
        self.active_record_track = 0
        self.mutes = [False, False, False]
        
        self.setFixedWidth(160)
        self.setFixedHeight(len(self.track_names) * self.track_height + self.ruler_height)
        
        self.init_ui()

    def init_ui(self):
        # We will manually position our UI controls relative to the tracks
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, self.ruler_height, 0, 0)
        layout.setSpacing(0)
        
        self.bg_group = QButtonGroup(self)
        self.bg_group.setExclusive(True)
        
        for i, name in enumerate(self.track_names):
            track_frame = QFrame()
            track_frame.setFrameShape(QFrame.NoFrame)
            track_frame.setFixedHeight(self.track_height)
            track_frame.setStyleSheet("""
                QFrame {
                    background-color: #1A1A1E;
                    border-bottom: 1px solid #27272A;
                    border-right: 2px solid #2D2D37;
                }
            """)
            
            frame_layout = QVBoxLayout(track_frame)
            frame_layout.setContentsMargins(12, 10, 12, 10)
            frame_layout.setSpacing(6)
            
            # Title
            title_lbl = QLabel(name)
            title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #F1F5F9; border: none; background: transparent;")
            frame_layout.addWidget(title_lbl)
            
            # Buttons
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(8)
            
            # Record enable button
            rec_btn = QPushButton("REC")
            rec_btn.setCheckable(True)
            rec_btn.setChecked(i == 0)
            rec_btn.setObjectName(f"rec_btn_{i}")
            rec_btn.setFixedSize(45, 22)
            rec_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D37;
                    border: 1px solid #3F3F46;
                    border-radius: 4px;
                    color: #94A3B8;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #EF4444;
                    border-color: #DC2626;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    border-color: #71717A;
                }
            """)
            self.bg_group.addButton(rec_btn, i)
            btn_layout.addWidget(rec_btn)
            
            # Mute button
            mute_btn = QPushButton("MUTE")
            mute_btn.setCheckable(True)
            mute_btn.setObjectName(f"mute_btn_{i}")
            mute_btn.setFixedSize(45, 22)
            mute_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D37;
                    border: 1px solid #3F3F46;
                    border-radius: 4px;
                    color: #94A3B8;
                    font-size: 9px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #F59E0B;
                    border-color: #D97706;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    border-color: #71717A;
                }
            """)
            mute_btn.toggled.connect(lambda checked, idx=i: self.set_mute(idx, checked))
            btn_layout.addWidget(mute_btn)
            
            frame_layout.addLayout(btn_layout)
            layout.addWidget(track_frame)
            
        self.bg_group.idClicked.connect(self.record_track_toggled)

    def record_track_toggled(self, track_idx):
        self.active_record_track = track_idx
        self.record_track_changed.emit(track_idx)

    def set_mute(self, track_idx, is_muted):
        self.mutes[track_idx] = is_muted

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw ruler cover background (top left corner)
        painter.fillRect(0, 0, self.width(), self.ruler_height, QColor("#18181B"))
        painter.setPen(QPen(QColor("#27272A"), 1))
        painter.drawLine(0, self.ruler_height - 1, self.width(), self.ruler_height - 1)
        
        # Track divider vertical border
        painter.setPen(QPen(QColor("#2D2D37"), 2))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())


class TimelineWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelineContainer")
        self.setStyleSheet("""
            QFrame#TimelineContainer {
                background-color: #121214;
                border-radius: 12px;
                border: 1px solid #2D2D37;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Fixed Headers Sidebar (aligned to top to match grid layout when expanded)
        self.headers = TrackHeaderWidget(self)
        layout.addWidget(self.headers, alignment=Qt.AlignTop)
        
        # Scrollable Grid Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                border: none;
                background: #18181B;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #3F3F46;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #52525B;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
        """)
        
        self.grid = TimelineGridWidget(self)
        self.scroll_area.setWidget(self.grid)
        
        layout.addWidget(self.scroll_area)
        
        # Wire active record track selection to the grid
        self.headers.record_track_changed.connect(self.active_track_changed)

    def active_track_changed(self, track_idx):
        # We can use this to update state if needed
        pass

    def get_active_record_track(self):
        return self.headers.active_record_track

    def add_note_to_timeline(self, track_idx, midi, name, start, duration):
        self.grid.add_note(track_idx, midi, name, start, duration)

    def update_active_note(self, track_idx, midi, name, start, duration):
        self.grid.set_active_note(track_idx, midi, name, start, duration)
        
        # Auto-scroll scroll area to follow the active note/playhead
        playhead_x = (start + duration) * self.grid.pixels_per_second
        scroll_bar = self.scroll_area.horizontalScrollBar()
        visible_width = self.scroll_area.viewport().width()
        
        if playhead_x > scroll_bar.value() + visible_width - 100:
            scroll_bar.setValue(int(playhead_x - visible_width + 100))

    def clear_active_note(self):
        self.grid.clear_active_note()

    def set_playhead_time(self, seconds):
        self.grid.set_playhead_time(seconds)
        
        # Auto-scroll to follow playhead during playback
        playhead_x = seconds * self.grid.pixels_per_second
        scroll_bar = self.scroll_area.horizontalScrollBar()
        visible_width = self.scroll_area.viewport().width()
        
        if playhead_x > scroll_bar.value() + visible_width - 100:
            scroll_bar.setValue(int(playhead_x - visible_width + 100))

    def clear_timeline(self):
        self.grid.clear_timeline()
