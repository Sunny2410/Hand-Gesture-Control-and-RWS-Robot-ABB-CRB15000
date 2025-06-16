from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QSlider, QFrame, QGridLayout,
                           QLCDNumber, QRadioButton, QButtonGroup,
                           QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor

class ModernButton(QPushButton):
    """Modern button with customizable styling"""
    
    def __init__(self, text="", active_color="#2196F3", inactive_color="#EEEEEE", 
                 text_color="#FFFFFF", inactive_text_color="#333333", parent=None):
        super().__init__(text, parent)
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.text_color = text_color
        self.inactive_text_color = inactive_text_color
        self.setCheckable(True)
        
        # Set minimum size
        self.setMinimumHeight(40)
        
        # Set initial style
        self.setActive(False)
        
    def setActive(self, active):
        """Set button active state with appropriate styling"""
        self.setChecked(active)
        
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.active_color};
                    color: {self.text_color};
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self._lighten_color(self.active_color, 20)};
                }}
                QPushButton:pressed {{
                    background-color: {self._darken_color(self.active_color, 20)};
                    border: 2px solid #555;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.inactive_color};
                    color: {self.inactive_text_color};
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {self._darken_color(self.inactive_color, 10)};
                }}
                QPushButton:pressed {{
                    background-color: {self._darken_color(self.inactive_color, 20)};
                    border: 2px solid #555;
                }}
            """)
    
    def _lighten_color(self, color, amount=30):
        """Lighten a color by the given amount"""
        if color.startswith('#'):
            # Handle hex color
            if len(color) == 7:  # #RRGGBB format
                r = min(255, int(color[1:3], 16) + amount)
                g = min(255, int(color[3:5], 16) + amount)
                b = min(255, int(color[5:7], 16) + amount)
                return f"#{r:02x}{g:02x}{b:02x}"
        return color
        
    def _darken_color(self, color, amount=30):
        """Darken a color by the given amount"""
        if color.startswith('#'):
            # Handle hex color
            if len(color) == 7:  # #RRGGBB format
                r = max(0, int(color[1:3], 16) - amount)
                g = max(0, int(color[3:5], 16) - amount)
                b = max(0, int(color[5:7], 16) - amount)
                return f"#{r:02x}{g:02x}{b:02x}"
        return color


class PanelTab(QWidget):
    """Tab for robot panel control"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # Disable updates until initialized
        self.initialized = False
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== MASTERSHIP STATUS =====
        mastership_layout = QHBoxLayout()
        mastership_label = QLabel("Mastership:")
        mastership_label.setStyleSheet("font-weight: bold;")
        self.mastership_status = QLabel("Unlocked")
        
        # Mastership buttons
        self.lock_button = ModernButton("🔒", active_color="#2196F3", inactive_color="#EEEEEE")
        self.lock_button.setToolTip("Request Mastership")
        self.lock_button.setFixedSize(40, 30)
        self.lock_button.clicked.connect(self.on_request_mastership)
        
        self.unlock_button = ModernButton("🔓", active_color="#2196F3", inactive_color="#EEEEEE")
        self.unlock_button.setToolTip("Release Mastership")
        self.unlock_button.setFixedSize(40, 30)
        self.unlock_button.clicked.connect(self.on_release_mastership)
        
        mastership_controls = QHBoxLayout()
        mastership_controls.addWidget(self.lock_button)
        mastership_controls.addWidget(self.unlock_button)
        mastership_controls.setContentsMargins(0, 0, 0, 0)
        mastership_controls.setSpacing(0)
        
        mastership_layout.addWidget(mastership_label)
        mastership_layout.addWidget(self.mastership_status)
        mastership_layout.addStretch()
        mastership_layout.addLayout(mastership_controls)
        
        mastership_frame = QFrame()
        mastership_frame.setLayout(mastership_layout)
        mastership_frame.setFrameShape(QFrame.StyledPanel)
        mastership_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        
        main_layout.addWidget(mastership_frame)
        
        # ===== OPERATION MODE SECTION =====
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("font-weight: bold;")
        self.operation_mode_label = QLabel("Auto")
        
        mode_header = QHBoxLayout()
        mode_header.addWidget(mode_label)
        mode_header.addWidget(self.operation_mode_label)
        mode_header.addStretch()
        
        # Mode buttons
        mode_buttons = QHBoxLayout()
        
        self.auto_button = ModernButton("Auto", active_color="#2196F3", 
                                              inactive_color="#EEEEEE", text_color="#333333",
                                              inactive_text_color="#333333")
        self.auto_button.clicked.connect(lambda: self.set_operation_mode("auto"))
        
        self.manual_button = ModernButton("Manual",active_color="#2196F3", 
                                              inactive_color="#EEEEEE", text_color="#333333",
                                              inactive_text_color="#333333")
        self.manual_button.clicked.connect(lambda: self.set_operation_mode("man"))
        
        mode_buttons.addWidget(self.auto_button)
        mode_buttons.addWidget(self.manual_button)
        
        # Combined mode section
        mode_section = QVBoxLayout()
        mode_section.addLayout(mode_header)
        mode_section.addLayout(mode_buttons)
        
        mode_frame = QFrame()
        mode_frame.setLayout(mode_section)
        mode_frame.setFrameShape(QFrame.StyledPanel)
        mode_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        
        main_layout.addWidget(mode_frame)
        
        # ===== MOTOR CONTROL SECTION =====
        motor_label = QLabel("Motors:")
        motor_label.setStyleSheet("font-weight: bold;")
        self.motor_state_label = QLabel("On")
        
        motor_header = QHBoxLayout()
        motor_header.addWidget(motor_label)
        motor_header.addWidget(self.motor_state_label)
        motor_header.addStretch()
        
        # Motor buttons
        motor_buttons = QHBoxLayout()
        
        self.motors_off_button = ModernButton("Motors off", active_color="#2196F3", 
                                             inactive_color="#EEEEEE", text_color="#333333",
                                             inactive_text_color="#333333")
        self.motors_off_button.clicked.connect(lambda: self.set_motor_state("motorOff"))
        
        self.motors_on_button = ModernButton("Motors on", active_color="#2196F3", 
                                            inactive_color="#EEEEEE",
                                             text_color="#333333",
                                            inactive_text_color="#333333")
        self.motors_on_button.clicked.connect(lambda: self.set_motor_state("motorOn"))
        
        motor_buttons.addWidget(self.motors_off_button)
        motor_buttons.addWidget(self.motors_on_button)
        
        # Combined motor section
        motor_section = QVBoxLayout()
        motor_section.addLayout(motor_header)
        motor_section.addLayout(motor_buttons)
        
        motor_frame = QFrame()
        motor_frame.setLayout(motor_section)
        motor_frame.setFrameShape(QFrame.StyledPanel)
        motor_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        
        main_layout.addWidget(motor_frame)
        
        # ===== SPEED CONTROL SECTION =====
        speed_label = QLabel("Run Speed")
        speed_value = QLabel("0%")
        self.speed_value_label = speed_value
        
        speed_header = QHBoxLayout()
        speed_header.addWidget(speed_label)
        speed_header.addWidget(speed_value)
        
        # Speed slider
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(0)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #CCCCCC;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #8E24AA;
                border-radius: 4px;
            }
        """)
        self.speed_slider.valueChanged.connect(self.on_speed_slider_change)
        self.speed_slider.sliderReleased.connect(self.on_set_speed_click)
        
        # Combined speed section
        speed_section = QVBoxLayout()
        speed_section.addLayout(speed_header)
        speed_section.addWidget(self.speed_slider)
        
        speed_frame = QFrame()
        speed_frame.setLayout(speed_section)
        speed_frame.setFrameShape(QFrame.StyledPanel)
        speed_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        
        main_layout.addWidget(speed_frame)
        
        # ===== RESET PROGRAM BUTTON =====
        self.reset_program_button = QPushButton("Reset program (PP to main)")
        self.reset_program_button.setStyleSheet("""
            QPushButton {
                background-color: #EEEEEE;
                border: none;
                border-radius: 5px;
                padding: 10px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #DDDDDD;
            }
            QPushButton:pressed {
                background-color: #CCCCCC;
            }
        """)
        self.reset_program_button.clicked.connect(self.on_reset_program)
        
        main_layout.addWidget(self.reset_program_button)
        
        # Add spacer
        main_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))
        
        # ===== EXECUTION CONTROLS =====
        # RAPID Execution label
        rapid_label = QLabel("RAPID Execution:")
        rapid_label.setStyleSheet("font-weight: bold;")
        self.rapid_state_label = QLabel("Stopped")
        
        rapid_header = QHBoxLayout()
        rapid_header.addWidget(rapid_label)
        rapid_header.addWidget(self.rapid_state_label)
        rapid_header.addStretch()
        
        # Execution buttons
        execution_layout = QHBoxLayout()
        
        # Play button - LED style
        self.play_button = ModernButton("▶ Play", active_color="#4CAF50", 
                                       inactive_color="#EEEEEE", text_color="#FFFFFF",
                                       inactive_text_color="#333333")
        self.play_button.clicked.connect(self.on_play)
        
        # Stop button - LED style
        self.stop_button = ModernButton("■ Stop", active_color="#F44336", 
                                       inactive_color="#EEEEEE", text_color="#FFFFFF",
                                       inactive_text_color="#333333")
        self.stop_button.clicked.connect(self.on_stop)
        
        execution_layout.addWidget(self.play_button)
        execution_layout.addWidget(self.stop_button)
        
        # Combined execution section
        execution_section = QVBoxLayout()
        execution_section.addLayout(rapid_header)
        execution_section.addLayout(execution_layout)
        
        execution_frame = QFrame()
        execution_frame.setLayout(execution_section)
        execution_frame.setFrameShape(QFrame.StyledPanel)
        execution_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 5px;")
        
        main_layout.addWidget(execution_frame)
        
        # ===== MASTERSHIP CONTROLS =====
        mastership_buttons = QHBoxLayout()
        
        # Request mastership button
        self.request_mastership_button = QPushButton("Request Mastership")
        self.request_mastership_button.setStyleSheet("""
            QPushButton {
                background-color: #EEEEEE;
                border: none;
                border-radius: 5px;
                padding: 10px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #DDDDDD;
            }
        """)
        self.request_mastership_button.clicked.connect(self.on_request_mastership)
        
        # Release mastership button
        self.release_mastership_button = QPushButton("Release Mastership")
        self.release_mastership_button.setStyleSheet("""
            QPushButton {
                background-color: #EEEEEE;
                border: none;
                border-radius: 5px;
                padding: 10px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #DDDDDD;
            }
        """)
        self.release_mastership_button.clicked.connect(self.on_release_mastership)
        
        mastership_buttons.addWidget(self.request_mastership_button)
        mastership_buttons.addWidget(self.release_mastership_button)
        
        main_layout.addLayout(mastership_buttons)
        
        # Add stretch to push everything to the top
        main_layout.addStretch(1)
        
        # Event log is hidden in this modern design
        self.event_log = QLabel("")
        self.event_log.hide()
    
    def initialize(self, robot):
        """Initialize with robot reference and get initial state"""
        self.robot = robot
        
        pass
    
    def set_initial_values(self, initial_values):
        """Initialize with values from subscription"""
        if not initial_values:
            return
            
        try:
            # Extract controller state from panel data
            if '/rw/panel/ctrl-state' in initial_values:
                ctrl_state_resp = initial_values['/rw/panel/ctrl-state']
                if ctrl_state_resp.get('status_code') == 200:
                    # Extract ctrlstate from the response structure
                    ctrl_state = ctrl_state_resp.get('content', {}).get('state', [{}])[0].get('ctrlstate', 'Unknown')
                    motor_state = "On" if ctrl_state.lower() == "motoron" else "Off"
                    self.motor_state_label.setText(motor_state)
                    
                    # Update buttons to reflect current state
                    self.motors_on_button.setActive(motor_state == "On")
                    self.motors_off_button.setActive(motor_state == "Off")
            
            # Extract operation mode
            if '/rw/panel/opmode' in initial_values:
                op_mode_resp = initial_values['/rw/panel/opmode']
                if op_mode_resp.get('status_code') == 200:
                    # Extract opmode from the response structure
                    op_mode = op_mode_resp.get('content', {}).get('state', [{}])[0].get('opmode', 'Unknown')
                    self.operation_mode_label.setText(op_mode)
                    
                    # Update buttons to reflect current mode
                    self.auto_button.setActive(op_mode.upper() == "AUTO")
                    # ...existing code...
                    self.manual_button.setActive(
                        op_mode.upper() in ["MANUAL", "MAN", "MANR"]
                    )
# ...existing code...
            
            # Extract speed ratio
            if '/rw/panel/speedratio' in initial_values:
                speed_ratio_resp = initial_values['/rw/panel/speedratio']
                if speed_ratio_resp.get('status_code') == 200:
                    # Extract speedratio from the response structure
                    speed_ratio_str = speed_ratio_resp.get('content', {}).get('state', [{}])[0].get('speedratio', '0')
                    try:
                        speed_ratio = int(speed_ratio_str)
                        self.speed_slider.setValue(speed_ratio)
                        self.speed_value_label.setText(f"{speed_ratio}%")
                    except (ValueError, TypeError):
                        self.speed_slider.setValue(0)
                        self.speed_value_label.setText("0%")
            
            # Extract RAPID execution state
            if '/rw/rapid/execution;ctrlexecstate' in initial_values:
                exec_state_resp = initial_values['/rw/rapid/execution;ctrlexecstate']
                if exec_state_resp.get('status_code') == 200:
                    # Lấy trạng thái thực thi RAPID
                    exec_state = exec_state_resp.get('content', {}).get('state', [{}])[0].get('ctrlexecstate', 'Unknown')
                    rapid_state = "Unknown"
                    
                    if exec_state.lower() == "running":
                        rapid_state = "Running"
                        # Update execution buttons
                        self.play_button.setActive(True)
                        self.stop_button.setActive(False)
                    elif exec_state.lower() == "stopped":
                        rapid_state = "Stopped"
                        # Update execution buttons
                        self.play_button.setActive(False)
                        self.stop_button.setActive(True)
                    else:
                        rapid_state = "Ready"
                        # Update execution buttons
                        self.play_button.setActive(False)
                        self.stop_button.setActive(True)
                    
                    self.rapid_state_label.setText(rapid_state)
                    # Set color based on state
                    if rapid_state == "Running":
                        self.rapid_state_label.setStyleSheet("color: green; font-weight: bold;")
                    elif rapid_state == "Stopped":
                        self.rapid_state_label.setStyleSheet("color: red; font-weight: bold;")
                    else:
                        self.rapid_state_label.setStyleSheet("color: black; font-weight: bold;")
            
            # Mark as initialized
            self.initialized = True
            
            # Log initial values
            self.log_event("Panel state initialized from subscription data")
            
        except Exception as e:
            import traceback
            print(f"Error setting initial panel values: {str(e)}")
            print(traceback.format_exc())
    
    def update_ui(self):
        """Update UI with latest information from robot"""
        if not self.robot or not self.initialized:
            return
        
        # Get the latest subscription data if any
        # Most updates will happen through the main_window subscription handler
        pass
        
    def update_motor_state(self, motor_state):
        """Update just the motor state field"""
        if motor_state:
            # Convert "Running" to "On" for display
            display_state = "On" if motor_state == "Running" else "Off"
            self.motor_state_label.setText(display_state)
            print(f"Updating motor state to: {display_state}")
            
            # Update buttons to reflect current state - not to trigger actions
            self.motors_on_button.setActive(display_state == "On")
            self.motors_off_button.setActive(display_state == "Off")
                
            # Log the update
            self.log_event(f"Updated motor state: {display_state}")
            
    def update_operation_mode(self, op_mode):
        """Update just the operation mode field"""
        if op_mode:
            self.operation_mode_label.setText(op_mode)
            print(f"Updating operation mode to: {op_mode}")
            
            # Update buttons to reflect current mode - not to trigger actions
            self.auto_button.setActive(op_mode.upper() == "AUTO")
            # ...existing code...
            self.manual_button.setActive(
                op_mode.upper() in ["MANUAL", "MAN", "MANR"]
            )
# ...existing code...
                
            # Log the update
            self.log_event(f"Updated operation mode: {op_mode}")
            
    def update_rapid_state(self, rapid_state):
        """Update just the RAPID execution state field"""
        if rapid_state:
            self.rapid_state_label.setText(rapid_state)
            print(f"Updating RAPID state to: {rapid_state}")
            
            # Update buttons to reflect current RAPID state - not to trigger actions
            if rapid_state.upper() == "RUNNING":
                self.play_button.setActive(True)
                self.stop_button.setActive(False)
                # Update style
                self.rapid_state_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.play_button.setActive(False)
                self.stop_button.setActive(True)
                # Update style based on state
                if rapid_state.upper() == "STOPPED":
                    self.rapid_state_label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.rapid_state_label.setStyleSheet("color: black; font-weight: bold;")
            
            # Log the update
            self.log_event(f"Updated RAPID state: {rapid_state}")
            
    def update_speed_ratio(self, speed_ratio):
        """Update just the speed ratio field"""
        if speed_ratio:
            try:
                print(f"Updating speed ratio to: {speed_ratio}")
                speed_ratio_int = int(speed_ratio)
                self.speed_slider.setValue(speed_ratio_int)
                self.speed_value_label.setText(f"{speed_ratio_int}%")
                
                # Log the update
                self.log_event(f"Updated speed ratio: {speed_ratio}%")
            except (ValueError, TypeError):
                pass  # Ignore if speed ratio is not a valid number
    
    def update_mastership(self, mastership_status):
        """Update mastership status"""
        if mastership_status:
            self.mastership_status.setText(mastership_status)
            is_local = mastership_status.lower() == "local"
            self.lock_button.setActive(is_local)
            
            # Also update button state
            self.request_mastership_button.setEnabled(not is_local)
            self.release_mastership_button.setEnabled(is_local)

    def on_speed_slider_change(self, value):
        """Handle speed slider value change"""
        # Update display
        self.speed_value_label.setText(f"{value}%")
    
    def on_set_speed_click(self):
        """Set speed ratio on robot"""
        if not self.robot:
            return
            
        try:
            value = self.speed_slider.value()
            result = self.robot.panel.set_speed_ratio(value)
            
            if result.get('status_code') == 204:
                self.log_event(f"Set speed ratio to {value}%")
            else:
                self.log_event(f"Failed to set speed ratio: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error setting speed ratio: {str(e)}")
    
    def set_motor_state(self, state):
        """Set motor state directly when button is clicked"""
        if not self.robot:
            return
            
        try:
            # Only change state if different from current state
            current_state = self.motor_state_label.text()
            if (state == "motorOn" and current_state == "On") or \
               (state == "motorOff" and current_state == "Off"):
                return  # Already in this state
            
            # Apply state change to robot
            result = self.robot.panel.set_controller_state(state)
            
            if result.get('status_code') == 204:
                motor_state = "On" if state == "motorOn" else "Off"
                self.motor_state_label.setText(motor_state)
                
                # Update button states
                self.motors_on_button.setActive(state == "motorOn")
                self.motors_off_button.setActive(state == "motorOff")
                
                self.log_event(f"Set motor state to {state}")
            else:
                self.log_event(f"Failed to set motor state: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error setting motor state: {str(e)}")
    
    def set_operation_mode(self, mode):
        """Set operation mode directly when button is clicked"""
        if not self.robot:
            return
            
        try:
            # Only change mode if different from current mode
            current_mode = self.operation_mode_label.text().upper()
            if (mode == "auto" and current_mode == "AUTO") or \
               (mode == "man" and (current_mode == "MANUAL" or current_mode == "MANR" or current_mode == "MAN")):
                return  # Already in this mode
            
            # Apply mode change to robot
            result = self.robot.panel.set_operation_mode(mode)
            
            if result.get('status_code') == 202:
                self.log_event(f"Set operation mode to {mode}")
                
                # Update display label
                if mode == "auto":
                    self.operation_mode_label.setText("AUTO")
                    # Update button states - Auto is active, Manual is inactive
                    self.auto_button.setActive(True)
                    self.manual_button.setActive(False)
                elif mode == "man":
                    self.operation_mode_label.setText("MANUAL")
                    # Update button states - Auto is inactive, Manual is active
                    self.auto_button.setActive(False)
                    self.manual_button.setActive(True)
                
                # Check if we need to acknowledge operation mode
                if result.get('status_code') == 202:
                    # Need to acknowledge
                    self.log_event("Acknowledging operation mode change...")
                    ack_result = self.robot.panel.set_ackoperation_mode(mode)
                    
                    if ack_result.get('status_code') == 204:
                        self.log_event("Operation mode change acknowledged")
                    else:
                        self.log_event(f"Failed to acknowledge mode change: {ack_result.get('error', 'Unknown error')}")
            else:
                self.log_event(f"Failed to set operation mode: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error setting operation mode: {str(e)}")


    def on_request_mastership(self):
        """Request mastership"""
        if not self.robot:
            return
            
        try:
            result = self.robot.panel.set_mastership_request()
            
            if result.get('status_code') == 204:
                self.log_event("Mastership requested successfully")
                self.mastership_status.setText("Local")
                self.lock_button.setActive(True)
                self.unlock_button.setActive(False)  

                self.request_mastership_button.setEnabled(False)
                self.release_mastership_button.setEnabled(True)
            else:
                self.log_event(f"Failed to request mastership: {result.get('error', 'Unknown error')}")
                self.lock_button.setActive(False)
                
        except Exception as e:
            self.log_event(f"Error requesting mastership: {str(e)}")
    
    def on_release_mastership(self):
        """Release mastership"""
        if not self.robot:
            return
            
        try:
            result = self.robot.panel.set_mastership_release()
            
            if result.get('status_code') == 204:
                self.log_event("Mastership released successfully")
                self.mastership_status.setText("None")
                self.lock_button.setActive(False)
                self.unlock_button.setActive(True)  
                self.request_mastership_button.setEnabled(True)
                self.release_mastership_button.setEnabled(False)
            else:
                self.log_event(f"Failed to release mastership: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error releasing mastership: {str(e)}")
    
    def on_play(self):
        """Start program execution"""
        if not self.robot:
            return
            
        try:
            # Only start if currently not running
            if self.rapid_state_label.text() == "Running":
                return  # Already running
                
            result = self.robot.rapid.set_execution_start(
                regain='continue',
                execmode='continue',
                cycle='forever',
                condition='none',
                stopatbp='disabled',
                alltaskbytsp='true'
            )
            
            if result.get('status_code') == 204:
                self.log_event("Started program execution")
                # Update UI to show running state
                self.rapid_state_label.setText("Running")
                self.rapid_state_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Update buttons
                self.play_button.setActive(True)
                self.stop_button.setActive(False)
            else:
                self.log_event(f"Failed to start program: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error starting program: {str(e)}")
    
    def on_stop(self):
        """Stop program execution"""
        if not self.robot:
            return
            
        try:
            # Only stop if currently running
            if self.rapid_state_label.text() != "Running":
                return  # Not running
                
            result = self.robot.rapid.set_execution_stop(stopmode="stop", usetsp="normal")
            
            if result.get('status_code') == 204:
                self.log_event("Stopped program execution")
                # Update UI to show stopped state
                self.rapid_state_label.setText("Stopped")
                self.rapid_state_label.setStyleSheet("color: red; font-weight: bold;")
                
                # Update buttons
                self.play_button.setActive(False)
                self.stop_button.setActive(True)
            else:
                self.log_event(f"Failed to stop program: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error stopping program: {str(e)}")
    
    def on_reset_program(self):
        """Reset program to main"""
        if not self.robot:
            return
            
        try:
            # First stop execution
            stop_result = self.robot.rapid.set_execution_resetpp()
            
            if stop_result.get('status_code') == 204:
                # Then reset pointer
                reset_result = self.robot.rapid.set_execution_resetpp()
                
                if reset_result.get('status_code') == 204:
                    self.log_event("Program reset to main (PP reset)")
                else:
                    self.log_event(f"Failed to reset PP: {reset_result.get('error', 'Unknown error')}")
            else:
                self.log_event(f"Failed to stop program before reset: {stop_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error resetting program: {str(e)}")
    
    def log_event(self, message):
        """Add a message to the event log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        # Just print to console since we're not showing the event log in UI
        print(f"[{timestamp}] {message}")
        
        # Still update the hidden event log in case we need it later
        self.event_log.setText(f"[{timestamp}] {message}\n" + self.event_log.text()) 