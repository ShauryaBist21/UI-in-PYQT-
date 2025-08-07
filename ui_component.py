
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QTextEdit, QCalendarWidget, QButtonGroup, QComboBox,
    QRadioButton, QGridLayout, QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QTabWidget, QFrame, QSplitter, QProgressBar, QDateEdit, QTimeEdit,
    QSpinBox, QCheckBox, QGroupBox, QScrollArea, QMainWindow, QStatusBar,
    QToolBar, QAction, QMenu, QMenuBar, QDockWidget, QSizePolicy, QDialog)
from PyQt5.QtCore import Qt, QDate, QTime, QDateTime, QTimer, QSize, QRect, QPoint, pyqtSignal, QThread, QByteArray
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont, QIcon, QBrush, QCursor, QPolygon
import cv2
import datetime
import json
import os
import numpy as np
import random

# Video processing thread for better performance
class VideoProcessingThread(QThread):
    frame_ready = pyqtSignal(object)
    detection_ready = pyqtSignal(list, list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.cap = None
    
    def set_capture(self, cap):
        self.cap = cap
    
    def run(self):
        self.running = True
        while self.running and self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                # Process frame for detections
                # This is a simplified example
                detection_boxes = []
                detection_labels = []
                
                # Emit signals
                self.frame_ready.emit(frame)
                self.detection_ready.emit(detection_boxes, detection_labels)
            
            # Sleep to control FPS
            self.msleep(33)  # ~30 FPS
    
    def stop(self):
        self.running = False

# Custom slider with detection markers
class DetectionSlider(QSlider):
    clicked = pyqtSignal(int)
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.detection_points = []
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2c3e50, stop:1 #1abc9c);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 5px;
            }
        """)
        
    def set_detection_points(self, points):
        self.detection_points = points
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.detection_points:
            return
            
        painter = QPainter(self)
        painter.setPen(QPen(QColor(255, 0, 0), 3))
        
        for point in self.detection_points:
            # Convert detection frame index to slider position
            x_pos = int((point / self.maximum() if self.maximum() > 0 else 0) * self.width())
            painter.drawLine(x_pos, 0, x_pos, self.height())
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            value = self.minimum() + ((self.maximum() - self.minimum()) * event.x()) // self.width()
            self.setValue(value)
            self.clicked.emit(value)
        super().mousePressEvent(event)

# Custom video frame with overlay capabilities
class VideoFrame(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #000000; border: 2px solid #2c3e50; border-radius: 5px;")
        self.setAlignment(Qt.AlignCenter)
        self.setText("No Video Feed")
        self.setFont(QFont("Arial", 14))
        self.detection_boxes = []
        self.detection_labels = []
        self.grid_enabled = True
        self.info_overlay = True
        self.recording = False
        self.setMinimumSize(640, 480)
        self.current_frame = None
        
    def set_detection_boxes(self, boxes, labels):
        self.detection_boxes = boxes
        self.detection_labels = labels
        self.update()
        
    def set_frame(self, frame):
        """Set the current frame for display"""
        self.current_frame = frame
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Draw grid if enabled
        if self.grid_enabled:
            painter.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.DashLine))
            
            # Vertical lines
            for i in range(1, 3):
                x = int(self.width() * i / 3)
                painter.drawLine(x, 0, x, self.height())
                
            # Horizontal lines
            for i in range(1, 3):
                y = int(self.height() * i / 3)
                painter.drawLine(0, y, self.width(), y)
        
        # Draw detection boxes
        for i, (x, y, w, h) in enumerate(self.detection_boxes):
            # Scale coordinates to widget size
            x_scaled = int(x * self.width())
            y_scaled = int(y * self.height())
            w_scaled = int(w * self.width())
            h_scaled = int(h * self.height())
            
            # Draw rectangle
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawRect(x_scaled, y_scaled, w_scaled, h_scaled)
            
            # Draw label if available
            if i < len(self.detection_labels):
                painter.setPen(QColor(255, 255, 0))
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.drawText(x_scaled, y_scaled - 5, self.detection_labels[i])
        
        # Draw recording indicator
        if self.recording:
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.drawEllipse(10, 10, 20, 20)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(35, 20, "REC")
        


# Alert widget with priority levels
class AlertWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 5px;
                color: #ecf0f1;
                alternate-background-color: #34495e;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #34495e;
            }
            QListWidget::item:selected {
                background-color: #16a085;
            }
        """)
        
    def add_alert(self, message, level="info"):
        item = QListWidgetItem()
        
        if level == "critical":
            item.setText(f"🚨 CRITICAL: {message}")
            item.setBackground(QColor(231, 76, 60, 100))
        elif level == "warning":
            item.setText(f"⚠️ WARNING: {message}")
            item.setBackground(QColor(243, 156, 18, 100))
        else:  # info
            item.setText(f"ℹ️ INFO: {message}")
            
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        item.setToolTip(f"{timestamp} - {message}")
        
        # Insert at the top
        self.insertItem(0, item)
        
        # Limit the number of items
        if self.count() > 100:
            self.takeItem(self.count() - 1)

# Enhanced calendar with detection markers
class DetectionCalendar(QCalendarWidget):
    date_clicked = pyqtSignal(QDate)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.detection_dates = set()
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setStyleSheet("""
            QCalendarWidget QToolButton {
                color: white;
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 3px;
            }
            QCalendarWidget QMenu {
                background-color: #2c3e50;
                color: white;
            }
            QCalendarWidget QSpinBox {
                background-color: #2c3e50;
                color: white;
                selection-background-color: #1abc9c;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #34495e;
                color: white;
                selection-background-color: #1abc9c;
                selection-color: white;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #2c3e50;
            }
        """)
        self.clicked.connect(self.date_clicked.emit)
        
    def add_detection_date(self, date):
        if isinstance(date, datetime.date):
            qdate = QDate(date.year, date.month, date.day)
        else:
            qdate = date
            
        self.detection_dates.add(qdate)
        self.update_detection_markers()
        
    def update_detection_markers(self):
        for date in self.detection_dates:
            format = self.dateTextFormat(date)
            format.setBackground(QColor(231, 76, 60, 100))
            self.setDateTextFormat(date, format)

# Main VIPERS UI Class
class VIPERS_UI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VIPERS - Drone Surveillance System")
        self.setGeometry(100, 50, 1280, 800)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #232526, stop:1 #414345);
                color: #ecf0f1;
            }
            QLabel {
                color: #ecf0f1;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #232526, stop:1 #1abc9c);
                color: white;
                border: 1.5px solid #16a085;
                border-radius: 8px;
                padding: 7px 24px;
                min-height: 36px;
                min-width: 120px;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: 500;
                transition: background 0.2s;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1abc9c, stop:1 #3498db);
                color: #fff;
            }
            QPushButton:pressed {
                background: #16a085;
            }
            QTabWidget::pane {
                border: 2px solid #16a085;
                background: #232526;
                border-radius: 10px;
                margin-top: 8px;
            }
            QTabBar::tab {
                background: #34495e;
                color: #fff;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 12px 36px;
                margin-right: 8px;
                min-width: 160px;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabBar::tab:selected {
                background: #1abc9c;
                color: #232526;
                border-bottom: 4px solid #16a085;
            }
            QTextEdit, QListWidget {
                background: #232526;
                color: #ecf0f1;
                border: 1.5px solid #16a085;
                border-radius: 8px;
                font-size: 14px;
                font-family: 'Consolas', 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 2px solid #16a085;
                border-radius: 10px;
                margin-top: 16px;
                font-weight: bold;
                color: #1abc9c;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
            }
            QComboBox {
                background: #232526;
                color: #fff;
                border: 1.5px solid #16a085;
                border-radius: 6px;
                padding: 7px;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox QAbstractItemView {
                background: #232526;
                color: #fff;
                selection-background-color: #1abc9c;
            }
            QProgressBar {
                border: 1.5px solid #16a085;
                border-radius: 8px;
                background: #232526;
                text-align: center;
                color: #fff;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1abc9c, stop:1 #3498db);
                border-radius: 8px;
            }
            QCheckBox {
                color: #1abc9c;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton {
                color: #1abc9c;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QStatusBar {
                background: #232526;
                color: #1abc9c;
                font-size: 14px;
                border-top: 2px solid #16a085;
            }
            QToolBar {
                background: #232526;
                border: none;
                spacing: 10px;
            }
            QMenuBar {
                background: #232526;
                color: #1abc9c;
                font-size: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMenuBar::item:selected {
                background: #1abc9c;
                color: #232526;
            }
            QMenu {
                background: #232526;
                color: #1abc9c;
                font-size: 15px;
            }
            QMenu::item:selected {
                background: #1abc9c;
                color: #232526;
            }
            QScrollArea {
                background: #232526;
            }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(18)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("System Ready")
        
        # Create header with title and mode selection
        header_layout = QHBoxLayout()
        
        # Title with logo
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)
        logo_label = QLabel()
        logo_pixmap = QPixmap("assests/logo.png")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_label.setText("🛡️")
            logo_label.setFont(QFont("Arial", 32, QFont.Bold))
        title_layout.addWidget(logo_label)
        self.title_label = QLabel("VIPERS: Video and Image Processing Enhancement and Recognition System")
        self.title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #1abc9c; font-family: 'Segoe UI', Arial, sans-serif; letter-spacing: 1px;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        header_layout.addLayout(title_layout, 7)
        
        # Mode selection
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(16)
        self.mode_group = QButtonGroup(self)
        self.live_radio = QRadioButton("Live")
        self.playback_radio = QRadioButton("Playback")
        self.analysis_radio = QRadioButton("Analysis")
        self.live_radio.setChecked(True)
        self.mode_group.addButton(self.live_radio)
        self.mode_group.addButton(self.playback_radio)
        self.mode_group.addButton(self.analysis_radio)
        mode_layout.addWidget(self.live_radio)
        mode_layout.addWidget(self.playback_radio)
        mode_layout.addWidget(self.analysis_radio)
        header_layout.addWidget(mode_group, 3)
        
        main_layout.addLayout(header_layout)
        
        # Create main content splitter
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(3)
        content_splitter.setStyleSheet("QSplitter::handle { background: #16a085; }")
        
        # Left panel - Video and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(16)
        
        # Video display with tabs for different views
        video_tabs = QTabWidget()
        
        # Main camera view
        self.video_frame = VideoFrame()
        video_tabs.addTab(self.video_frame, "Main Camera")
        
        # Thermal view (placeholder)
        thermal_frame = QLabel("Thermal View Not Available")
        thermal_frame.setStyleSheet("background-color: #000000; color: #ecf0f1;")
        thermal_frame.setAlignment(Qt.AlignCenter)
        video_tabs.addTab(thermal_frame, "Thermal")
        
        # Detection view (processed)
        self.detection_view_frame = VideoFrame()
        self.detection_view_frame.setText("Detection View - Shows processed frames with detections")
        video_tabs.addTab(self.detection_view_frame, "Detection View")
        
        left_layout.addWidget(video_tabs)
        
        # Video controls
        controls_group = QGroupBox("Video Controls")
        controls_layout = QVBoxLayout(controls_group)
        controls_layout.setSpacing(12)
        
        # Slider with time display
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(10)
        self.time_label = QLabel("00:00:00")
        self.time_label.setMinimumWidth(80)
        slider_layout.addWidget(self.time_label)
        
        self.video_slider = DetectionSlider(Qt.Horizontal)
        self.video_slider.setEnabled(False)  # Disabled in live mode
        slider_layout.addWidget(self.video_slider)
        
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setMinimumWidth(80)
        slider_layout.addWidget(self.duration_label)
        
        controls_layout.addLayout(slider_layout)
        
        # Playback controls
        playback_layout = QHBoxLayout()
        playback_layout.setSpacing(16)
        
        self.start_stop_button = QPushButton("Start Detection")
        playback_layout.addWidget(self.start_stop_button)
        
        self.record_button = QPushButton("Record")
        playback_layout.addWidget(self.record_button)
        
        self.play_button = QPushButton("Play")
        self.play_button.setEnabled(False)  # Disabled until recording exists
        playback_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        playback_layout.addWidget(self.stop_button)
        
        controls_layout.addLayout(playback_layout)
        
        # Detection settings
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)
        
        self.detection_combo = QComboBox()
        self.detection_combo.addItems(["Face Detection", "Drone Detection", "Person Detection", "Vehicle Detection", "All Objects"])
        settings_layout.addWidget(QLabel("Detection Type:"))
        settings_layout.addWidget(self.detection_combo)
        
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(1)
        self.sensitivity_slider.setMaximum(10)
        self.sensitivity_slider.setValue(5)
        settings_layout.addWidget(QLabel("Sensitivity:"))
        settings_layout.addWidget(self.sensitivity_slider)
        
        controls_layout.addLayout(settings_layout)
        
        # Display options
        options_layout = QHBoxLayout()
        options_layout.setSpacing(16)
        
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(True)
        options_layout.addWidget(self.grid_checkbox)
        
        self.info_checkbox = QCheckBox("Show Info Overlay")
        self.info_checkbox.setChecked(True)
        options_layout.addWidget(self.info_checkbox)
        
        self.tracking_checkbox = QCheckBox("Enable Tracking")
        self.tracking_checkbox.setChecked(True)
        options_layout.addWidget(self.tracking_checkbox)
        
        controls_layout.addLayout(options_layout)
        
        left_layout.addWidget(controls_group)
        
        # Right panel with tabs for different functions
        right_panel = QTabWidget()
        self.right_panel = right_panel
        right_panel.setStyleSheet("QTabWidget::tab-bar { left: 10px; }")
        
        # Detections tab
        detections_tab = QWidget()
        detections_layout = QVBoxLayout(detections_tab)
        detections_layout.setContentsMargins(10, 10, 10, 10)
        detections_layout.setSpacing(14)
        
        # Calendar for date selection
        calendar_group = QGroupBox("Detection Calendar")
        calendar_layout = QVBoxLayout(calendar_group)
        calendar_layout.setSpacing(8)
        self.calendar = DetectionCalendar()
        calendar_layout.addWidget(self.calendar)
        detections_layout.addWidget(calendar_group)
        
        # Detection list
        detection_list_group = QGroupBox("Detection Events")
        detection_list_layout = QVBoxLayout(detection_list_group)
        detection_list_layout.setSpacing(8)
        self.detection_list = QListWidget()
        detection_list_layout.addWidget(self.detection_list)
        detections_layout.addWidget(detection_list_group)
        
        right_panel.addTab(detections_tab, "Detections")
        
        # Logs tab
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setContentsMargins(10, 10, 10, 10)
        logs_layout.setSpacing(10)
        
        # Log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        logs_layout.addWidget(QLabel("System Logs"))
        logs_layout.addWidget(self.log_viewer)
        # Add Clear Logs button
        self.clear_logs_button = QPushButton("Clear Logs")
        self.clear_logs_button.clicked.connect(self.clear_logs)
        logs_layout.addWidget(self.clear_logs_button)
        
        right_panel.addTab(logs_tab, "Logs")
        
        # Alerts tab
        alerts_tab = QWidget()
        alerts_layout = QVBoxLayout(alerts_tab)
        alerts_layout.setContentsMargins(10, 10, 10, 10)
        alerts_layout.setSpacing(10)
        
        # Alert panel
        self.alert_panel = AlertWidget()
        alerts_layout.addWidget(QLabel("Live Alerts"))
        alerts_layout.addWidget(self.alert_panel)
        

        
        right_panel.addTab(alerts_tab, "Alerts")
        
        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(14)
        
        # Camera settings
        camera_settings_group = QGroupBox("Camera Settings")
        camera_settings_layout = QGridLayout(camera_settings_group)
        camera_settings_layout.setHorizontalSpacing(16)
        camera_settings_layout.setVerticalSpacing(10)
        
        camera_settings_layout.addWidget(QLabel("Camera Source:"), 0, 0)
        self.camera_source = QComboBox()
        self.camera_source.addItems(["Webcam", "IP Camera", "RTSP Stream", "Video File"])
        camera_settings_layout.addWidget(self.camera_source, 0, 1)
        
        camera_settings_layout.addWidget(QLabel("Resolution:"), 1, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "1280x720", "1920x1080"])
        camera_settings_layout.addWidget(self.resolution_combo, 1, 1)
        
        camera_settings_layout.addWidget(QLabel("Frame Rate:"), 2, 0)
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 60)
        self.fps_spinbox.setValue(30)
        camera_settings_layout.addWidget(self.fps_spinbox, 2, 1)
        
        settings_layout.addWidget(camera_settings_group)
        
        # Detection settings
        detection_settings_group = QGroupBox("Detection Settings")
        detection_settings_layout = QGridLayout(detection_settings_group)
        detection_settings_layout.setHorizontalSpacing(16)
        detection_settings_layout.setVerticalSpacing(10)
        
        detection_settings_layout.addWidget(QLabel("Detection Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Haar Cascade", "YOLO", "SSD MobileNet", "Custom Model"])
        detection_settings_layout.addWidget(self.model_combo, 0, 1)
        
        detection_settings_layout.addWidget(QLabel("Confidence Threshold:"), 1, 0)
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(1, 100)
        self.confidence_slider.setValue(50)
        detection_settings_layout.addWidget(self.confidence_slider, 1, 1)
        
        detection_settings_layout.addWidget(QLabel("Non-Maximum Suppression:"), 2, 0)
        self.nms_slider = QSlider(Qt.Horizontal)
        self.nms_slider.setRange(1, 100)
        self.nms_slider.setValue(50)
        detection_settings_layout.addWidget(self.nms_slider, 2, 1)
        
        settings_layout.addWidget(detection_settings_group)
        
        # Storage settings
        storage_settings_group = QGroupBox("Storage Settings")
        storage_settings_layout = QGridLayout(storage_settings_group)
        storage_settings_layout.setHorizontalSpacing(16)
        storage_settings_layout.setVerticalSpacing(10)
        
        storage_settings_layout.addWidget(QLabel("Storage Path:"), 0, 0)
        self.storage_path = QLabel("./recordings")
        storage_settings_layout.addWidget(self.storage_path, 0, 1)
        
        self.browse_button = QPushButton("Browse")
        storage_settings_layout.addWidget(self.browse_button, 0, 2)
        
        storage_settings_layout.addWidget(QLabel("Auto Delete After:"), 1, 0)
        self.auto_delete_days = QSpinBox()
        self.auto_delete_days.setRange(0, 365)
        self.auto_delete_days.setValue(30)
        self.auto_delete_days.setSpecialValueText("Never")
        storage_settings_layout.addWidget(self.auto_delete_days, 1, 1)
        storage_settings_layout.addWidget(QLabel("days"), 1, 2)
        
        settings_layout.addWidget(storage_settings_group)
        
        right_panel.addTab(settings_tab, "Settings")
        
        # Add panels to splitter
        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([700, 500])
        
        main_layout.addWidget(content_splitter)
        
        # Initialize camera and detection related attributes
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Initialize video processing flag
        self._video_initialized = False
        
        # Initialize face cascade as None (will be loaded when needed)
        self.face_cascade = None
        
        # Initialize drone detection (placeholder for actual model)
        self.drone_detector_initialized = False
        
        # Create logs directory if it doesn't exist
        self.logs_dir = "logs"
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            
        # Create recordings directory if it doesn't exist
        self.recordings_dir = "recordings"
        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir)
            
        # Detection data
        self.detected_frames = []
        self.detection_frame_indices = []
        self.detection_timestamps = []
        self.detection_video = 'detections.avi'
        self.detections_data_file = 'detections.json'
        self.playback_mode = False
        self.recording = None
        self.is_recording = False
        self.frame_count = 0
        self.current_recording_file = None
        self.total_frames = 0
        
        # Load existing detection data
        self.load_detection_data()
            
        # Connect signals to slots
        self.connect_signals()
        
        # Initialize with a log message
        self.log_message("VIPERS Surveillance System initialized")
        self.alert_panel.add_alert("System ready for operation", "info")
        
        # Ensure tab text is not elided
        self.right_panel.setStyleSheet(self.right_panel.styleSheet() + " QTabBar::tab { elide-mode: none; }")
        
        # Load UI cache
        self.load_ui_cache()
        
        # Save detection data when application closes
        self.closeEvent = self.on_close
    
    def on_close(self, event):
        """Handle application close event"""
        self.save_detection_data()
        self.cache_ui_state()
        self.log_message("Application closing - data saved")
        event.accept()
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Video", self)
        open_action.triggered.connect(self.open_video_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Current Frame", self)
        save_action.triggered.connect(self.save_current_frame)
        file_menu.addAction(save_action)
        
        export_action = QAction("Export Detections", self)
        export_action.triggered.connect(self.export_detections)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        analyze_action = QAction("Analyze Video", self)
        analyze_action.triggered.connect(self.analyze_video)
        tools_menu.addAction(analyze_action)
        
        generate_report_action = QAction("Generate Report", self)
        generate_report_action.triggered.connect(self.generate_report)
        tools_menu.addAction(generate_report_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About VIPERS", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        # Remove duplicate controls: Start Detection, Record, Play, Stop
        # Only keep screenshot and settings in the toolbar
        screenshot_action = QAction("Screenshot", self)
        screenshot_action.triggered.connect(self.save_current_frame)
        toolbar.addAction(screenshot_action)
        toolbar.addSeparator()
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(lambda: self.right_panel.setCurrentIndex(3))
        toolbar.addAction(settings_action)
        
    def connect_signals(self):
        # Connect buttons to methods
        self.start_stop_button.clicked.connect(self.start_detection)
        self.record_button.clicked.connect(self.toggle_recording)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)
        self.video_slider.sliderMoved.connect(self.seek_video)
        self.video_slider.clicked.connect(self.seek_video)
        
        # Connect log viewer to click handler
        self.log_viewer.mousePressEvent = self.log_viewer_clicked
        
        # Connect checkboxes
        self.grid_checkbox.stateChanged.connect(self.toggle_grid)
        self.info_checkbox.stateChanged.connect(self.toggle_info_overlay)
        
        # Connect mode radio buttons
        self.live_radio.toggled.connect(self.mode_changed)
        self.playback_radio.toggled.connect(self.mode_changed)
        self.analysis_radio.toggled.connect(self.mode_changed)
        
        # Connect calendar
        self.calendar.date_clicked.connect(self.load_date_detections)
        
        # Connect detection list
        self.detection_list.itemClicked.connect(self.jump_to_detection)
        
        # Connect camera source combo
        self.camera_source.currentIndexChanged.connect(self.camera_source_changed)
        
        # Connect browse button
        self.browse_button.clicked.connect(self.browse_storage_path)
        
    def start_detection(self):
        if self.cap is not None and self.cap.isOpened():
            # Stop current capture
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.start_stop_button.setText("Start Detection")
            self.log_message("Detection stopped")
            return
        
        # Initialize video processing if not already done
        self.initialize_video_processing()
        
        # Start new capture
        self.cap = cv2.VideoCapture(0)  # Use default camera
        if not self.cap.isOpened():
            self.log_message("Error: Could not open camera", "error")
            self.alert_panel.add_alert("Failed to open camera", "critical")
            return
            
        # Reset detection data
        self.detected_frames = []
        self.detection_frame_indices = []
        self.detection_timestamps = []
        self.start_time = datetime.datetime.now()
        self.frame_count = 0
        
        # Start timer for frame updates - adjust based on performance
        frame_interval = max(33, 1000 // self.fps_spinbox.value())  # Ensure minimum 30fps
        self.timer.start(frame_interval)  # Update every frame_interval ms
        self.start_stop_button.setText("Stop Detection")
        
        # Update UI
        self.video_slider.setEnabled(False)
        self.play_button.setEnabled(False)
        self.playback_mode = False
        
        # Log the action
        self.log_message("Started detection session")
        self.alert_panel.add_alert("Detection started - Monitoring for objects", "info")
        self.statusBar.showMessage("Live Detection Active")
        
    def toggle_recording(self):
        if not self.cap or not self.cap.isOpened():
            self.log_message("Cannot record: No active camera")
            return
            
        if self.is_recording:
            # Stop recording
            if self.recording:
                self.recording.release()
                self.recording = None
            self.is_recording = False
            self.record_button.setText("Record")
            self.log_message("Recording stopped")
            self.alert_panel.add_alert("Recording stopped", "info")
            self.video_frame.recording = False
            self.video_frame.update()
            
            # Enable play button if we have a recording
            if self.current_recording_file and os.path.exists(self.current_recording_file):
                self.play_button.setEnabled(True)
                self.log_message("Recording saved successfully")
        else:
            # Start recording
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_recording_file = os.path.join(self.recordings_dir, f"recording_{timestamp}.avi")
            
            # Use a more efficient codec for better performance
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')  # More efficient than XVID
            fps = min(self.fps_spinbox.value(), 30)  # Cap at 30 fps for performance
            
            self.recording = cv2.VideoWriter(
                self.current_recording_file,
                fourcc,
                fps,
                (width, height)
            )
            
            if not self.recording.isOpened():
                self.log_message("Error: Could not initialize video writer", "error")
                return
            
            self.is_recording = True
            self.record_button.setText("Stop Recording")
            self.log_message(f"Started recording to {self.current_recording_file}")
            self.alert_panel.add_alert("Recording started", "info")
            self.video_frame.recording = True
            self.video_frame.update()
            
    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if not ret:
            self.log_message("Error: Failed to capture frame", "error")
            self.timer.stop()
            return
            
        # Increment frame counter
        self.frame_count += 1
        
        # Get detection type from combo box
        detection_type = self.detection_combo.currentText()
        
        # Initialize detection boxes and labels
        detection_boxes = []
        detection_labels = []
        
        # Process frame based on detection type
        if detection_type == "Face Detection":
            detected_objects, processed_frame = self.detect_faces(frame.copy())
        elif detection_type == "Drone Detection":
            detected_objects, processed_frame = self.detect_drones(frame.copy())
        elif detection_type == "Person Detection":
            detected_objects, processed_frame = self.detect_persons(frame.copy())
        elif detection_type == "Vehicle Detection":
            detected_objects, processed_frame = self.detect_vehicles(frame.copy())
        else:  # All Objects
            detected_objects, processed_frame = self.detect_all_objects(frame.copy())
        
        # Convert detections to relative coordinates for display
        for obj in detected_objects:
            x, y, w, h = obj['box']
            rel_x = x / frame.shape[1]
            rel_y = y / frame.shape[0]
            rel_w = w / frame.shape[1]
            rel_h = h / frame.shape[0]
            
            detection_boxes.append((rel_x, rel_y, rel_w, rel_h))
            detection_labels.append(obj['label'])
        
        # If we have detections, store this frame and update calendar
        if detection_boxes:
            # Store detection data
            self.detected_frames.append(frame.copy())
            self.detection_frame_indices.append(self.frame_count)
            self.detection_timestamps.append(datetime.datetime.now())
            
            # Add to calendar
            current_date = datetime.datetime.now().date()
            self.calendar.add_detection_date(current_date)
            
            # Update detection list
            self.add_detection_to_list(detection_boxes, detection_labels)
            
            # Update the slider with detection points if in playback mode
            if self.playback_mode and hasattr(self, 'video_slider'):
                self.video_slider.set_detection_points(self.detection_frame_indices)
            
            # Log detection
            detection_msg = f"Detected {len(detection_boxes)} {detection_type.lower()}(s)"
            self.log_message(detection_msg, "detection")
            
            # Show alert
            self.alert_panel.add_alert(f"Detection: {len(detection_boxes)} objects found", "warning")
        
        # Save frame to recording if active
        if self.is_recording and self.recording:
            self.recording.write(processed_frame)
            
        # Update detection boxes in video frame
        self.video_frame.set_detection_boxes(detection_boxes, detection_labels)
        
        # Convert frame to QImage and display (use processed frame for better visualization)
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        image = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        
        # Scale pixmap to fit the video frame while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(self.video_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_frame.setPixmap(scaled_pixmap)
        
        # Also update detection view frame
        self.detection_view_frame.setPixmap(scaled_pixmap)
        self.detection_view_frame.set_detection_boxes(detection_boxes, detection_labels)
        
        # Update time display
        if hasattr(self, 'start_time'):
            elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
            hours, remainder = divmod(int(elapsed), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        
    def detect_faces(self, frame):
        # Ensure video processing is initialized
        if not self._video_initialized or self.face_cascade is None:
            self.initialize_video_processing()
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Get sensitivity value (scale factor is inverse - higher value = less sensitive)
        sensitivity = self.sensitivity_slider.value()
        scale_factor = 1.3 - (sensitivity * 0.02)  # Range from 1.1 to 1.3
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # Prepare results
        detected_objects = []
        
        for (x, y, w, h) in faces:
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add text label
            cv2.putText(frame, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add to detected objects
            detected_objects.append({
                'label': 'Face',
                'box': (x, y, w, h),
                'confidence': 1.0  # Haar cascade doesn't provide confidence scores
            })
            
        return detected_objects, frame
        
    def detect_drones(self, frame):
        # This is a placeholder for actual drone detection
        # In a real implementation, you would use a specialized model for drone detection
        
        # Simulate drone detection with random detections
        detected_objects = []
        
        # Only detect occasionally to simulate realistic behavior
        if random.random() < 0.05:  # 5% chance of detection
            # Generate a random position for the drone
            h, w = frame.shape[:2]
            x = random.randint(0, w - 100)
            y = random.randint(0, h - 100)
            width = random.randint(50, 100)
            height = random.randint(50, 100)
            
            # Draw rectangle around drone
            cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 255), 2)
            
            # Add text label
            cv2.putText(frame, "Drone", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Add to detected objects
            detected_objects.append({
                'label': 'Drone',
                'box': (x, y, width, height),
                'confidence': random.uniform(0.7, 0.95)
            })
            
        return detected_objects, frame
        
    def detect_persons(self, frame):
        # Placeholder for person detection
        # In a real implementation, you would use a model like YOLO or SSD
        
        # For demonstration, we'll use the face detector but label as "Person"
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        
        detected_objects = []
        
        for (x, y, w, h) in faces:
            # Extend the box to simulate full body
            body_h = int(h * 3)  # Body is about 3x the height of the face
            
            # Make sure we don't go out of frame
            if y + body_h > frame.shape[0]:
                body_h = frame.shape[0] - y
                
            # Draw rectangle around person
            cv2.rectangle(frame, (x, y), (x + w, y + body_h), (255, 0, 0), 2)
            
            # Add text label
            cv2.putText(frame, "Person", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            # Add to detected objects
            detected_objects.append({
                'label': 'Person',
                'box': (x, y, w, body_h),
                'confidence': 0.85
            })
            
        return detected_objects, frame
        
    def detect_vehicles(self, frame):
        # Placeholder for vehicle detection
        # In a real implementation, you would use a specialized model
        
        # Simulate vehicle detection with random detections
        detected_objects = []
        
        # Only detect occasionally
        if random.random() < 0.03:  # 3% chance of detection
            # Generate a random position for the vehicle
            h, w = frame.shape[:2]
            x = random.randint(0, w - 200)
            y = random.randint(h//2, h - 100)  # Vehicles usually in lower half of frame
            width = random.randint(100, 200)
            height = random.randint(50, 100)
            
            # Draw rectangle around vehicle
            cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 0), 2)
            
            # Add text label
            cv2.putText(frame, "Vehicle", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Add to detected objects
            detected_objects.append({
                'label': 'Vehicle',
                'box': (x, y, width, height),
                'confidence': random.uniform(0.75, 0.9)
            })
            
        return detected_objects, frame
        
    def detect_all_objects(self, frame):
        # Combine all detection methods
        face_objects, frame = self.detect_faces(frame)
        drone_objects, frame = self.detect_drones(frame)
        person_objects, frame = self.detect_persons(frame)
        vehicle_objects, frame = self.detect_vehicles(frame)
        
        # Combine all detections
        all_objects = face_objects + drone_objects + person_objects + vehicle_objects
        
        return all_objects, frame
        
    def play_video(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        if self.timer.isActive():
            # Pause playback
            self.timer.stop()
            self.play_button.setText("Play")
        else:
            # Start/resume playback
            self.timer.start(30)  # Update every 30ms (approx. 33 fps)
            self.play_button.setText("Pause")
            self.log_message(f"Playing video: {os.path.basename(self.current_recording_file)}")
            
            # Make sure detection points are displayed on the slider
            if hasattr(self, 'detection_frame_indices') and self.detection_frame_indices:
                self.video_slider.set_detection_points(self.detection_frame_indices)
        
    def update_playback(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        # Get current position
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        
        # Check if we reached the end
        if current_frame >= self.total_frames - 1:
            self.timer.stop()
            self.play_button.setText("Play")
            self.log_message("Playback finished")
            self.statusBar.showMessage("Playback Finished")
            return
            
        # Read frame
        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            self.log_message("Error: Failed to read frame from video", "error")
            return
            
        # Update slider position
        self.video_slider.setValue(current_frame)
        
        # Update time display
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        current_time = current_frame / fps if fps > 0 else 0
        hours, remainder = divmod(int(current_time), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.time_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        
        # Check if this is a detection frame
        is_detection_frame = current_frame in self.detection_frame_indices
        
        # Add visual indicator for detection frames
        if is_detection_frame:
            # Draw red border
            cv2.rectangle(frame, (0, 0), (frame.shape[1]-1, frame.shape[0]-1), (0, 0, 255), 10)
            
            # Add text
            cv2.putText(frame, "DETECTION FRAME", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Convert frame to QImage and display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        image = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
        self.video_frame.setPixmap(QPixmap.fromImage(image))
        
    def stop_video(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
            
        # Reset UI
        self.video_frame.setText("No Video Feed")
        self.video_slider.setValue(0)
        self.video_slider.setEnabled(False)
        self.time_label.setText("00:00:00")
        self.duration_label.setText("00:00:00")
        self.play_button.setText("Play")
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Log the action
        self.log_message("Playback stopped")
        self.statusBar.showMessage("Ready")
        
    def seek_video(self, position):
        if not self.playback_mode or not self.cap or not self.cap.isOpened():
            return

        # Only start playback if the position is a detection frame
        if hasattr(self, 'detection_frame_indices') and position in self.detection_frame_indices:
            # Set position
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            # Start playback
            if not self.timer.isActive():
                self.play_video()
        else:
            # Set position only, do not start playback
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            if not self.timer.isActive():
                self.update_playback()


        

    def mode_changed(self):
        if self.live_radio.isChecked():
            # Switch to live mode
            self.stop_video()
            self.start_detection()
        elif self.playback_radio.isChecked():
            # Switch to playback mode
            self.stop_video()
            self.play_video()
        elif self.analysis_radio.isChecked():
            # Switch to analysis mode
            self.stop_video()
            self.analyze_video()
            
    def load_date_detections(self, date):
        """Load detections for the selected date"""
        date_str = date.toString("yyyy-MM-dd")
        self.log_message(f"Loading detections for {date_str}")
        
        # Clear current detection list
        self.detection_list.clear()
        
        # Check if this date has detections (in our calendar)
        qdate = QDate(date.year(), date.month(), date.day())
        if qdate in self.calendar.detection_dates:
            # Load detections from storage (in a real implementation)
            # For now, we'll show some sample detections
            self.statusBar.showMessage(f"Found detections for {date_str}")
            
            # Add sample detections for demonstration
            detection_types = ["Face", "Drone", "Person", "Vehicle"]
            for i in range(random.randint(3, 8)):  # Random number of detections
                hour = random.randint(0, 23)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                time_str = f"{hour:02}:{minute:02}:{second:02}"
                
                detection_type = random.choice(detection_types)
                count = random.randint(1, 3)
                
                item_text = f"{time_str} - {count} {detection_type}(s) detected"
                item = QListWidgetItem(item_text)
                item.setToolTip(f"Date: {date_str}, Time: {time_str}")
                self.detection_list.addItem(item)
                
            self.log_message(f"Loaded {self.detection_list.count()} detections for {date_str}")
        else:
            self.statusBar.showMessage(f"No detections found for {date_str}")
            self.log_message(f"No detections recorded for {date_str}")
                
    def jump_to_detection(self, item):
        # This would jump to the selected detection in playback mode
        if not self.playback_mode or not self.cap or not self.cap.isOpened():
            self.log_message("Cannot jump to detection: Not in playback mode")
            return
            
        # Get the time from the item text
        item_text = item.text()
        time_str = item_text.split(" - ")[0]
        
        # In a real implementation, you would look up the frame index for this detection
        # For now, we'll just jump to a random position in the video
        frame_index = random.randint(0, self.total_frames - 1)
        
        # Set the position and update the display
        self.seek_video(frame_index)
        self.log_message(f"Jumped to detection at {time_str}")
        
    def camera_source_changed(self, index):
        # Handle camera source change
        source_type = self.camera_source.currentText()
        self.log_message(f"Camera source changed to {source_type}")
        
        if self.cap and self.cap.isOpened():
            # Stop current capture
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.start_stop_button.setText("Start Detection")
        
        if source_type == "Video File":
            self.open_video_file()
        elif source_type == "IP Camera" or source_type == "RTSP Stream":
            # Show dialog to enter IP/RTSP URL
            from PyQt5.QtWidgets import QInputDialog
            url, ok = QInputDialog.getText(self, "Enter Stream URL", 
                                         "Enter the IP camera URL or RTSP stream address:")
            if ok and url:
                self.log_message(f"Connecting to stream: {url}")
                # In a real implementation, you would connect to the stream
                # For now, just show a message
                self.statusBar.showMessage(f"Connected to {source_type}")
        
    def browse_storage_path(self):
        # Open directory selection dialog
        dir_path = QFileDialog.getExistingDirectory(self, "Select Storage Directory", 
                                                  self.recordings_dir)
        if dir_path:
            self.recordings_dir = dir_path
            self.storage_path.setText(dir_path)
            self.log_message(f"Storage path changed to {dir_path}")
            
            # Create directory if it doesn't exist
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
    
    def open_video_file(self):
        # Open file selection dialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", 
                                                "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if file_path:
            self.open_video_file_direct(file_path)
            
            # Switch to playback mode
            self.playback_radio.setChecked(True)
            self.play_video()
    
    def save_current_frame(self):
        # Check if we have a frame to save
        pixmap = self.video_frame.pixmap()
        if pixmap and not pixmap.isNull():
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshots_dir = os.path.join(self.recordings_dir, "screenshots")
            
            # Create screenshots directory if it doesn't exist
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
                
            # Save the image
            file_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
            pixmap.save(file_path, "PNG")
            
            self.log_message(f"Screenshot saved to {file_path}")
            self.statusBar.showMessage("Screenshot saved")
        else:
            self.log_message("Cannot save screenshot: No frame available")
    
    def export_detections(self):
        # Check if we have detections to export
        if not self.detection_timestamps:
            self.log_message("No detections to export")
            return
            
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        exports_dir = os.path.join(self.recordings_dir, "exports")
        
        # Create exports directory if it doesn't exist
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)
            
        # Prepare detection data
        detection_data = {
            "session_start": self.start_time.isoformat() if hasattr(self, 'start_time') else None,
            "detection_count": len(self.detection_timestamps),
            "detections": []
        }
        
        # Add detection data
        for i, timestamp in enumerate(self.detection_timestamps):
            if i < len(self.detection_frame_indices):
                frame_index = self.detection_frame_indices[i]
                detection_data["detections"].append({
                    "timestamp": timestamp,
                    "frame_index": frame_index,
                    "time_str": str(datetime.timedelta(seconds=int(timestamp)))
                })
        
        # Save as JSON
        file_path = os.path.join(exports_dir, f"detections_{timestamp}.json")
        with open(file_path, 'w') as f:
            json.dump(detection_data, f, indent=4)
            
        self.log_message(f"Exported {len(self.detection_timestamps)} detections to {file_path}")
        self.statusBar.showMessage("Detections exported")
        
        # Show success message
        QMessageBox.information(self, "Export Complete", 
                              f"Successfully exported {len(self.detection_timestamps)} detections to {file_path}")
    
    def analyze_video(self):
        """Perform comprehensive video analysis"""
        if not self.cap or not self.cap.isOpened():
            QMessageBox.warning(self, "No Video", "Please load a video file for analysis.")
            return
            
        self.log_message("Starting comprehensive video analysis...")
        self.statusBar.showMessage("Analyzing video...")
        
        # Create progress dialog
        from PyQt5.QtWidgets import QProgressDialog, QApplication
        progress = QProgressDialog("Analyzing video...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Video Analysis")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        try:
            # Get video properties
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            # Analysis results
            analysis_results = {
                'total_frames': total_frames,
                'fps': fps,
                'duration': duration,
                'detection_count': 0,
                'detection_types': {},
                'motion_segments': [],
                'quality_score': 0
            }
            
            # Reset video to beginning
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Analyze each frame
            for frame_idx in range(0, total_frames, 10):  # Sample every 10th frame for speed
                if progress.wasCanceled():
                    break
                    
                # Update progress
                progress_value = int((frame_idx / total_frames) * 100)
                progress.setValue(progress_value)
                progress.setLabelText(f"Analyzing frame {frame_idx}/{total_frames}")
                QApplication.processEvents()
                
                # Read frame
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                # Perform detections
                detected_objects, _ = self.detect_all_objects(frame.copy())
                
                # Count detections
                for obj in detected_objects:
                    obj_type = obj['label']
                    analysis_results['detection_count'] += 1
                    analysis_results['detection_types'][obj_type] = analysis_results['detection_types'].get(obj_type, 0) + 1
                
                # Simple motion detection (compare with previous frame)
                if frame_idx > 0:
                    prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    # This is a simplified motion detection
                    if random.random() < 0.1:  # Simulate motion detection
                        analysis_results['motion_segments'].append(frame_idx / fps)
            
            # Calculate quality score
            analysis_results['quality_score'] = min(100, analysis_results['detection_count'] * 10)
            
            # Show results
            if not progress.wasCanceled():
                self.show_analysis_results(analysis_results)
                self.log_message("Video analysis completed successfully")
                self.statusBar.showMessage("Analysis complete")
            else:
                self.log_message("Video analysis cancelled")
                self.statusBar.showMessage("Analysis cancelled")
                
        except Exception as e:
            self.log_message(f"Error during analysis: {str(e)}", "error")
            QMessageBox.critical(self, "Analysis Error", f"Error during analysis: {str(e)}")
        finally:
            progress.close()
    
    def show_analysis_results(self, results):
        """Display analysis results in a dialog"""
        results_text = f"""
        <h2>Video Analysis Results</h2>
        <p><b>Video Duration:</b> {results['duration']:.2f} seconds</p>
        <p><b>Total Frames:</b> {results['total_frames']}</p>
        <p><b>Frame Rate:</b> {results['fps']:.2f} fps</p>
        <p><b>Total Detections:</b> {results['detection_count']}</p>
        <p><b>Quality Score:</b> {results['quality_score']}/100</p>
        
        <h3>Detection Breakdown:</h3>
        <ul>
        """
        
        for obj_type, count in results['detection_types'].items():
            results_text += f"<li>{obj_type}: {count}</li>"
        
        results_text += "</ul>"
        
        if results['motion_segments']:
            results_text += f"<p><b>Motion Detected at:</b> {len(results['motion_segments'])} time points</p>"
        
        QMessageBox.information(self, "Analysis Results", results_text)
    
    def generate_report(self):
        # This would generate a report of detections
        # For now, just show a message
        self.log_message("Generating detection report")
        
        # Check if we have detections
        if not self.detection_timestamps:
            QMessageBox.warning(self, "No Detections", 
                              "No detections available to generate a report.")
            return
            
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = os.path.join(self.recordings_dir, "reports")
        
        # Create reports directory if it doesn't exist
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            
        # Generate a simple HTML report
        file_path = os.path.join(reports_dir, f"report_{timestamp}.html")
        
        with open(file_path, 'w') as f:
            f.write("<html>\n")
            f.write("<head>\n")
            f.write("<title>VIPERS Detection Report</title>\n")
            f.write("<style>\n")
            f.write("body { font-family: Arial, sans-serif; margin: 20px; }\n")
            f.write("h1 { color: #2c3e50; }\n")
            f.write("table { border-collapse: collapse; width: 100%; }\n")
            f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
            f.write("th { background-color: #2c3e50; color: white; }\n")
            f.write("tr:nth-child(even) { background-color: #f2f2f2; }\n")
            f.write("</style>\n")
            f.write("</head>\n")
            f.write("<body>\n")
            f.write("<h1>VIPERS Detection Report</h1>\n")
            f.write(f"<p>Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            f.write(f"<p>Total Detections: {len(self.detection_timestamps)}</p>\n")
            
            # Add detection table
            f.write("<h2>Detection Events</h2>\n")
            f.write("<table>\n")
            f.write("<tr><th>No.</th><th>Time</th><th>Frame</th><th>Type</th></tr>\n")
            
            for i, timestamp in enumerate(self.detection_timestamps):
                time_str = str(datetime.timedelta(seconds=int(timestamp)))
                frame_index = self.detection_frame_indices[i] if i < len(self.detection_frame_indices) else "N/A"
                detection_type = "Object"  # In a real implementation, you would store the detection type
                
                f.write(f"<tr><td>{i+1}</td><td>{time_str}</td><td>{frame_index}</td><td>{detection_type}</td></tr>\n")
                
            f.write("</table>\n")
            f.write("</body>\n")
            f.write("</html>\n")
            
        self.log_message(f"Report generated: {file_path}")
        
        # Show success message with option to open the report
        reply = QMessageBox.question(self, "Report Generated", 
                                   f"Report has been generated at {file_path}\n\nWould you like to open it now?",
                                   QMessageBox.Yes | QMessageBox.No)
                                   
        if reply == QMessageBox.Yes:
            # Open the report in the default browser
            import webbrowser
            webbrowser.open(file_path)
    
    def show_about(self):
        # Show about dialog
        about_text = """
        <h1 style="color: #1abc9c;">VIPERS</h1>
        <h2>Video and Image Processing Enhancement and Recognition System</h2>
        <p>Version 1.0</p>
        <p>VIPERS is an advanced surveillance system designed for drone detection and monitoring.</p>
        <p>Features:</p>
        <ul>
            <li>Real-time object detection</li>
            <li>Multiple detection types (Face, Drone, Person, Vehicle)</li>
            <li>Video recording and playback</li>
            <li>Detection event logging</li>
            <li>Calendar-based detection history</li>
            <li>Alert system</li>
        </ul>
        <p>&copy; 2023 VIPERS Team</p>
        """
        
        QMessageBox.about(self, "About VIPERS", about_text)
    
    def log_message(self, message, level="info"):
        # Get current timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp_obj = datetime.datetime.now()
        
        # Format message with timestamp and level
        if level == "error":
            formatted_message = f"<span style='color:#e74c3c;'>[{timestamp}] ERROR: {message}</span>"
        elif level == "warning":
            formatted_message = f"<span style='color:#f39c12;'>[{timestamp}] WARNING: {message}</span>"
        elif level == "detection":
            formatted_message = f"<span style='color:#1abc9c;'>[{timestamp}] {message}</span>"
        else:
            formatted_message = f"<span style='color:#bdc3c7;'>[{timestamp}] INFO: {message}</span>"
            
        # Add to log viewer with clickable functionality
        cursor = self.log_viewer.textCursor()
        cursor.movePosition(cursor.End)
        self.log_viewer.setTextCursor(cursor)
        
        # Store the current position
        position = cursor.position()
        
        # Add the formatted message
        self.log_viewer.append(formatted_message)
        
        # If this is a detection-related message, make it clickable
        if ("detection" in message.lower() or "detected" in message.lower() or level == "detection"):
            # Store the timestamp and frame info for this log entry
            if hasattr(self, 'log_timestamps') == False:
                self.log_timestamps = {}
            
            # Store the position and timestamp for later retrieval
            self.log_timestamps[position] = {
                'timestamp': timestamp_obj,
                'frame_index': self.frame_count if hasattr(self, 'frame_count') else 0
            }
        
        # Write to log file
        log_date = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.logs_dir, f"vipers_{log_date}.log")
        
        try:
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")
            
        # Print to console for debugging
        print(formatted_message)
        
    def log_viewer_clicked(self, event):
        # Get the cursor at the click position
        cursor = self.log_viewer.cursorForPosition(event.pos())
        position = cursor.position()
        
        # Check if we have a timestamp for this position or nearby
        if hasattr(self, 'log_timestamps'):
            # Find the closest log entry position
            closest_pos = None
            min_distance = float('inf')
            
            for pos in self.log_timestamps.keys():
                distance = abs(position - pos)
                if distance < min_distance and distance < 100:  # Within reasonable distance
                    min_distance = distance
                    closest_pos = pos
            
            if closest_pos is not None:
                # We found a clickable log entry
                log_data = self.log_timestamps[closest_pos]
                
                # Switch to playback mode if not already
                if not self.playback_mode:
                    self.playback_radio.setChecked(True)
                    self.mode_changed()
                
                # If we have a recording loaded, seek to the frame and play
                if self.cap and self.cap.isOpened():
                    self.seek_video(log_data['frame_index'])
                    # Ensure playback starts if this is a detection frame
                    if hasattr(self, 'detection_frame_indices') and log_data['frame_index'] in self.detection_frame_indices:
                        if not self.timer.isActive():
                            self.play_video()
                else:
                    # Try to load the most recent recording
                    self.load_most_recent_recording()
                    # After loading, seek to the appropriate position
                    if self.cap and self.cap.isOpened():
                        self.seek_video(log_data['frame_index'])
                        if hasattr(self, 'detection_frame_indices') and log_data['frame_index'] in self.detection_frame_indices:
                            if not self.timer.isActive():
                                self.play_video()
        
        # Call the original mousePressEvent
        super(QTextEdit, self.log_viewer).mousePressEvent(event)
                
    def toggle_grid(self, state):
        # Toggle grid overlay on video frame
        self.video_frame.grid_enabled = state == 2  # Qt.Checked = 2
        self.video_frame.update()
        self.log_message(f"Grid overlay {'enabled' if state == 2 else 'disabled'}")
        
    def toggle_info_overlay(self, state):
        # Toggle info overlay on video frame
        self.video_frame.info_overlay = state == 2  # Qt.Checked = 2
        self.video_frame.update()
        self.log_message(f"Info overlay {'enabled' if state == 2 else 'disabled'}")
        
    def load_most_recent_recording(self):
        # Find the most recent recording file
        if not os.path.exists(self.recordings_dir):
            self.log_message("No recordings directory found")
            return
            
        recording_files = [f for f in os.listdir(self.recordings_dir) 
                          if f.endswith('.avi') and os.path.isfile(os.path.join(self.recordings_dir, f))]
        
        if not recording_files:
            self.log_message("No recordings available for playback")
            return
            
        # Sort by modification time (most recent first)
        recording_files.sort(key=lambda f: os.path.getmtime(os.path.join(self.recordings_dir, f)), reverse=True)
        
        # Load the most recent file
        self.current_recording_file = os.path.join(self.recordings_dir, recording_files[0])
        self.open_video_file_direct(self.current_recording_file)
        
    def open_video_file_direct(self, file_path):
        # Open video file directly without dialog
        if file_path and os.path.exists(file_path):
            # Initialize video processing if not already done
            self.initialize_video_processing()
            
            # Stop any active capture
            self.timer.stop()
            if self.cap:
                self.cap.release()
                
            # Open the video file
            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                self.log_message(f"Error: Could not open video file {file_path}", "error")
                self.alert_panel.add_alert("Failed to open video file", "critical")
                return
                
            # Set as current recording file
            self.current_recording_file = file_path
            
            # Get video properties
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            duration = self.total_frames / fps if fps > 0 else 0
            
            # Update UI
            self.video_slider.setMaximum(self.total_frames - 1)
            self.video_slider.setEnabled(True)
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            
            # Update duration display
            hours, remainder = divmod(int(duration), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.duration_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
            
            # Set playback mode
            self.playback_mode = True

            # Update timer to use playback method
            self.timer.timeout.disconnect()
            self.timer.timeout.connect(self.update_playback)

            # Update detection marks on slider
            if hasattr(self, 'detection_frame_indices'):
                self.video_slider.set_detection_points(self.detection_frame_indices)

            self.log_message(f"Opened video file: {os.path.basename(file_path)}")

    def add_detection_to_list(self, detection_boxes, detection_labels):
        """Add detection event to the detection list"""
        if not detection_boxes:
            return
            
        # Create timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Count detections by type
        detection_counts = {}
        for label in detection_labels:
            detection_counts[label] = detection_counts.get(label, 0) + 1
        
        # Create summary text
        summary_parts = []
        for label, count in detection_counts.items():
            summary_parts.append(f"{count} {label}")
        
        summary = ", ".join(summary_parts)
        item_text = f"{timestamp} - {summary}"
        
        # Create list item
        item = QListWidgetItem(item_text)
        item.setToolTip(f"Frame: {self.frame_count}, Objects: {len(detection_boxes)}")
        
        # Add to the top of the list
        self.detection_list.insertItem(0, item)
        
        # Limit list size to prevent memory issues
        while self.detection_list.count() > 100:
            self.detection_list.takeItem(self.detection_list.count() - 1)
        
        # Save detection data periodically
        if len(self.detection_timestamps) % 10 == 0:  # Save every 10 detections
            self.save_detection_data()
    
    def load_detection_data(self):
        """Load detection data from file"""
        try:
            if os.path.exists(self.detections_data_file):
                with open(self.detections_data_file, 'r') as f:
                    data = json.load(f)
                    self.detection_timestamps = [datetime.datetime.fromisoformat(ts) for ts in data.get('timestamps', [])]
                    self.detection_frame_indices = data.get('frame_indices', [])
                    
                    # Add dates to calendar
                    for timestamp in self.detection_timestamps:
                        self.calendar.add_detection_date(timestamp.date())
                        
                self.log_message(f"Loaded {len(self.detection_timestamps)} detection records")
        except Exception as e:
            self.log_message(f"Error loading detection data: {e}", "error")
    
    def save_detection_data(self):
        """Save detection data to file"""
        try:
            data = {
                'timestamps': [ts.isoformat() for ts in self.detection_timestamps],
                'frame_indices': self.detection_frame_indices,
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            with open(self.detections_data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.log_message("Detection data saved successfully")
        except Exception as e:
            self.log_message(f"Error saving detection data: {e}", "error")
    
    def clear_logs(self):
        self.log_viewer.clear()
        if hasattr(self, 'log_timestamps'):
            self.log_timestamps.clear()
    
    def optimize_detection_data(self):
        """Optimize detection data storage"""
        # Limit the number of stored detections to prevent memory issues
        max_detections = 1000
        
        if len(self.detection_timestamps) > max_detections:
            # Keep only the most recent detections
            self.detection_timestamps = self.detection_timestamps[-max_detections:]
            self.detection_frame_indices = self.detection_frame_indices[-max_detections:]
            
            # Save optimized data
            self.save_detection_data()
    
    def initialize_video_processing(self):
        """Lazy load video processing components only when needed"""
        if not hasattr(self, '_video_initialized') or not self._video_initialized:
            # Import heavy video processing libraries only when needed
            import cv2
            import numpy as np
            
            # Initialize face detection model
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            
            self._video_initialized = True
            self.log_message("Video processing initialized")
    
    def cleanup_resources(self):
        """Release resources to free memory"""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        
        # Clear large data structures
        self.detection_boxes = []
        self.detection_labels = []
        
        # Force garbage collection
        import gc
        gc.collect()
    
    def cache_ui_state(self):
        """Cache UI state for faster startup"""
        cache = {
            'window_geometry': self.saveGeometry().toBase64().data().decode(),
            'window_state': self.saveState().toBase64().data().decode(),
            'last_camera': self.camera_source.currentIndex(),
            'last_mode': 'live' if self.live_radio.isChecked() else 'playback' if self.playback_radio.isChecked() else 'analysis',
            'grid_enabled': self.video_frame.grid_enabled,
            'info_overlay': self.video_frame.info_overlay
        }
        
        with open('ui_cache.json', 'w') as f:
            json.dump(cache, f)

    def load_ui_cache(self):
        """Load cached UI state"""
        try:
            if os.path.exists('ui_cache.json'):
                with open('ui_cache.json', 'r') as f:
                    cache = json.load(f)
                    
                # Restore window geometry and state
                if 'window_geometry' in cache:
                    from PyQt5.QtCore import QByteArray
                    self.restoreGeometry(QByteArray.fromBase64(cache['window_geometry'].encode()))
                if 'window_state' in cache:
                    from PyQt5.QtCore import QByteArray
                    self.restoreState(QByteArray.fromBase64(cache['window_state'].encode()))
                    
                # Restore other settings
                if 'last_camera' in cache:
                    self.camera_source.setCurrentIndex(cache['last_camera'])
                if 'last_mode' in cache:
                    if cache['last_mode'] == 'playback':
                        self.playback_radio.setChecked(True)
                    elif cache['last_mode'] == 'analysis':
                        self.analysis_radio.setChecked(True)
                    else:
                        self.live_radio.setChecked(True)
                if 'grid_enabled' in cache:
                    self.video_frame.grid_enabled = cache['grid_enabled']
                    self.grid_checkbox.setChecked(cache['grid_enabled'])
                if 'info_overlay' in cache:
                    self.video_frame.info_overlay = cache['info_overlay']
                    self.info_checkbox.setChecked(cache['info_overlay'])
        except Exception as e:
            self.log_message(f"Error loading UI cache: {e}", "warning")