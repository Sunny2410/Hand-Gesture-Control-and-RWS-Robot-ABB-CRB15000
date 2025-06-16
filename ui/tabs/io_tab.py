from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QTabWidget, QSplitter, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCursor

# Đăng ký meta types để tránh cảnh báo về queue
try:
    from PyQt5.QtCore import qRegisterMetaType
    qRegisterMetaType('QVector<int>')
    qRegisterMetaType('QTextCursor')
except (ImportError, TypeError):
    pass  # Bỏ qua nếu không đăng ký được

class IOTab(QWidget):
    """Tab for robot I/O signals control"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # Disable updates until initialized
        self.initialized = False
        
        # Store signals
        self.signals = []
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Search and filter layout at top
        search_layout = QHBoxLayout()
        
        # Signal name search
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter signal name...")
        self.search_input.textChanged.connect(self.on_search_change)
        search_layout.addWidget(self.search_input)
        
        # Signal type filter
        search_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "DI", "DO", "AI", "AO", "GI", "GO"])
        self.type_combo.currentIndexChanged.connect(self.on_type_filter_change)
        search_layout.addWidget(self.type_combo)
        
        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search_click)
        search_layout.addWidget(self.search_button)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setIcon(QIcon("ui/resources/refresh.png"))
        self.refresh_button.clicked.connect(self.on_refresh_click)
        search_layout.addWidget(self.refresh_button)
        
        # Add search layout to main layout
        main_layout.addLayout(search_layout)
        
        # Create splitter between signal table and details/control
        self.splitter = QSplitter(Qt.Vertical)
        
        # Signal table
        self.signal_table = QTableWidget(0, 4)  # Rows, Columns
        self.signal_table.setHorizontalHeaderLabels(["Name", "Type", "Value", "State"])
        self.signal_table.setAlternatingRowColors(True)
        self.signal_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.signal_table.setSelectionMode(QTableWidget.SingleSelection)
        self.signal_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Stretch name column
        self.signal_table.horizontalHeader().setStretchLastSection(True)  # Stretch last column
        self.signal_table.verticalHeader().setVisible(False)  # Hide vertical header
        self.signal_table.selectionModel().selectionChanged.connect(self.on_signal_selected)
        
        # Add signal table to splitter
        self.splitter.addWidget(self.signal_table)
        
        # Signal details and control area
        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)
        
        # Signal details
        signal_details_group = QGroupBox("Signal Details")
        signal_details_layout = QFormLayout()
        
        # Signal path
        signal_details_layout.addRow("Path:", QLabel())
        self.signal_path_label = signal_details_layout.itemAt(1).widget()
        
        # Signal name
        signal_details_layout.addRow("Name:", QLabel())
        self.signal_name_label = signal_details_layout.itemAt(3).widget()
        
        # Signal type
        signal_details_layout.addRow("Type:", QLabel())
        self.signal_type_label = signal_details_layout.itemAt(5).widget()
        
        # Signal value
        signal_details_layout.addRow("Value:", QLabel())
        self.signal_value_label = signal_details_layout.itemAt(7).widget()
        
        # Signal state
        signal_details_layout.addRow("State:", QLabel())
        self.signal_state_label = signal_details_layout.itemAt(9).widget()
        
        # Apply layout to group
        signal_details_group.setLayout(signal_details_layout)
        details_layout.addWidget(signal_details_group)
        
        # Signal control
        signal_control_group = QGroupBox("Signal Control")
        signal_control_layout = QHBoxLayout()
        
        # Set value for digital signals
        self.set_true_button = QPushButton("Set TRUE")
        self.set_true_button.clicked.connect(lambda: self.on_set_value(1))
        signal_control_layout.addWidget(self.set_true_button)
        
        self.set_false_button = QPushButton("Set FALSE")
        self.set_false_button.clicked.connect(lambda: self.on_set_value(0))
        signal_control_layout.addWidget(self.set_false_button)
        
        # Set value for analog signals
        signal_control_layout.addWidget(QLabel("Value:"))
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Analog value...")
        signal_control_layout.addWidget(self.value_input)
        
        self.set_value_button = QPushButton("Set Value")
        self.set_value_button.clicked.connect(lambda: self.on_set_value(self.value_input.text()))
        signal_control_layout.addWidget(self.set_value_button)
        
        # Apply layout to group
        signal_control_group.setLayout(signal_control_layout)
        details_layout.addWidget(signal_control_group)
        
        # Add a placeholder for event log
        log_group = QGroupBox("IO Events")
        log_layout = QVBoxLayout()
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setStyleSheet("background-color: #F0F0F0; border: 1px solid #CCC; padding: 5px;")
        self.event_log.setMaximumHeight(100)
        log_layout.addWidget(self.event_log)
        
        # Apply layout to group
        log_group.setLayout(log_layout)
        details_layout.addWidget(log_group)
        
        # Add details widget to splitter
        self.splitter.addWidget(self.details_widget)
        
        # Add splitter to main layout
        main_layout.addWidget(self.splitter)
        
        # Set initial splitter sizes - 70% for table, 30% for details
        self.splitter.setSizes([700, 300])
        
        # Disable control buttons initially
        self.set_control_enabled(False)
    
    def initialize(self, robot):
        """Initialize with robot reference and load signals"""
        self.robot = robot
        
        # Update table with initial signals
        self.on_refresh_click()
        
        # Set initialized flag
        self.initialized = True
        self.log_event("IO control initialized")
    
    def set_initial_values(self, initial_values):
        """Update with initial values from subscription"""
        # This will be called once subscriptions are set up
        # Update UI with any values provided
        if not initial_values:
            return
            
        self.log_event("Received initial signal values from subscription")
        
        # Store signal paths that we want to track
        self.signal_paths = {}  # name -> path mapping
        
        # Process any IO signal values in the initial values
        for path, data in initial_values.items():
            if '/rw/iosystem/' in path and ';state' in path:
                try:
                    signal_name = path.split('/')[-1].split(';')[0]
                    self.signal_paths[signal_name] = path
                    
                    if 'content' in data and 'state' in data['content']:
                        signal_value = data['content']['state'][0].get('lvalue', 'Unknown')
                        self.log_event(f"Initial value for {signal_name}: {signal_value}")
                except Exception as e:
                    self.log_event(f"Error processing initial value for {path}: {str(e)}")
    
    def update_signal_value(self, signal_name, signal_value):
        """Update a signal value in the UI when a subscription event occurs"""
        if not self.initialized:
            return
            
        try:
            # Log the update attempt for debugging
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Force signal_value to be a string
            signal_value = str(signal_value)
            
            # Print current table contents for debugging
            print(f"[{timestamp}] Current table has {self.signal_table.rowCount()} rows")
            
            # Find the signal in the table
            signal_found = False
                        # Trong update_signal_value, trước vòng for:
            print(f"==> Đang cập nhật signal: '{signal_name}' với giá trị {signal_value}")
            for row in range(self.signal_table.rowCount()):
                name_item = self.signal_table.item(row, 0)
                if name_item:
                    print(f"Row {row}: '{name_item.text()}'")
            for row in range(self.signal_table.rowCount()):
                name_item = self.signal_table.item(row, 0)
                if name_item:
                    print(f"[{timestamp}] Row {row}: '{name_item.text()}' vs '{signal_name}'")
                    
                if name_item and name_item.text().strip() == signal_name.strip():
                    signal_found = True
                    print(f"[{timestamp}] Found signal {signal_name} at row {row}")
                    # Update the value in the table
                    value_item = self.signal_table.item(row, 2)
                    if value_item:
                        old_value = value_item.text()
                        
                        # Only update if value actually changed
                        if old_value != signal_value:
                            value_item.setText(signal_value)
                            
                            # Update the signal in our signals list
                            if row < len(self.signals):
                                self.signals[row]['lvalue'] = signal_value
                            
                            # Update color for digital signals
                            signal_type = self.signal_table.item(row, 1).text()
                            if signal_type in ['DI', 'DO', 'GI', 'GO']:
                                if signal_value == '1':
                                    value_item.setBackground(QColor('#A3FFA3'))  # Light green
                                else:
                                    value_item.setBackground(QColor('#FFA3A3'))  # Light red
                            
                            # If this signal is currently selected, update the details
                            selected_indexes = self.signal_table.selectedIndexes()
                            if selected_indexes and selected_indexes[0].row() == row:
                                self.signal_value_label.setText(signal_value)
                            
                            # Log value change
                            self.log_event(f"Signal {signal_name} changed: {old_value} → {signal_value}")
                            
                            # Make sure the change is visible immediately
                            self.signal_table.viewport().update()
                    
                    # We found our signal, no need to continue checking
                    break
            
            # If signal wasn't found in the table but we received an update
            if not signal_found:
                # Log the issue
                self.log_event(f"Signal {signal_name} not found in table, attempting to add it")
                print(f"[{timestamp}] Signal {signal_name} not found in table, attempting to add it")
                
                # If robot is available, try to get more information about the signal
                if self.robot:
                    try:
                        # Try to find the full signal path
                        signal_path = f"/rw/iosystem/signals/{signal_name}"
                        if hasattr(self, 'signal_paths') and signal_name in self.signal_paths:
                            signal_path = self.signal_paths[signal_name]
                        
                        # Get signal info
                        signal_info = self.robot.io.get_signal_value(signal_path)
                        print(f"[{timestamp}] Signal info: {signal_info}")
                        
                        if signal_info.get('status_code') == 200 and 'content' in signal_info:
                            # Create new signal entry
                            new_signal = {
                                'name': signal_name,
                                'type': 'DI',  # Default to DI, will be updated later
                                'lvalue': signal_value,
                                'lstate': 'valid',
                                '_links': {'self': {'href': signal_path}}
                            }
                            
                            # Extract type if available
                            if 'state' in signal_info['content']:
                                for state_item in signal_info['content']['state']:
                                    if 'type' in state_item:
                                        new_signal['type'] = state_item['type']
                            
                            # Add to signals list
                            self.signals.append(new_signal)
                            
                            # Add to table
                            row = self.signal_table.rowCount()
                            self.signal_table.setRowCount(row + 1)
                            
                            # Set items
                            self.signal_table.setItem(row, 0, QTableWidgetItem(signal_name))
                            self.signal_table.setItem(row, 1, QTableWidgetItem(new_signal['type']))
                            self.signal_table.setItem(row, 2, QTableWidgetItem(signal_value))
                            self.signal_table.setItem(row, 3, QTableWidgetItem(new_signal.get('lstate', 'valid')))
                            
                            # Set color
                            value_item = self.signal_table.item(row, 2)
                            if new_signal['type'] in ['DI', 'DO', 'GI', 'GO']:
                                if signal_value == '1':
                                    value_item.setBackground(QColor('#A3FFA3'))  # Light green
                                else:
                                    value_item.setBackground(QColor('#FFA3A3'))  # Light red
                            
                            self.log_event(f"Added new signal {signal_name} to table with value {signal_value}")
                            # Store path for future updates
                            if hasattr(self, 'signal_paths'):
                                self.signal_paths[signal_name] = signal_path
                    except Exception as e:
                        self.log_event(f"Error adding signal {signal_name}: {str(e)}")
                        import traceback
                        print(f"Error adding signal: {traceback.format_exc()}")
                else:
                    # Store the path for future updates, in case we reload the table
                    if hasattr(self, 'signal_paths'):
                        self.signal_paths[signal_name] = f"/rw/iosystem/signals/{signal_name}"
                    self.log_event(f"Received update for signal {signal_name} not in table: {signal_value}")
                    
                    # Try to refresh signals list if we haven't in a while
                    self._last_refresh_attempt = getattr(self, '_last_refresh_attempt', 0)
                    if timestamp.time() - self._last_refresh_attempt > 15:  # Refresh at most every 15 seconds
                        self._last_refresh_attempt = timestamp.time()
                        self.log_event(f"Automatically refreshing signals list to find {signal_name}")
                        # Use QTimer to avoid blocking the UI thread
                        QTimer.singleShot(100, self.on_refresh_click)
                
        except Exception as e:
            self.log_event(f"Error updating signal value: {str(e)}")
            import traceback
            print(f"Error stack: {traceback.format_exc()}")
    
    def update_ui(self):
        """Periodic UI update"""
        if not self.robot or not self.initialized:
            return
        
        # We don't need to poll for updates since we're using subscriptions
        # But we could update some dynamic elements here if needed
        pass
    
    def on_search_change(self, text):
        """Filter signals table based on search text"""
        self.filter_table()
    
    def on_type_filter_change(self, index):
        """Filter signals table based on type selection"""
        self.filter_table()
    
    def filter_table(self):
        """Apply filters to the signal table"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_combo.currentText()
        
        # Show all rows first
        for row in range(self.signal_table.rowCount()):
            self.signal_table.setRowHidden(row, False)
        
        # Apply filters
        for row in range(self.signal_table.rowCount()):
            show_row = True
            
            # Check name filter
            if search_text:
                name_item = self.signal_table.item(row, 0)
                if not name_item or search_text not in name_item.text().lower():
                    show_row = False
            
            # Check type filter
            if type_filter != "All" and show_row:
                type_item = self.signal_table.item(row, 1)
                if not type_item or type_filter != type_item.text():
                    show_row = False
            
            # Show or hide row based on filters
            self.signal_table.setRowHidden(row, not show_row)
    
    def on_search_click(self):
        """Search for signals matching criteria"""
        if not self.robot:
            return
            
        try:
            # Get search criteria
            search_name = self.search_input.text()
            
            if not search_name:
                self.log_event("Please enter a signal name to search")
                return
                
            # Search for signals
            self.log_event(f"Searching for signals matching '{search_name}'...")
            results = self.robot.io.search_signals(name=search_name)
            
            if results.get('status_code') == 200 and 'content' in results:
                # Clear existing table
                self.signal_table.setRowCount(0)
                self.signals = []
                
                # Process results
                if '_embedded' in results['content'] and 'resources' in results['content']['_embedded']:
                    signals = results['content']['_embedded']['resources']
                    self.populate_signal_table(signals)
                    self.log_event(f"Found {len(signals)} signals matching '{search_name}'")
                else:
                    self.log_event(f"No signals found matching '{search_name}'")
            else:
                self.log_event(f"Error searching for signals: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error searching for signals: {str(e)}")
    
    def on_refresh_click(self):
        """Refresh all signals in the table"""
        if not self.robot:
            return
            
        try:
            # Clear existing table
            self.signal_table.setRowCount(0)
            self.signals = []
            
            # Get all signals
            self.log_event("Loading signals...")
            results = self.robot.io.list_signals()
            
            if results.get('status_code') == 200 and 'content' in results:
                # Process results
                if '_embedded' in results['content'] and 'resources' in results['content']['_embedded']:
                    signals = results['content']['_embedded']['resources']
                    self.populate_signal_table(signals)
                    self.log_event(f"Loaded {len(signals)} signals")
                else:
                    self.log_event("No signals found")
            else:
                self.log_event(f"Error loading signals: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error refreshing signals: {str(e)}")
    
    def populate_signal_table(self, signals):
        """Populate the signal table with signal data"""
        # Store signals
        self.signals = signals
        
        # Ensure we have a signal_paths dictionary
        if not hasattr(self, 'signal_paths'):
            self.signal_paths = {}
        
        # Set table row count
        self.signal_table.setRowCount(len(signals))
        
        # Fill table with signal data
        for i, signal in enumerate(signals):
            # Extract data
            name = signal.get('name', 'Unknown')
            signal_type = signal.get('type', 'Unknown')
            value = signal.get('lvalue', 'Unknown')
            state = signal.get('lstate', 'Unknown')
            
            # Get and store signal path
            signal_path = signal.get('_links', {}).get('self', {}).get('href', '')
            if signal_path and name != 'Unknown':
                # Store the path for subscription updates
                self.signal_paths[name] = signal_path
            
            # Create table items
            name_item = QTableWidgetItem(name)
            type_item = QTableWidgetItem(signal_type)
            value_item = QTableWidgetItem(value)
            state_item = QTableWidgetItem(state)
            
            # Set items in table
            self.signal_table.setItem(i, 0, name_item)
            self.signal_table.setItem(i, 1, type_item)
            self.signal_table.setItem(i, 2, value_item)
            self.signal_table.setItem(i, 3, state_item)
            
            # Color based on signal type
            if signal_type in ['DI', 'DO', 'GI', 'GO']:
                if value == '1':
                    value_item.setBackground(QColor('#A3FFA3'))  # Light green
                else:
                    value_item.setBackground(QColor('#FFA3A3'))  # Light red
        
        # Apply filters
        self.filter_table()
    
    def on_signal_selected(self, selected, deselected):
        """Handle signal selection in the table"""
        # Get selected row
        indexes = selected.indexes()
        if not indexes:
            # No selection
            self.set_control_enabled(False)
            return
            
        # Get row index
        row = indexes[0].row()
        
        # Get signal data
        if row < 0 or row >= len(self.signals):
            # Invalid row
            self.set_control_enabled(False)
            return
            
        signal = self.signals[row]
        
        # Update details labels
        self.signal_path_label.setText(signal.get('_links', {}).get('self', {}).get('href', 'Unknown'))
        self.signal_name_label.setText(signal.get('name', 'Unknown'))
        self.signal_type_label.setText(signal.get('type', 'Unknown'))
        self.signal_value_label.setText(signal.get('lvalue', 'Unknown'))
        self.signal_state_label.setText(signal.get('lstate', 'Unknown'))
        
        # Enable control buttons
        self.set_control_enabled(True)
        
        # Configure controls based on signal type
        signal_type = signal.get('type', '')
        
        if signal_type in ['DI', 'GI']:
            # Digital inputs can't be set
            self.set_control_enabled(True)
            self.set_true_button.setEnabled(True)
            self.set_false_button.setEnabled(True)
        elif signal_type in ['DO', 'GO']:
            # Digital outputs can be set to true/false
            self.set_true_button.setEnabled(True)
            self.set_false_button.setEnabled(True)
            self.value_input.setEnabled(False)
            self.set_value_button.setEnabled(False)
        elif signal_type in ['AI']:
            # Analog inputs can't be set
            self.set_control_enabled(False)
        elif signal_type in ['AO']:
            # Analog outputs require a value
            self.set_true_button.setEnabled(False)
            self.set_false_button.setEnabled(False)
            self.value_input.setEnabled(True)
            self.set_value_button.setEnabled(True)
    
    def set_control_enabled(self, enabled):
        """Enable or disable signal control buttons"""
        self.set_true_button.setEnabled(enabled)
        self.set_false_button.setEnabled(enabled)
        self.value_input.setEnabled(enabled)
        self.set_value_button.setEnabled(enabled)
    
    def on_set_value(self, value):
        """Set signal value"""
        if not self.robot:
            return
            
        # Get selected signal
        indexes = self.signal_table.selectedIndexes()
        if not indexes:
            return
            
        row = indexes[0].row()
        if row < 0 or row >= len(self.signals):
            return
            
        signal = self.signals[row]
        signal_path = signal.get('_links', {}).get('self', {}).get('href', '')
        
        if not signal_path:
            self.log_event("Error: No signal path found")
            return
            
        try:
            # Set signal value
            self.log_event(f"Setting signal {signal.get('name', '')} to {value}...")
            result = self.robot.io.set_signal_value(signal_path, value)
            
            if result.get('status_code') in [200, 201, 202, 204]:
                self.log_event(f"Set signal value successfully")
                
                # Update the displayed value
                self.signal_value_label.setText(str(value))
                
                # Update table item for this signal
                value_item = self.signal_table.item(row, 2)
                if value_item:
                    value_item.setText(str(value))
                    
                    # Update background color for digital signals
                    signal_type = signal.get('type', '')
                    if signal_type in ['DO', 'GO']:
                        if value == 1 or value == '1':
                            value_item.setBackground(QColor('#A3FFA3'))  # Light green
                        else:
                            value_item.setBackground(QColor('#FFA3A3'))  # Light red
            else:
                self.log_event(f"Failed to set signal value: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error setting signal value: {str(e)}")
    
    def log_event(self, message):
        """Add a message to the event log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {message}") 