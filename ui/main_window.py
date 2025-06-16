import logging
import time
import json
from PyQt5.QtWidgets import (QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                           QComboBox, QGroupBox, QGridLayout, QSpinBox,
                           QDoubleSpinBox, QFrame, QSplitter, QAction, 
                           QStatusBar, QToolBar, QTextEdit, QCheckBox,
                           QMessageBox, QSlider, QFormLayout, QScrollArea,
                           QDockWidget, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# Import tab widgets
from ui.tabs.connection_tab import ConnectionTab
from ui.tabs.panel_tab import PanelTab
from ui.tabs.io_tab import IOTab
from ui.tabs.motion_tab import MotionTab
from ui.tabs.rapid_tab import RAPIDTab
from ui.tabs.system_tab import SystemTab
from ui.tabs.robot_control_tab import RobotControlTab

# Import custom widgets
from ui.widgets.log_widget import LogWidget
from ui.widgets.status_widget import StatusWidget

# Import backend robot controller
from API.abb_robot import ABBRobot


class ABBRobotControlUI(QMainWindow):
    """Main window for ABB Robot Control application"""
    
    def __init__(self, logger=None):
        super().__init__()
        
        # Setup logger
        self.logger = logger or logging.getLogger('ABBRobotUI')
        
        # Initialize robot object
        self.robot = None
        
        # Setup UI
        self.setWindowTitle("ABB Robot Control")
        self.setMinimumSize(1280, 800)
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create main splitter between tabs and log area
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.main_splitter)
        
        # Create tab container
        self.tab_container = QWidget()
        self.tab_layout = QVBoxLayout(self.tab_container)
        self.tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_layout.addWidget(self.tab_widget)
        
        # Add tabs
        self.connection_tab = ConnectionTab(self.connect_to_robot)
        self.tab_widget.addTab(self.connection_tab, "Connection")
        
        # Create Panel Panel Tab as a dock widget (not in tab widget)
        self.panel_tab = PanelTab()
        self.panel_dock = QDockWidget("Control Panel", self)
        self.panel_dock.setWidget(self.panel_tab)
        self.panel_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.panel_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.panel_dock)
        # Hide the dock initially - will be shown after connection
        self.panel_dock.hide()
        
        # These tabs will be enabled only after connection
        self.io_tab = IOTab()
        self.tab_widget.addTab(self.io_tab, "I/O")
        
        self.motion_tab = MotionTab()
        self.tab_widget.addTab(self.motion_tab, "Motion")
        
        self.rapid_tab = RAPIDTab()
        self.tab_widget.addTab(self.rapid_tab, "RAPID")
        
        self.robot_control_tab = RobotControlTab()
        self.tab_widget.addTab(self.robot_control_tab, "Robot Control")
        
        self.system_tab = SystemTab()
        self.tab_widget.addTab(self.system_tab, "User Management")
        
        # Disable all tabs except connection at startup
        self.set_tabs_enabled(False)
        
        # Add tab widget to splitter
        self.main_splitter.addWidget(self.tab_container)
        
        # Create log widget
        self.log_widget = LogWidget(self.logger)
        self.main_splitter.addWidget(self.log_widget)
        
        # Set splitter sizes - 70% for tabs, 30% for log
        self.main_splitter.setSizes([700, 300])
        
        # Create status bar
        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget, 1)
        
        # Create toolbar
        self.setup_toolbar()
        
        # Load settings
        self.load_settings()
        
        # Setup update timer for UI
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # Update UI every second
    
    def setup_toolbar(self):
        """Set up the main toolbar"""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(self.toolbar)
        
        # Connect action
        self.connect_action = QAction(QIcon("ui/resources/connect.png"), "Connect", self)
        self.connect_action.triggered.connect(self.connect_toolbar)
        self.toolbar.addAction(self.connect_action)
        
        # Disconnect action
        self.disconnect_action = QAction(QIcon("ui/resources/disconnect.png"), "Disconnect", self)
        self.disconnect_action.triggered.connect(self.disconnect_robot)
        self.disconnect_action.setEnabled(False)
        self.toolbar.addAction(self.disconnect_action)
        
        self.toolbar.addSeparator()
        
        # Emergency stop action
        self.estop_action = QAction(QIcon("ui/resources/emergency.png"), "Emergency Stop", self)
        self.estop_action.triggered.connect(self.emergency_stop)
        self.estop_action.setEnabled(False)
        self.toolbar.addAction(self.estop_action)
        
        self.toolbar.addSeparator()
        
        # Settings action
        self.settings_action = QAction(QIcon("ui/resources/settings.png"), "Settings", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.toolbar.addAction(self.settings_action)
        
        # Help action
        self.help_action = QAction(QIcon("ui/resources/help.png"), "Help", self)
        self.help_action.triggered.connect(self.open_help)
        self.toolbar.addAction(self.help_action)
    
    def connect_toolbar(self):
        """Handle connect action from toolbar"""
        # Switch to connection tab
        self.tab_widget.setCurrentIndex(0)
        # Call connect button click handler in connection tab
        self.connection_tab.connect_button.click()
    
    def connect_to_robot(self, host, username, password, protocol="https://"):
        """Connect to the robot controller"""
        try:
            self.logger.info(f"Connecting to robot at {host}")
            
            # Create robot object
            self.robot = ABBRobot(
                host=host,
                username=username,
                password=password,
                protocol=protocol,
                debug=True
            )
            
            # Attempt connection
            success = self.robot.connect()
            
            if success:
                self.logger.info("Connected successfully")
                self.set_tabs_enabled(True)
                self.connection_tab.set_connected(True)
                self.disconnect_action.setEnabled(True)
                self.connect_action.setEnabled(False)
                self.estop_action.setEnabled(True)
                
                # Show the panel dock widget
                self.panel_dock.show()
                
                # Update status widget
                self.status_widget.set_status("Connected", "green")
                
                # Setup combined subscription first
                self.setup_subscriptions()
                
                # Initialize the last subscription update time
                self._last_subscription_update = time.time()
                
                # Set initial controller information with default values first
                # These will be updated by subscription data
                self.connection_tab.set_controller_info(
                    "OmniCore Controller C30",  # controller_version 
                    "7.8",                     # robotware_version
                    "Unknown",                 # controller_state
                    "Unknown",                 # motor_state - will be updated via subscription
                    "Unknown"                  # rapid_state - will be updated via subscription
                )
                
                # Get initial values from subscription
                initial_values = self.robot.get_initial_values()
                print(initial_values)

                # Update controller info from initial values if available
                try:
                    # Get values directly from endpoints if available
                    ctrl_state_data = initial_values.get('/rw/panel/ctrl-state', {})
                    op_mode_data = initial_values.get('/rw/panel/opmode', {})
                    speed_ratio_data = initial_values.get('/rw/panel/speedratio', {})
                    rapid_exec_data = initial_values.get('/rw/rapid/execution;ctrlexecstate', {})
                    user_data = initial_values.get('/rw/rmpp/user-info', {})
                    
                    # Extract values safely with proper error handling
                    ctrl_state = 'Unknown'
                    if (ctrl_state_data and 'content' in ctrl_state_data and 
                        'state' in ctrl_state_data['content'] and 
                        len(ctrl_state_data['content']['state']) > 0):
                        ctrl_state = ctrl_state_data['content']['state'][0].get('ctrlstate', 'Unknown')
                    
                    op_mode = 'Unknown'
                    if (op_mode_data and 'content' in op_mode_data and 
                        'state' in op_mode_data['content'] and 
                        len(op_mode_data['content']['state']) > 0):
                        op_mode = op_mode_data['content']['state'][0].get('opmode', 'Unknown')
                    
                    speed_ratio = '0'
                    if (speed_ratio_data and 'content' in speed_ratio_data and 
                        'state' in speed_ratio_data['content'] and 
                        len(speed_ratio_data['content']['state']) > 0):
                        speed_ratio = speed_ratio_data['content']['state'][0].get('speedratio', '0')
                    
                    # Extract motor state from controller state
                    motor_state = "Running" if ctrl_state.lower() == "motoron" else "Stopped"
                    
                    # Update connection tab with controller state
                    self.connection_tab.update_controller_state(op_mode, motor_state)
                    

                    if (rapid_exec_data and 'content' in rapid_exec_data and 
                            'state' in rapid_exec_data['content'] and 
                            len(rapid_exec_data['content']['state']) > 0):
                            rapid_exec_state = rapid_exec_data['content']['state'][0].get('ctrlexecstate', '')
                        
                    rapid_state = "Unknown"
                    if rapid_exec_state == "running":
                            rapid_state = "Running"
                    elif rapid_exec_state == "stopped":
                            rapid_state = "Stopped"
                    else:
                            rapid_state = "Ready"
                            
                    self.connection_tab.update_rapid_state(rapid_state)

                    self.logger.info(f"Initial values: Motor state: {motor_state}, Operation mode: {op_mode}, Speed ratio: {speed_ratio}")

                    # Update user management tab with user info
                    if user_data:
                        self.system_tab.update_user_info(user_data)

                except Exception as e:
                    self.logger.error(f"Error processing initial subscription values: {str(e)}")
                    import traceback
                    self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                
                # Initialize each tab with robot object
                self.panel_tab.initialize(self.robot)
                self.io_tab.initialize(self.robot)
                self.motion_tab.initialize(self.robot)
                self.rapid_tab.initialize(self.robot)
                self.robot_control_tab.initialize(self.robot)
                self.system_tab.initialize(self.robot)
                
                # Show success message
                QMessageBox.information(self, "Connection Successful", 
                                      f"Successfully connected to robot at {host}")
                
                return True
            else:
                self.logger.error("Failed to connect to robot")
                QMessageBox.critical(self, "Connection Failed", 
                                   "Failed to connect to robot. Check credentials and network connection.")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to robot: {str(e)}")
            QMessageBox.critical(self, "Connection Error", 
                               f"Error connecting to robot: {str(e)}")
            return False
    
    def disconnect_robot(self):
        """Disconnect from the robot controller"""
        if self.robot:
            try:
                # Unsubscribe from all subscriptions
                self.robot.unsubscribe_all()
                
                # Disconnect
                self.robot.disconnect()
                self.logger.info("Disconnected from robot")
                
                # Update UI
                self.set_tabs_enabled(False)
                self.connection_tab.set_connected(False)
                self.disconnect_action.setEnabled(False)
                self.connect_action.setEnabled(True)
                self.estop_action.setEnabled(False)
                
                # Hide the panel dock widget
                self.panel_dock.hide()
                
                # Update status widget
                self.status_widget.set_status("Disconnected", "red")
                
                # Show message
                QMessageBox.information(self, "Disconnected", 
                                      "Successfully disconnected from robot.")
                
            except Exception as e:
                self.logger.error(f"Error disconnecting from robot: {str(e)}")
                QMessageBox.warning(self, "Disconnect Warning", 
                                  f"Error during disconnect: {str(e)}")
                
            finally:
                # Reset robot object
                self.robot = None
    
    def emergency_stop(self):
        """Execute emergency stop"""
        if not self.robot:
            return
            
        try:
            # Execute emergency stop via rapid
            self.logger.warning("EMERGENCY STOP triggered")
            
            # Stop RAPID execution with qstop
            result = self.robot.rapid.set_execution_stop("qstop", "alltsk")
            
            # Turn off motors
            self.robot.panel.set_controller_state("motorOff")
            
            # Show message
            QMessageBox.critical(self, "EMERGENCY STOP", 
                               "Emergency stop has been triggered. The robot has been stopped.")
            
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {str(e)}")
            QMessageBox.critical(self, "Emergency Stop Error", 
                               f"Error executing emergency stop: {str(e)}")
    
    def setup_subscriptions(self):
        """Set up combined subscriptions to robot events"""
        
        if not self.robot:
            return
            
        try:
            # Get a list of all IO signals for subscription
            io_signals_list = []
            try:
                # Get all signals
                signals_result = self.robot.io.list_signals()
                if signals_result.get('status_code') == 200 and 'content' in signals_result:
                    if '_embedded' in signals_result['content'] and 'resources' in signals_result['content']['_embedded']:
                        signals = signals_result['content']['_embedded']['resources']
                        for signal in signals:
                            signal_path = signal.get('_links', {}).get('self', {}).get('href', '')
                            if signal_path:
                                # Remove the /rw/iosystem/ prefix if present
                                if signal_path.startswith('/rw/iosystem/'):
                                    signal_path = signal_path[len('/rw/iosystem/'):]
                                io_signals_list.append(signal_path)
                        self.logger.info(f"Found {len(io_signals_list)} IO signals for subscription")
            except Exception as e:
                self.logger.error(f"Error getting IO signals for subscription: {str(e)}")
                
            # Set up subscription to monitor various aspects of the robot
            self.robot.setup_combined_subscription(
                collect_signals=True,
                collect_user=True,
                collect_panel=True,
                collect_rapid=True,
                collect_motion=True,
                collect_vision=False,
                io_signals=io_signals_list
            )
            
            # Get initial values
            initial_values = self.robot.get_initial_values()
            print(initial_values)
            # Store initial values in each tab
            self.panel_tab.set_initial_values(initial_values)
            self.io_tab.set_initial_values(initial_values)
            self.rapid_tab.set_initial_values(initial_values)
            self.system_tab.set_initial_values(initial_values)
            # Create a custom callback for subscription data
            def subscription_callback(xml_str):
                self.handle_subscription_data(xml_str)
            
            # Create subscription with the callback
            subscription_id = self.robot.subscribe_to_collected_resources(subscription_callback)
            
            self.logger.info(f"Created subscription: {subscription_id}")
            
        except Exception as e:
            self.logger.error(f"Error setting up subscriptions: {str(e)}")
            import traceback
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def handle_subscription_data(self, xml_str):
        """Handle subscription data received from robot"""
        try:
            # Log the raw XML for debugging (limited length)
            self.logger.debug(f"Received subscription data: {xml_str[:200]}...")
            
            # Use the subscription parser from the robot object
            if not hasattr(self.robot, 'subscription_parser'):
                from API.abb_robot_utils import SubscriptionParser
                self.robot.subscription_parser = SubscriptionParser(self.logger)
            
            # Parse different types of events
            panel_data = self.robot.subscription_parser.parse_event_xml(xml_str)
            io_data = self.robot.io.processor.parse_io_event_xml(xml_str)
            rapid_data = self.robot.subscription_parser.parse_rapid_event_xml(xml_str)
            motion_data = self.robot.subscription_parser.parse_motion_event_xml(xml_str)
            user_data = self.robot.subscription_parser.parse_user_event_xml(xml_str)
            print(user_data)
            # Update UI based on event data
            if panel_data:
                # Process panel events
                self.logger.info(f"Received panel event: {panel_data}")
                
                # Prepare update data with only fields that were received in event
                panel_update = {}
                
                if 'controller_state' in panel_data:
                    # Convert controller_state to motor_state correctly
                    ctrl_state = panel_data['controller_state']
                    motor_state = "Running" if ctrl_state.lower() == "motoron" else "Stopped"
                    self.logger.info(f"Updated motor state to: {motor_state}")
                    # Update only the motor state
                    self.connection_tab.update_motor_state(motor_state)
                    self.panel_tab.update_motor_state(motor_state)
                
                if 'operation_mode' in panel_data:
                    # Only include op_mode if it was in the event
                    panel_update['op_mode'] = panel_data['operation_mode']
                    self.logger.info(f"Updated operation mode to: {panel_data['operation_mode']}")
                    # Update only operation mode in connection tab
                    self.connection_tab.update_operation_mode(panel_data['operation_mode'])
                    self.panel_tab.update_operation_mode(panel_data['operation_mode'])
                
                if 'speed_ratio' in panel_data:
                    # Only include speed_ratio if it was in the event
                    panel_update['speed_ratio'] = panel_data['speed_ratio']
                    self.panel_tab.update_speed_ratio(panel_data['speed_ratio'])
                    self.logger.info(f"Updated speed ratio to: {panel_data['speed_ratio']}")
                
            if io_data:
                # Process IO events
                self.logger.info(f"Received IO event: {io_data}")
                if hasattr(self.io_tab, 'update_signal_value'):
                    signal_name = io_data.get('signal_name', '')
                    signal_value = io_data.get('lvalue', '')
                    signal_path = io_data.get('signal_path', '')
                    
                    # If we have a signal path but no name, try to extract the name
                    if signal_path and not signal_name and ';state' in signal_path:
                        try:
                            signal_name = signal_path.split('/')[-1].split(';')[0]
                            self.logger.debug(f"Extracted signal name {signal_name} from path {signal_path}")
                        except Exception as e:
                            self.logger.error(f"Error extracting signal name from path: {str(e)}")
                    
                    # If we have a signal path but no value, try to extract from span elements
                    if not signal_value and 'class' in io_data:
                        signal_value = io_data.get(io_data['class'], '')
                        self.logger.debug(f"Extracted signal value {signal_value} from class {io_data['class']}")
                    
                    if signal_name and signal_value:
                        self.logger.info(f"Updating signal {signal_name} to {signal_value}")
                        self.io_tab.update_signal_value(signal_name, signal_value)
                    elif signal_path:
                        # Try harder to extract signal name
                        self.logger.warning(f"Signal event with incomplete data: {io_data}")
                        if '/' in signal_path:
                            parts = signal_path.split('/')
                            for part in reversed(parts):
                                if part and part != 'state' and ';' not in part:
                                    # This is likely the signal name
                                    signal_name = part
                                    self.logger.info(f"Extracted alternate signal name: {signal_name}")
                                    break
                            
                            # If we found a name but no value, try to get it from the event
                            if signal_name and not signal_value:
                                # Try various common class names for signal values
                                for key in ['lvalue', 'value', 'state']:
                                    if key in io_data:
                                        signal_value = io_data[key]
                                        self.logger.info(f"Extracted signal value {signal_value} using key {key}")
                                        break
                            
                            if signal_name and signal_value:
                                self.logger.info(f"Updating signal {signal_name} to {signal_value} (alternative method)")
                                self.io_tab.update_signal_value(signal_name, signal_value)
            
            if rapid_data and rapid_data.get('ctrlexecstate', ''):
                # Process RAPID events
                self.logger.info(f"Received RAPID event: {rapid_data}")
                rapid_exec_state = rapid_data.get('ctrlexecstate', '')
                rapid_state = "Unknown"
                
                if rapid_exec_state == "running":
                    rapid_state = "Running"
                elif rapid_exec_state == "stopped":
                    rapid_state = "Stopped"
                else:
                    rapid_state = "Ready"
                
                self.logger.info(f"Updated RAPID state to: {rapid_state}")
                self.connection_tab.update_rapid_state(rapid_state)
                self.panel_tab.update_rapid_state(rapid_state)
                self.rapid_tab.update_rapid_state(rapid_state)
            
            if motion_data and motion_data.get('errorstate', ''):
                self.logger.info(f"Received motion event: {motion_data}")
                self.motion_tab.update_motion_data(motion_data)
            
            if user_data and user_data.get('rmmp', ''):
                rmmp_value = user_data.get('rmmp', '0')
                self.logger.info(f"Received user event: {rmmp_value}")
                self.system_tab.update_rmpp_user_info(rmmp_value)
                    
            # Store timestamp of last subscription update
            self._last_subscription_update = time.time()
                    
        except Exception as e:
            self.logger.error(f"Error processing subscription data: {str(e)}")
            import traceback
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def set_tabs_enabled(self, enabled):
        """Enable or disable control tabs"""
        # Skip connection tab (index 0)
        for i in range(1, self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, enabled)
    
    def update_ui(self):
        """Update UI with latest information from robot"""
        if not self.robot:
            return
            
        # Update UI with latest subscription data
        try:
            # Update connection status
            connection_status = "Connected"
            status_color = "green"
            
            # Update status and each tab
            self.status_widget.set_status(connection_status, status_color)
            self.status_widget.update_controller_time()
            
            # Periodically update controller information as a fallback
            # Using a static counter to avoid doing this on every update
            if not hasattr(self, '_update_counter'):
                self._update_counter = 0
            
            self._update_counter += 1
            if self._update_counter >= 30:  # Update every 30 seconds
                self._update_counter = 0
                
                # Check if we haven't received subscription data for a while
                last_update_time = getattr(self, '_last_subscription_update', 0)
                time_since_last_update = time.time() - last_update_time
                
                # Only perform a manual update if no subscription data received for 30 seconds
                if time_since_last_update > 30 or last_update_time == 0:
                    self.logger.info("No recent subscription data. Performing manual UI update as fallback.")
                    try:
                        # Get the current controller state directly
                        ctrl_state_resp = self.robot.panel.get_controller_state()
                        if ctrl_state_resp.get('status_code') == 200:
                            ctrl_state = ctrl_state_resp.get('content', {}).get('state', [{}])[0].get('ctrlstate', 'Unknown')
                            motor_state = "Running" if ctrl_state.lower() == "motoron" else "Stopped"
                            
                            # Get operation mode
                            op_mode_resp = self.robot.panel.get_operation_mode()
                            op_mode = "Unknown"
                            if op_mode_resp.get('status_code') == 200:
                                op_mode = op_mode_resp.get('content', {}).get('state', [{}])[0].get('opmode', 'Unknown')
                            
                            # Get RAPID state
                            rapid_exec_resp = self.robot.rapid.get_execution_state()
                            rapid_state = None
                            if rapid_exec_resp.get('status_code') == 200:
                                rapid_exec_state = rapid_exec_resp.get('content', {}).get('state', [{}])[0].get('ctrlexecstate', '')
                                
                                if rapid_exec_state == "running":
                                    rapid_state = "Running"
                                elif rapid_exec_state == "stopped":
                                    rapid_state = "Stopped"
                                else:
                                    rapid_state = "Ready"
                            
                            # Update each state individually
                            self.connection_tab.update_operation_mode(op_mode)
                            self.connection_tab.update_motor_state(motor_state)
                            if rapid_state:
                                self.connection_tab.update_rapid_state(rapid_state)
                                self.panel_tab.update_rapid_state(rapid_state)
                                self.rapid_tab.update_rapid_state(rapid_state)
                            # Get speed ratio
                            speed_ratio_resp = self.robot.panel.get_speed_ratio()
                            speed_ratio = "0"
                            if speed_ratio_resp.get('status_code') == 200:
                                speed_ratio = speed_ratio_resp.get('content', {}).get('state', [{}])[0].get('speedratio', '0')
                            
                            # Update panel tab components individually
                            self.panel_tab.update_motor_state(motor_state)
                            self.panel_tab.update_operation_mode(op_mode)
                            self.panel_tab.update_speed_ratio(speed_ratio)
                            
                            self.logger.info(f"Manual update completed: Motor: {motor_state}, Mode: {op_mode}, Speed: {speed_ratio}")
                    except Exception as e:
                        self.logger.error(f"Error during manual UI update: {str(e)}")
                else:
                    self.logger.debug(f"Using subscription data ({time_since_last_update:.1f}s since last update)")
            
            # Call update_ui on each tab for any internal periodic updates they need
            self.panel_tab.update_ui()
            self.io_tab.update_ui()
            self.motion_tab.update_ui()
            self.rapid_tab.update_ui()
            self.robot_control_tab.update_ui()
            self.system_tab.update_ui()
            
        except Exception as e:
            self.logger.error(f"Error updating UI: {str(e)}")
            import traceback
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def open_settings(self):
        """Open settings dialog"""
        pass  # Will implement settings dialog
    
    def open_help(self):
        """Open help dialog"""
        pass  # Will implement help dialog
    
    def load_settings(self):
        """Load application settings"""
        settings = QSettings()
        
        # Load window geometry
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        # Load connection settings
        host = settings.value("connection/host", "")
        username = settings.value("connection/username", "Default User")
        password = settings.value("connection/password", "")
        protocol = settings.value("connection/protocol", "https://")
        
        # Update connection tab
        self.connection_tab.set_credentials(host, username, password, protocol)
    
    def save_settings(self):
        """Save application settings"""
        settings = QSettings()
        
        # Save window geometry
        settings.setValue("geometry", self.saveGeometry())
        
        # Save connection settings
        if self.connection_tab:
            host, username, password, protocol = self.connection_tab.get_credentials()
            settings.setValue("connection/host", host)
            settings.setValue("connection/username", username)
            # Don't save password for security reasons unless user opts in
            settings.setValue("connection/protocol", protocol)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop the update timer first to prevent UI updates during shutdown
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
            
        # Disconnect from robot if connected
        if self.robot:
            self.disconnect_robot()
            
        # Save settings
        self.save_settings()
        
        # Accept close event
        event.accept() 