from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QTabWidget, QSplitter, QTextEdit, QListWidget,
                           QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QImage
import cv2
import numpy as np
import threading
import time
import sys
import os
import traceback

# Ensure the vision module can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # Go up two levels
if project_root not in sys.path:
    sys.path.append(project_root)

# Import hand detector directly from vision module
from vision.hand_detector import HandDetector

class VisionTab(QWidget):
    """Tab for robot vision system control"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # Disable updates until initialized
        self.initialized = False
        
        # Initialize vision processing variables
        self.camera = None
        self.is_streaming = False
        self.processed_frame = None
        self.n_fingers = -1
        self.last_detected_gesture = "Không phát hiện tay"
        self.hand_option = -1
        
        # Initialize HandDetector
        try:
            self.hand_detector = HandDetector(min_detection_confidence=0.7)
            self.mediapipe_available = True
            print("Hand detector initialized successfully in vision_tab")
        except Exception as e:
            print(f"Failed to initialize hand detector: {str(e)}")
            traceback.print_exc()
            self.mediapipe_available = False
            self.hand_detector = None
        
        # Tín hiệu I/O được chọn
        self.selected_io_signal = None
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Camera control section
        camera_group = QGroupBox("Camera Control")
        camera_layout = QVBoxLayout()
        
        # Camera selection
        camera_form = QFormLayout()
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Camera 0")
        self.camera_combo.addItem("Camera 1")
        self.camera_combo.addItem("Camera 2")
        camera_form.addRow("Select Camera:", self.camera_combo)
        camera_layout.addLayout(camera_form)
        
        # Camera control buttons
        btn_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.on_connect_camera)
        btn_layout.addWidget(self.connect_button)
        
        self.start_stream_button = QPushButton("Start Stream")
        self.start_stream_button.clicked.connect(self.on_start_stream)
        self.start_stream_button.setEnabled(False)
        btn_layout.addWidget(self.start_stream_button)
        
        self.capture_button = QPushButton("Capture Image")
        self.capture_button.clicked.connect(self.on_capture_image)
        self.capture_button.setEnabled(False)
        btn_layout.addWidget(self.capture_button)
        
        self.stop_stream_button = QPushButton("Stop Stream")
        self.stop_stream_button.clicked.connect(self.on_stop_stream)
        self.stop_stream_button.setEnabled(False)
        btn_layout.addWidget(self.stop_stream_button)
        
        camera_layout.addLayout(btn_layout)
        
        # Apply layout to camera group
        camera_group.setLayout(camera_layout)
        main_layout.addWidget(camera_group)
        
        # Create splitter for video display and settings
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Video display
        video_widget = QWidget()
        video_layout = QVBoxLayout(video_widget)
        
        # Video feed label
        self.video_label = QLabel("No video feed")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setMinimumSize(640, 480)
        video_layout.addWidget(self.video_label)
        
        # Hand gesture detection info
        gesture_layout = QHBoxLayout()
        gesture_layout.addWidget(QLabel("Detected Gesture:"))
        self.gesture_label = QLabel("No hand detected")
        self.gesture_label.setStyleSheet("font-weight: bold; color: green;")
        gesture_layout.addWidget(self.gesture_label)
        
        gesture_layout.addWidget(QLabel("Fingers:"))
        self.fingers_label = QLabel("-1")
        self.fingers_label.setStyleSheet("font-weight: bold; color: blue;")
        gesture_layout.addWidget(self.fingers_label)
        
        video_layout.addLayout(gesture_layout)
        
        # Add to splitter
        self.splitter.addWidget(video_widget)
        
        # Right side - Vision settings and controls
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        
        # Vision settings
        settings_group = QGroupBox("Vision Settings")
        settings_form = QFormLayout()
        
        # Brightness
        self.brightness_combo = QComboBox()
        self.brightness_combo.addItems(["Auto", "Low", "Medium", "High"])
        settings_form.addRow("Brightness:", self.brightness_combo)
        
        # Contrast
        self.contrast_combo = QComboBox()
        self.contrast_combo.addItems(["Auto", "Low", "Medium", "High"])
        settings_form.addRow("Contrast:", self.contrast_combo)
        
        # Exposure
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(["Auto", "1/30", "1/60", "1/125", "1/250", "1/500"])
        settings_form.addRow("Exposure:", self.exposure_combo)
        
        # Resolution
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "800x600", "1280x720", "1920x1080"])
        settings_form.addRow("Resolution:", self.resolution_combo)
        
        # Apply settings button
        self.apply_settings_button = QPushButton("Apply Settings")
        self.apply_settings_button.clicked.connect(self.on_apply_settings)
        self.apply_settings_button.setEnabled(False)
        settings_form.addRow("", self.apply_settings_button)
        
        # Apply layout to settings group
        settings_group.setLayout(settings_form)
        settings_layout.addWidget(settings_group)
        
        # I/O Signal Control group 
        io_group = QGroupBox("I/O Signal Control")
        io_layout = QVBoxLayout()
        
        # I/O signal selection
        io_form = QFormLayout()
        self.io_signal_combo = QComboBox()
        self.io_signal_combo.addItem("Select an I/O signal")
        io_form.addRow("I/O Signal:", self.io_signal_combo)
        io_layout.addLayout(io_form)
        
        # I/O control buttons
        io_btn_layout = QHBoxLayout()
        self.refresh_io_button = QPushButton("Refresh I/O Signals")
        self.refresh_io_button.clicked.connect(self.on_refresh_io)
        io_btn_layout.addWidget(self.refresh_io_button)
        
        self.write_io_button = QPushButton("Write Gesture to I/O")
        self.write_io_button.clicked.connect(self.on_write_io)
        self.write_io_button.setEnabled(False)
        io_btn_layout.addWidget(self.write_io_button)
        
        io_layout.addLayout(io_btn_layout)
        
        # Auto-write checkbox
        self.auto_write_check = QCheckBox("Auto-write gesture to selected I/O")
        self.auto_write_check.setEnabled(False)
        self.auto_write_check.stateChanged.connect(self.on_auto_write_changed)
        io_layout.addWidget(self.auto_write_check)
        
        # Apply layout to I/O group
        io_group.setLayout(io_layout)
        settings_layout.addWidget(io_group)
        
        # Event log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        settings_layout.addWidget(QLabel("Event Log:"))
        settings_layout.addWidget(self.log_text)
        
        # Add to splitter
        self.splitter.addWidget(settings_widget)
        
        # Set initial splitter sizes - 70% for video, 30% for settings
        self.splitter.setSizes([700, 300])
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        # Timer for updating UI with processed frames
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_ui_from_frame)
        self.ui_update_timer.start(30)  # 30ms = ~33 fps
        
        # Camera processing timer
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.process_camera)
        # Don't start the timer yet - it will be started when camera is connected
    
    def initialize(self, robot):
        """Initialize with robot reference and load initial state"""
        self.robot = robot
        
        try:
            # Lấy danh sách tín hiệu I/O để điền vào combo box
            self.load_io_signals()
            
            # Set initialized flag
            self.initialized = True
            self.log_event("Vision system initialized")
            
            # Log MediaPipe status
            if self.mediapipe_available:
                self.log_event("MediaPipe initialized successfully")
            else:
                self.log_event("MediaPipe initialization failed - hand detection disabled")
            
        except Exception as e:
            self.log_event(f"Error initializing vision tab: {str(e)}")
            traceback.print_exc()
            self.initialized = False
    
    def process_camera(self):
        """Process camera frame and detect hand gestures"""
        if not self.camera or not self.is_streaming:
            return
            
        try:
            # Read frame from camera
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.log_event("Error reading frame from camera")
                return
                
            # Flip image horizontally for easier use
            frame = cv2.flip(frame, 1)
            
            # Process frame with hand detector if available
            if self.hand_detector and self.mediapipe_available:
                processed_frame, hand_lms = self.hand_detector.findHands(frame)
                
                # Count fingers
                n_fingers = self.hand_detector.count_finger(hand_lms)
                
                # Get hand gesture
                hand_gesture = self.hand_detector.get_hand_gesture(n_fingers)
                
                # Get option
                hand_option = self.hand_detector.get_option(n_fingers)
                
                # Display option information on image
                if hand_option > 0:
                    cv2.putText(processed_frame, f"Option: {hand_option}", 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Save results
                self.processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)  # Convert to RGB for Qt
                self.n_fingers = n_fingers
                self.last_detected_gesture = hand_gesture
                self.hand_option = hand_option
            else:
                # If hand detector not available, just show original image with a notice
                h, w, _ = frame.shape
                cv2.putText(frame, "MediaPipe not available", (int(w/4), int(h/2)-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                self.processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.n_fingers = -1
                self.last_detected_gesture = "MediaPipe không khả dụng"
                self.hand_option = -1
                
            # Process I/O auto-write if enabled
            if self.selected_io_signal and self.robot:
                try:
                    io_value = self.n_fingers + 1 if self.n_fingers >= 0 else 0
                    io_value = min(io_value, 6)
                    self.robot.io.set_signal_value(self.selected_io_signal, io_value)
                except Exception as e:
                    # Don't log errors here to avoid noise
                    pass
                
        except Exception as e:
            self.log_event(f"Error processing camera: {str(e)}")
            traceback.print_exc()
    
    def load_io_signals(self):
        """Load I/O signals into combo box"""
        if not self.robot:
            return
            
        try:
            # Xóa các signals hiện tại
            self.io_signal_combo.clear()
            self.io_signal_combo.addItem("Select an I/O signal")
            
            # Lấy digital signals từ robot
            signals = self.robot.io.search_signals()
            
            if signals.get('status_code') == 200 and 'content' in signals:
                if '_embedded' in signals['content'] and 'resources' in signals['content']['_embedded']:
                    signal_list = signals['content']['_embedded']['resources']
                    
                    # Chỉ lấy digital output signals
                    for signal in signal_list:
                        signal_name = signal.get('name', '')
                        signal_type = signal.get('type', '')
                        
                        if signal_type == 'DO' or signal_type == 'GO':  # Digital Output hoặc Group Output
                            self.io_signal_combo.addItem(signal_name)
                    
                    self.log_event(f"Loaded {self.io_signal_combo.count()-1} digital output signals")
                    
                    if self.io_signal_combo.count() > 1:
                        self.write_io_button.setEnabled(True)
                        self.auto_write_check.setEnabled(True)
        except Exception as e:
            self.log_event(f"Error loading I/O signals: {str(e)}")
    
    def on_refresh_io(self):
        """Refresh I/O signals list"""
        self.load_io_signals()
    
    def on_write_io(self):
        """Write current gesture value to selected I/O signal"""
        if not self.robot:
            return
            
        signal_name = self.io_signal_combo.currentText()
        if signal_name == "Select an I/O signal":
            self.log_event("Please select an I/O signal first")
            return
            
        try:
            # Chuyển số ngón tay thành giá trị digital (0-6)
            io_value = self.n_fingers + 1 if self.n_fingers >= 0 else 0
            
            # Giới hạn giá trị tối đa là 6
            io_value = min(io_value, 6)
            
            # Ghi giá trị vào tín hiệu
            result = self.robot.io.set_signal_value(signal_name, io_value)
            
            if result.get('status_code') in [200, 204]:
                self.log_event(f"Wrote value {io_value} to signal {signal_name}")
            else:
                self.log_event(f"Failed to write to signal {signal_name}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error writing to I/O signal: {str(e)}")
    
    def on_auto_write_changed(self, state):
        """Handle auto-write checkbox state change"""
        if state == Qt.Checked:
            signal_name = self.io_signal_combo.currentText()
            if signal_name == "Select an I/O signal":
                self.log_event("Please select an I/O signal first")
                self.auto_write_check.setChecked(False)
            else:
                self.selected_io_signal = signal_name
                self.log_event(f"Auto-write enabled for signal {signal_name}")
        else:
            self.selected_io_signal = None
            self.log_event("Auto-write disabled")
    
    def set_initial_values(self, initial_values):
        """Update with initial values from subscription"""
        # This will be called once subscriptions are set up
        # Update UI with any values provided
        pass
    
    def update_ui_from_frame(self):
        """Update UI with latest processed frame"""
        if self.processed_frame is not None:
            try:
                # Chuyển đổi frame từ OpenCV sang QImage để hiển thị
                h, w, ch = self.processed_frame.shape
                bytes_per_line = ch * w
                convertToQtFormat = QImage(self.processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(convertToQtFormat)
                self.video_label.setPixmap(pixmap)
                
                # Cập nhật thông tin cử chỉ
                self.fingers_label.setText(str(self.n_fingers))
                self.gesture_label.setText(self.last_detected_gesture)
            except Exception as e:
                self.log_event(f"Error updating UI from frame: {str(e)}")
        else:
            # Không có frame, hiển thị thông báo
            self.video_label.setText("No video feed")
            self.fingers_label.setText("-1")
            self.gesture_label.setText("Không có dữ liệu")
    
    def update_ui(self):
        """Periodic UI update - used for live video feed if implemented"""
        # This method is called from main window
        pass
    
    def connect_camera(self, camera_id):
        """Connect to a camera"""
        self.log_event(f"Connecting to camera {camera_id}")
        
        try:
            # Close current camera if open
            if self.camera is not None:
                self.stop_camera()
                self.camera.release()
                self.camera = None
            
            # Open new camera
            self.camera = cv2.VideoCapture(camera_id)
            
            if not self.camera.isOpened():
                self.log_event(f"Failed to open camera {camera_id}")
                return False
                
            # Read a frame to verify connection
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.log_event("Failed to capture frame from camera")
                self.camera.release()
                self.camera = None
                return False
            
            self.log_event(f"Connected to camera {camera_id} successfully")
            return True
            
        except Exception as e:
            self.log_event(f"Error connecting to camera: {str(e)}")
            if self.camera:
                self.camera.release()
                self.camera = None
            return False
    
    def start_camera(self, resolution=None):
        """Start camera processing"""
        if not self.camera:
            self.log_event("Cannot start camera - not connected")
            return False
        
        try:
            # Set resolution if provided
            if resolution:
                width, height = resolution
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Start streaming
            self.is_streaming = True
            
            # Start camera timer
            self.camera_timer.start(30)  # 30ms = ~33 fps
            
            self.log_event("Camera streaming started")
            return True
            
        except Exception as e:
            self.log_event(f"Error starting camera: {str(e)}")
            return False
    
    def stop_camera(self):
        """Stop camera processing"""
        if not self.is_streaming:
            return
            
        self.log_event("Stopping camera")
        self.is_streaming = False
        
        # Stop camera timer
        if self.camera_timer.isActive():
            self.camera_timer.stop()
        
        self.log_event("Camera stopped")
    
    def set_camera_settings(self, settings):
        """Apply camera settings"""
        if not self.camera:
            return False
            
        try:
            # Apply brightness
            if 'brightness' in settings:
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, settings['brightness'])
            
            # Apply contrast
            if 'contrast' in settings:
                self.camera.set(cv2.CAP_PROP_CONTRAST, settings['contrast'])
            
            # Apply resolution
            if 'width' in settings and 'height' in settings:
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings['width'])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings['height'])
            
            # Apply exposure
            if 'exposure' in settings:
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1 if settings['exposure'] != 0 else 3)  # 1 = manual, 3 = auto
                if settings['exposure'] != 0:
                    self.camera.set(cv2.CAP_PROP_EXPOSURE, settings['exposure'])
            
            self.log_event("Camera settings applied")
            return True
            
        except Exception as e:
            self.log_event(f"Error applying camera settings: {str(e)}")
            return False
    
    def on_connect_camera(self):
        """Connect to the selected camera"""
        camera_idx = self.camera_combo.currentIndex()
        self.log_event(f"Connecting to camera: {camera_idx}")
        
        if self.connect_camera(camera_idx):
            # Connection successful, enable other buttons
            self.start_stream_button.setEnabled(True)
            self.capture_button.setEnabled(True)
            self.apply_settings_button.setEnabled(True)
            self.log_event(f"Connected to camera {camera_idx} successfully")
        else:
            self.log_event(f"Failed to connect to camera {camera_idx}")
            
    def on_start_stream(self):
        """Start the video stream"""
        # Get current resolution
        width, height = [int(x) for x in self.resolution_combo.currentText().split('x')]
        resolution = (width, height)
        
        if self.start_camera(resolution):
            # Update button states
            self.stop_stream_button.setEnabled(True)
            self.start_stream_button.setEnabled(False)
            self.log_event("Video stream started")
        else:
            self.log_event("Failed to start video stream")
    
    def on_stop_stream(self):
        """Stop the video stream"""
        self.stop_camera()
        
        # Display "No video feed"
        self.video_label.setText("No video feed")
        self.processed_frame = None
        
        # Update button states
        self.stop_stream_button.setEnabled(False)
        self.start_stream_button.setEnabled(True)
        self.log_event("Video stream stopped")
            
    def on_capture_image(self):
        """Capture a still image"""
        if self.processed_frame is None:
            self.log_event("No frame to capture")
            return
            
        try:
            # Save current image
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            
            # Convert back to BGR before saving
            frame_to_save = cv2.cvtColor(self.processed_frame, cv2.COLOR_RGB2BGR)
            
            # Save image
            cv2.imwrite(filename, frame_to_save)
            self.log_event(f"Image captured and saved as {filename}")
            
        except Exception as e:
            self.log_event(f"Error capturing image: {str(e)}")
    
    def on_apply_settings(self):
        """Apply camera settings"""
        # Create settings dictionary
        settings = {}
        
        # Brightness
        brightness_map = {"Low": 0, "Medium": 50, "High": 100, "Auto": -1}
        settings['brightness'] = brightness_map[self.brightness_combo.currentText()]
        
        # Contrast
        contrast_map = {"Low": 0, "Medium": 50, "High": 100, "Auto": -1}
        settings['contrast'] = contrast_map[self.contrast_combo.currentText()]
        
        # Resolution
        width, height = [int(x) for x in self.resolution_combo.currentText().split('x')]
        settings['width'] = width
        settings['height'] = height
        
        # Exposure
        exposure_map = {"1/30": -5, "1/60": -6, "1/125": -7, "1/250": -8, "1/500": -9, "Auto": 0}
        settings['exposure'] = exposure_map[self.exposure_combo.currentText()]
        
        if self.set_camera_settings(settings):
            self.log_event("Camera settings applied")
        else:
            self.log_event("Failed to apply camera settings")
    
    def log_event(self, message):
        """Add a message to the event log"""
        time_str = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{time_str}] {message}")
    
    def cleanup_camera(self):
        """Release camera resources"""
        try:
            # Stop camera first
            self.stop_camera()
            
            # Release camera
            if self.camera:
                self.camera.release()
                self.camera = None
                
            self.log_event("Camera resources released")
        except Exception as e:
            self.log_event(f"Error cleaning up camera: {str(e)}")
        
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up camera resources before closing
        self.cleanup_camera()
        event.accept() 