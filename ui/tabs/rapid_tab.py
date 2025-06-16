from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QTabWidget, QSplitter, QTextEdit, QListWidget,
                           QTreeWidget, QTreeWidgetItem, QRadioButton,
                           QButtonGroup, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor

class RAPIDTab(QWidget):
    """Tab for robot RAPID program control"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # Disable updates until initialized
        self.initialized = False
        
        # Current task and module info
        self.current_task = None
        self.current_module = None
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Execution control at top
        exec_group = QGroupBox("Execution Control")
        exec_layout = QGridLayout()
        
        # Current execution state
        exec_layout.addWidget(QLabel("Current state:"), 0, 0)
        self.exec_state_label = QLabel("Unknown")
        self.exec_state_label.setStyleSheet("font-weight: bold;")
        exec_layout.addWidget(self.exec_state_label, 0, 1)
        
        # Current task
        exec_layout.addWidget(QLabel("Current task:"), 0, 2)
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self.on_task_changed)
        exec_layout.addWidget(self.task_combo, 0, 3)
        
        # RAPID execution control buttons
        self.start_button = QPushButton("Start")
        self.start_button.setIcon(QIcon("ui/resources/play.png"))
        self.start_button.clicked.connect(self.on_start_click)
        exec_layout.addWidget(self.start_button, 1, 0)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setIcon(QIcon("ui/resources/stop.png"))
        self.stop_button.clicked.connect(self.on_stop_click)
        exec_layout.addWidget(self.stop_button, 1, 1)
        
        self.reset_pp_button = QPushButton("Reset PP")
        self.reset_pp_button.setIcon(QIcon("ui/resources/reset.png"))
        self.reset_pp_button.clicked.connect(self.on_reset_pp_click)
        exec_layout.addWidget(self.reset_pp_button, 1, 2)
        
        # Cycle selection
        self.cycle_combo = QComboBox()
        self.cycle_combo.addItems(["Once", "Forever"])
        exec_layout.addWidget(QLabel("Cycle:"), 1, 3)
        exec_layout.addWidget(self.cycle_combo, 1, 4)
        
        # Start mode options
        start_options_group = QGroupBox("Start Options")
        start_options_layout = QGridLayout()
        
        # Regain mode
        start_options_layout.addWidget(QLabel("Regain:"), 0, 0)
        self.regain_combo = QComboBox()
        self.regain_combo.addItems(["continue", "regain", "clear", "continueconsume"])
        start_options_layout.addWidget(self.regain_combo, 0, 1)
        
        # Exec mode
        start_options_layout.addWidget(QLabel("Exec Mode:"), 1, 0)
        self.exec_mode_combo = QComboBox()
        self.exec_mode_combo.addItems(["continue", "stepin", "stepover", "stepout", "stepback", "steplast", "stepmotion"])
        start_options_layout.addWidget(self.exec_mode_combo, 1, 1)
        
        # Condition
        start_options_layout.addWidget(QLabel("Condition:"), 2, 0)
        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["none", "callchain"])
        start_options_layout.addWidget(self.condition_combo, 2, 1)
        
        # Stop at breakpoint
        start_options_layout.addWidget(QLabel("Stop at BP:"), 0, 2)
        self.stopatbp_combo = QComboBox()
        self.stopatbp_combo.addItems(["disabled", "enabled"])
        start_options_layout.addWidget(self.stopatbp_combo, 0, 3)
        
        # All tasks by TSP
        start_options_layout.addWidget(QLabel("All Tasks:"), 1, 2)
        self.alltasks_combo = QComboBox()
        self.alltasks_combo.addItems(["false", "true"])
        start_options_layout.addWidget(self.alltasks_combo, 1, 3)
        
        # Apply layout to group
        start_options_group.setLayout(start_options_layout)
        exec_layout.addWidget(start_options_group, 2, 0, 1, 5)
        
        # Apply layout to group
        exec_group.setLayout(exec_layout)
        main_layout.addWidget(exec_group)
              
        # Add a placeholder for event log
        log_group = QGroupBox("RAPID Events")
        log_layout = QVBoxLayout()
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setStyleSheet("background-color: #F0F0F0; border: 1px solid #CCC; padding: 5px;")
        self.event_log.setMaximumHeight(800)
        log_layout.addWidget(self.event_log)
        
        # Apply layout to group
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
    
    def initialize(self, robot):
        """Initialize with robot reference and load initial state"""
        self.robot = robot
        
        # Get execution state
        try:
            exec_state = self.robot.rapid.get_execution_state()
            print(exec_state)
            if exec_state.get('status_code') == 200 and 'content' in exec_state:
                state = exec_state['content']['state'][0].get('ctrlexecstate', '')
                if state == "running":
                    state = "Running"
                elif state == "stopped":
                    state = "Stopped"
                else:
                    state = "Ready"
                            
                self.exec_state_label.setText(state)
                
                # Enable/disable buttons based on state
                self.update_button_state(state)
            
            # Get available tasks
            self.load_tasks()

                
            # Set initialized flag
            self.initialized = True
            self.log_event("RAPID control initialized")
            
        except Exception as e:
            self.log_event(f"Error initializing RAPID tab: {str(e)}")
    
    def set_initial_values(self, initial_values):
        """Update with initial values from subscription"""
        # This will be called once subscriptions are set up
        # Update UI with any values provided
        pass
    
    def update_ui(self):
        """Periodic UI update"""
        if not self.robot or not self.initialized:
            return
        pass

    def update_rapid_state(self, rapid_state):
        """Update just the RAPID execution state field"""
        if rapid_state:
            self.exec_state_label.setText(rapid_state)
            print(f"Updating RAPID state to: {rapid_state}")
            self.update_button_state(rapid_state)

            # Log the update
            self.log_event(f"Updated RAPID state: {rapid_state}")

    def load_tasks(self):
        """Load available RAPID tasks"""
        if not self.robot:
            return
            
        try:
            # Get tasks
            result = self.robot.rapid.get_tasks()
            
            if result.get('status_code') == 200 and 'content' in result:
                # Clear existing items
                self.task_combo.clear()
                
                # Process tasks
                if '_embedded' in result['content'] and 'resources' in result['content']['_embedded']:
                    tasks = result['content']['_embedded']['resources']
                    
                    for task in tasks:
                        name = task.get('name', 'Unknown')
                        if name != 'Unknown':

                            self.task_combo.addItem(name, task)
                    
                    self.log_event(f"Loaded {len(tasks)} tasks")
                    
                    if self.task_combo.count() > 0:
                        self.task_combo.setCurrentIndex(0)
                        self.current_task = self.task_combo.currentText()
                else:
                    self.log_event("No tasks found")
            else:
                self.log_event(f"Error loading tasks: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error loading tasks: {str(e)}")
    
    def on_task_changed(self, index):
        """Handle task selection change"""
        if index < 0:
            return
            
        task_name = self.task_combo.currentText()
        self.current_task = task_name
        self.log_event(f"Selected task: {task_name}")
        
    
    def on_start_click(self):
        """Start program execution"""
        if not self.robot:
            return
            
        try:
            # Get start parameters
            regain = self.regain_combo.currentText()
            execmode = self.exec_mode_combo.currentText()
            cycle = self.cycle_combo.currentText().lower()
            condition = self.condition_combo.currentText()
            stopatbp = self.stopatbp_combo.currentText()
            alltaskbytsp = self.alltasks_combo.currentText()
            
            # Start execution
            self.log_event("Starting program execution...")
            result = self.robot.rapid.set_execution_start(
                regain=regain,
                execmode=execmode,
                cycle=cycle,
                condition=condition,
                stopatbp=stopatbp,
                alltaskbytsp=alltaskbytsp
            )
            
            if result.get('status_code') in [200, 202, 204]:
                self.log_event("Program execution started successfully")
                # Update state immediately
                self.exec_state_label.setText("Running")
                self.update_button_state("Running")
            else:
                self.log_event(f"Failed to start execution: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error starting execution: {str(e)}")
    
    def on_stop_click(self):
        """Stop program execution"""
        if not self.robot:
            return
            
        try:
            # Stop execution
            self.log_event("Stopping program execution...")
            result = self.robot.rapid.set_execution_stop(stopmode="stop", usetsp="normal")
            
            if result.get('status_code') in [200, 202, 204]:
                self.log_event("Program execution stopped successfully")
                # Update state immediately
                self.exec_state_label.setText("Stopped")
                self.update_button_state("Stopped")
            else:
                self.log_event(f"Failed to stop execution: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error stopping execution: {str(e)}")
    
    def on_reset_pp_click(self):
        """Reset program pointer"""
        if not self.robot:
            return
            
        try:
            # Reset program pointer
            self.log_event("Resetting program pointer...")
            result = self.robot.rapid.set_execution_resetpp()
            
            if result.get('status_code') in [200, 202, 204]:
                self.log_event("Program pointer reset successfully")
            else:
                self.log_event(f"Failed to reset program pointer: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error resetting program pointer: {str(e)}")
    
    def update_button_state(self, state):
        """Update button state based on execution state"""
        if state == "Running":
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.reset_pp_button.setEnabled(False)
        elif state == "Stopped":
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.reset_pp_button.setEnabled(True)
        else:  # unknown or other states
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.reset_pp_button.setEnabled(True)
    
    def log_event(self, message):
        """Add a message to the event log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {message}") 