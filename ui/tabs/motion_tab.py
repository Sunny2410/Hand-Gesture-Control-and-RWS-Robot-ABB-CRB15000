from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QDoubleSpinBox, QSlider, QTabWidget,
                           QSpinBox, QRadioButton, QButtonGroup, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor

class MotionTab(QWidget):
    """Tab for robot motion control"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # Disable updates until initialized
        self.initialized = False
        
        # Current mechunit
        self.current_mechunit = None
        
        # Timer for continuous jogging
        self.jog_timer = QTimer()
        self.jog_timer.setInterval(100)  # Gửi lệnh mỗi 100ms
        self.jog_timer.timeout.connect(self.on_jog_timer)
        self.current_jog_axis = None
        self.current_jog_value = 0
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Upper section - Mechanical unit selection and position display
        upper_layout = QHBoxLayout()
        
        # Mechanical unit selection
        mechunit_group = QGroupBox("Mechanical Unit")
        mechunit_layout = QFormLayout()
        
        # Mechunit combo
        self.mechunit_combo = QComboBox()
        self.mechunit_combo.currentIndexChanged.connect(self.on_mechunit_changed)
        mechunit_layout.addRow("Current Unit:", self.mechunit_combo)
        
        # Refresh button
        self.refresh_mechunits_button = QPushButton("Refresh")
        self.refresh_mechunits_button.clicked.connect(self.on_refresh_mechunits_click)
        mechunit_layout.addRow("", self.refresh_mechunits_button)
        
        # Apply layout to group
        mechunit_group.setLayout(mechunit_layout)
        upper_layout.addWidget(mechunit_group)
        
        # Current position display
        position_group = QGroupBox("Current Position")
        position_layout = QGridLayout()
        
        # Cartesian position
        position_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_label = QLabel("0.0")
        self.x_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.x_label, 0, 1)
        
        position_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_label = QLabel("0.0")
        self.y_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.y_label, 1, 1)
        
        position_layout.addWidget(QLabel("Z:"), 2, 0)
        self.z_label = QLabel("0.0")
        self.z_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.z_label, 2, 1)
        
        position_layout.addWidget(QLabel("Q1:"), 0, 2)
        self.q1_label = QLabel("0.0")
        self.q1_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.q1_label, 0, 3)
        
        position_layout.addWidget(QLabel("Q2:"), 1, 2)
        self.q2_label = QLabel("0.0")
        self.q2_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.q2_label, 1, 3)
        
        position_layout.addWidget(QLabel("Q3:"), 2, 2)
        self.q3_label = QLabel("0.0")
        self.q3_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.q3_label, 2, 3)
        
        position_layout.addWidget(QLabel("Q4:"), 3, 2)
        self.q4_label = QLabel("0.0")
        self.q4_label.setStyleSheet("font-weight: bold;")
        position_layout.addWidget(self.q4_label, 3, 3)

        # Apply layout to group
        position_group.setLayout(position_layout)
        upper_layout.addWidget(position_group)
        
        # Motion status
        status_group = QGroupBox("Motion Status")
        status_layout = QFormLayout()
        
        # Error state
        self.error_state_label = QLabel("Unknown")
        self.error_state_label.setStyleSheet("font-weight: bold;")
        status_layout.addRow("Error State:", self.error_state_label)
        
        
        # Apply layout to group
        status_group.setLayout(status_layout)
        upper_layout.addWidget(status_group)
        
        # Add upper layout to main layout
        main_layout.addLayout(upper_layout)
        
        # Current Joint Values display
        joint_values_group = QGroupBox("Current Joint Values")
        joint_values_layout = QGridLayout()
        
        # Joint values display
        joint_values_layout.addWidget(QLabel("Joint 1:"), 0, 0)
        self.joint1_label = QLabel("0.0°")
        self.joint1_label.setStyleSheet("font-weight: bold;")
        joint_values_layout.addWidget(self.joint1_label, 0, 1)
        
        joint_values_layout.addWidget(QLabel("Joint 2:"), 1, 0)
        self.joint2_label = QLabel("0.0°")
        self.joint2_label.setStyleSheet("font-weight: bold;")
        joint_values_layout.addWidget(self.joint2_label, 1, 1)
        
        joint_values_layout.addWidget(QLabel("Joint 3:"), 2, 0)
        self.joint3_label = QLabel("0.0°")
        self.joint3_label.setStyleSheet("font-weight: bold;")
        joint_values_layout.addWidget(self.joint3_label, 2, 1)
        
        joint_values_layout.addWidget(QLabel("Joint 4:"), 0, 2)
        self.joint4_label = QLabel("0.0°")
        self.joint4_label.setStyleSheet("font-weight: bold;")
        joint_values_layout.addWidget(self.joint4_label, 0, 3)
        
        joint_values_layout.addWidget(QLabel("Joint 5:"), 1, 2)
        self.joint5_label = QLabel("0.0°")
        self.joint5_label.setStyleSheet("font-weight: bold;")
        joint_values_layout.addWidget(self.joint5_label, 1, 3)
        
        joint_values_layout.addWidget(QLabel("Joint 6:"), 2, 2)
        self.joint6_label = QLabel("0.0°")
        self.joint6_label.setStyleSheet("font-weight: bold;")
        joint_values_layout.addWidget(self.joint6_label, 2, 3)
        
        # Refresh button for joints
        self.refresh_joints_button = QPushButton("Refresh Joint Values")
        self.refresh_joints_button.clicked.connect(self.on_refresh_joints_click)
        joint_values_layout.addWidget(self.refresh_joints_button, 3, 0, 1, 4)
        
        # Apply layout to group
        joint_values_group.setLayout(joint_values_layout)
        main_layout.addWidget(joint_values_group)
        
        # Jogging controls
        self.setup_jogging_controls()
        
        # Add a fixed-size placeholder for event log
        log_group = QGroupBox("Motion Events")
        log_layout = QVBoxLayout()
        
        log_scroll = QScrollArea()
        log_scroll.setWidgetResizable(True)
        log_scroll.setMaximumHeight(600)  # Fixed height
        
        log_content = QWidget()
        log_content_layout = QVBoxLayout(log_content)
        
        self.event_log = QLabel("Motion events will be displayed here...")
        self.event_log.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.event_log.setStyleSheet("background-color: #F0F0F0; border: 1px solid #CCC; padding: 5px;")
        self.event_log.setWordWrap(True)
        log_content_layout.addWidget(self.event_log)
        log_content_layout.addStretch()
        
        log_scroll.setWidget(log_content)
        log_layout.addWidget(log_scroll)
        
        # Apply layout to group
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
    
    def setup_jogging_controls(self):
        """Set up the jogging control with sliders"""
        jog_group = QGroupBox("Jogging Controls")
        jog_layout = QVBoxLayout()
        
        # Axis slider group
        axes_group = QGridLayout()
        
        # Define axes names and indices
        axes = [
            {"name": "Joint 1", "axis": 1},
            {"name": "Joint 2", "axis": 2},
            {"name": "Joint 3", "axis": 3},
            {"name": "Joint 4", "axis": 4},
            {"name": "Joint 5", "axis": 5},
            {"name": "Joint 6", "axis": 6}
        ]
        
        # Create sliders for each axis
        self.jog_sliders = {}
        self.jog_value_labels = {}
        
        for i, axis_info in enumerate(axes):
            row = i // 2
            col_start = (i % 2) * 3
            
            # Label
            axes_group.addWidget(QLabel(f"{axis_info['name']}:"), row, col_start)
            
            # Value display
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setMinimumWidth(30)
            axes_group.addWidget(value_label, row, col_start + 2)
            self.jog_value_labels[axis_info['axis']] = value_label
            
            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(-100)
            slider.setMaximum(100)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(25)
            
            # Connect slider value changed and released events
            slider.valueChanged.connect(lambda value, axis=axis_info['axis']: self.on_jog_slider_change(axis, value))
            slider.sliderReleased.connect(lambda axis=axis_info['axis']: self.on_jog_slider_released(axis))
            
            axes_group.addWidget(slider, row, col_start + 1)
            self.jog_sliders[axis_info['axis']] = slider
        
        # Jogging settings
        settings_layout = QFormLayout()
        
        # Increment mode
        self.increment_combo = QComboBox()
        self.increment_combo.addItems(["Small", "Medium", "Large", "User"])
        settings_layout.addRow("Increment:", self.increment_combo)
        
        # Add layouts to main layout
        jog_layout.addLayout(axes_group)
        jog_layout.addLayout(settings_layout)
        
        # Apply layout to group
        jog_group.setLayout(jog_layout)
        self.layout().addWidget(jog_group)
    
    def initialize(self, robot):
        """Initialize with robot reference and get initial state"""
        self.robot = robot
        
        # Load mechanical units
        self.load_mechunits()
        self.set_initial_values()
        # Set initialized flag
        self.initialized = True
        self.log_event("Motion control initialized")
        
    def set_initial_values(self):
        """Update with initial values from subscription"""
        error_state = self.robot.motion.get_error_state()
        print(error_state)
        if error_state.get('status_code') == 200 and 'content' in error_state:
                state_list = error_state['content'].get('state', [])
                if state_list and isinstance(state_list, list):
                    state = state_list[0].get('err-state', 'Unknown')
                else:
                    state = 'Unknown'
                self.error_state_label.setText(state)
            
    
    def update_ui(self):
        """Periodic UI update"""
        if not self.robot or not self.initialized:
            return
        
        # Update current position if a mechunit is selected
        if self.current_mechunit:
            self.update_current_position()
            self.update_current_joints()
    
    def load_mechunits(self):
        """Load available mechanical units"""
        if not self.robot:
            return
            
        try:
            # Get mechunits
            result = self.robot.motion.get_mechunits()
            
            if result.get('status_code') == 200 and 'content' in result:
                # Clear combo box
                self.mechunit_combo.clear()
                
                # Add mechunits
                if '_embedded' in result['content'] and 'resources' in result['content']['_embedded']:
                    mechunits = result['content']['_embedded']['resources']
                    for mechunit in mechunits:
                        name = mechunit.get('_title', 'Unknown')  # Sửa lại từ 'name' thành '_title'
                        self.mechunit_combo.addItem(name, mechunit)
                    
                    # Select first mechunit if available
                    if self.mechunit_combo.count() > 0:
                        self.mechunit_combo.setCurrentIndex(0)
                        self.current_mechunit = self.mechunit_combo.currentText()
                        
                        # Set this mechunit for jogging
                        self.robot.motion.set_mechunit_for_jogging(self.current_mechunit)
                        
                        # Update position
                        self.update_current_position()
                        self.update_current_joints()
            else:
                self.log_event(f"Failed to load mechunits: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error loading mechunits: {str(e)}")
    
    def on_refresh_mechunits_click(self):
        """Refresh mechunits list"""
        self.load_mechunits()
    
    def on_mechunit_changed(self, index):
        """Handle mechunit selection change"""
        if index < 0 or not self.robot:
            return
            
        # Get selected mechunit
        self.current_mechunit = self.mechunit_combo.currentText()
        
        # Set this mechunit for jogging
        try:
            self.robot.motion.set_mechunit_for_jogging(self.current_mechunit)
            self.log_event(f"Set mechunit {self.current_mechunit} for jogging")
            
            # Update position
            self.update_current_position()
            self.update_current_joints()
            
        except Exception as e:
            self.log_event(f"Error setting mechunit for jogging: {str(e)}")
    
    def update_current_position(self):
        """Update current position display"""
        if not self.robot or not self.current_mechunit:
            return
            
        try:
            # Get current position
            result = self.robot.motion.get_mechunit_robtarget(self.current_mechunit)
            print(result)
            if result.get('status_code') == 200 and 'content' in result:
                state_list = result['content'].get('state', [])
                if state_list and isinstance(state_list, list):
                    state = state_list[0]
                    pos_x = float(state.get('x', 0.0))
                    pos_y = float(state.get('y', 0.0))
                    pos_z = float(state.get('z', 0.0))
                    orient_q1 = float(state.get('q1', 0.0))
                    orient_q2 = float(state.get('q2', 0.0))
                    orient_q3 = float(state.get('q3', 0.0))
                    orient_q4 = float(state.get('q4', 0.0))
                else:
                    pos_x = pos_y = pos_z = orient_q1 = orient_q2 = orient_q3 = orient_q4 = 0.0

                # Định dạng 3 chữ số thập phân
                pos_x = f"{pos_x:.3f}"
                pos_y = f"{pos_y:.3f}"
                pos_z = f"{pos_z:.3f}"
                orient_q1 = f"{orient_q1:.3f}"
                orient_q2 = f"{orient_q2:.3f}"
                orient_q3 = f"{orient_q3:.3f}"
                orient_q4 = f"{orient_q4:.3f}"
                
                # Update labels
                self.x_label.setText(pos_x)
                self.y_label.setText(pos_y)
                self.z_label.setText(pos_z)
                self.q1_label.setText(orient_q1)
                self.q2_label.setText(orient_q2)
                self.q3_label.setText(orient_q3)
                self.q4_label.setText(orient_q4)
                
                # Log update
                self.log_event("Updated position values")
            else:
                self.log_event(f"Failed to get position: {result.get('error', 'Unknown error')}")
        except Exception as e:
            self.log_event(f"Error getting position: {str(e)}")
    
    def update_current_joints(self):
        """Update current joint values display"""
        if not self.robot or not self.current_mechunit:
            return
            
        try:
            # Get current joint values
            result = self.robot.motion.get_mechunit_jointtarget(self.current_mechunit)
            print(result)
            if result.get('status_code') == 200 and 'content' in result:
                # Extract joint values
                state_list = result['content'].get('state', [])
                if state_list and isinstance(state_list, list):
                    state = state_list[0]
                    # Robot joints
                    self.joint1_label.setText(f"{float(state.get('rax_1', 0.0)):.3f}°")
                    self.joint2_label.setText(f"{float(state.get('rax_2', 0.0)):.3f}°")
                    self.joint3_label.setText(f"{float(state.get('rax_3', 0.0)):.3f}°")
                    self.joint4_label.setText(f"{float(state.get('rax_4', 0.0)):.3f}°")
                    self.joint5_label.setText(f"{float(state.get('rax_5', 0.0)):.3f}°")
                    self.joint6_label.setText(f"{float(state.get('rax_6', 0.0)):.3f}°")
                    # Log update
                    self.log_event("Updated joint values")
                else:
                    self.log_event("No joint state data found")
            else:
                self.log_event(f"Failed to get joint values: {result.get('error', 'Unknown error')}")
        except Exception as e:
            self.log_event(f"Error getting joint values: {str(e)}")
            
    def on_refresh_joints_click(self):
        """Refresh joint values display"""
        self.update_current_joints()
    
    def on_jog_slider_change(self, axis, value):
        """Handle jog slider value change"""
        # Update value label
        self.jog_value_labels[axis].setText(str(value))
        
        # Store current jogging values
        self.current_jog_axis = axis
        self.current_jog_value = value
        
        # Perform jogging if slider is not at zero
        if value != 0:
            # Execute jog command immediately
            self.jog_axis(axis, value)
            
            # Start timer for continuous jogging
            if not self.jog_timer.isActive():
                self.jog_timer.start()
            else:
            # Stop timer if value is zero
                if self.jog_timer.isActive():
                    self.jog_timer.stop()
                    self.current_jog_axis = None
        
    def on_jog_slider_released(self, axis):
        """Handle jog slider release - reset to zero"""
        # Reset slider to zero
        self.jog_sliders[axis].setValue(0)
        self.jog_value_labels[axis].setText("0")
        
        # Stop motion for this axis
        self.jog_axis(axis, 0)
        
        # Stop timer
        if self.jog_timer.isActive():
            self.jog_timer.stop()
        
        self.current_jog_axis = None
        self.current_jog_value = 0
    
    def on_jog_timer(self):
        """Handle timer event for continuous jogging"""
        if self.current_jog_axis is not None and self.current_jog_value != 0:
            # Re-send the jogging command
            self.jog_axis(self.current_jog_axis, self.current_jog_value)
            
    def jog_axis(self, axis, value):
        """Jog specified axis with specified value"""
        if not self.robot or not self.current_mechunit:
            return
            
        try:
            # Convert value to appropriate jog value (-100 to 100 maps to full range)
            # The increment affects how fast the robot moves
            increment = self.increment_combo.currentText()
            
            # Map slider value to axis values
            # Create array of 6 zeros
            axis_values = ["0"] * 6
            
            # Set the value for specified axis (adjust for 0-based index)
            axis_values[axis-1] = str(value)
            
            # Execute jog command
            result = self.robot.motion.jog_multiple_axes(
                axis1=axis_values[0],
                axis2=axis_values[1],
                axis3=axis_values[2],
                axis4=axis_values[3],
                axis5=axis_values[4],
                axis6=axis_values[5],
                ccount="0",  # Use 0 for continuous jogging
                inc_mode=increment.lower(),
                token="0"  # Empty token for manual jogging
            )
            
            if result.get('status_code') not in [200, 201, 202, 204]:
                self.log_event(f"Jog error: {result.get('error', 'Unknown error')}")
                if self.jog_timer.isActive():
                    self.jog_timer.stop()
                
        except Exception as e:
            self.log_event(f"Error jogging axis {axis}: {str(e)}")
            if self.jog_timer.isActive():
                self.jog_timer.stop()
    
    def log_event(self, message):
        """Add a message to the event log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        current_text = self.event_log.text()
        # Keep only last 15 messages
        lines = current_text.split('\n')
        if len(lines) > 15:
            lines = lines[:15]  # Keep most recent messages
        
        new_text = f"[{timestamp}] {message}\n" + '\n'.join(lines)
        self.event_log.setText(new_text)
    
    def update_motion_data(self, motion_data):
        """Xử lý sự kiện motion từ robot"""

        try:

            self.error_state_label.setText(motion_data)
            self.log_event(f"Updated error state: {motion_data}")
                
        except Exception as e:
            self.log_event(f"Error processing motion event: {str(e)}") 
    
