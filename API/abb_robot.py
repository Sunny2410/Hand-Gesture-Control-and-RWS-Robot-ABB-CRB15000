"""
ABB Robot Web Services (RWS) Robot Modules

A library providing a unified interface for controlling ABB robot systems:
- Panel controls (speed ratio, controller state, operation mode)
- Controller-specific functions (restart, backup, network settings)
- I/O system functions for signal management
- User management functions
- Vision system functions
- RAPID programming and execution
- Motion system control and monitoring

Author: Sunny24
Date: May 21, 2025
"""

from typing import Dict, List, Optional, Any, Union, Callable
import time
import threading
from .abb_base import ABBRobotAPI
from .abb_robot_utils import IOSignalProcessor, SubscriptionParser, SubscriptionHelper, SubscriptionManager


class ABBEndpoints:
    """Constants for ABB Robot Web Services API endpoints"""
    
    # Base paths
    BASE_PATH = '/rw'
    
    # Panel endpoints
    PANEL_BASE = f'{BASE_PATH}/panel'
    SPEED_RATIO = f'{PANEL_BASE}/speedratio'
    CTRL_STATE = f'{PANEL_BASE}/ctrl-state'
    OPMODE = f'{PANEL_BASE}/opmode'
    OPMODE_ACK = f'{OPMODE}/acknowledge'
    COLLISION = f'{PANEL_BASE}/coldetstate'
    
    # Mastership endpoints
    MASTERSHIP_BASE = f'{BASE_PATH}/mastership'
    MASTERSHIP_REQUEST = f'{MASTERSHIP_BASE}/request'
    MASTERSHIP_RELEASE = f'{MASTERSHIP_BASE}/release'
    
    # User endpoints
    USERS_BASE = '/users'
    LOGOUT = '/logout'
    USERS_REGISTER = f'{USERS_BASE}/register'
    USER_INFO = f'{USERS_BASE}/login-info'
    RMPP_USER_INFO = f'{USERS_BASE}/rmmp'
    RMPP_USER_INFO_POOL = f'{USERS_BASE}/rmmp/pool'
    USERS_REGISTER_LOCAL = f'{USERS_BASE}/register/local'

    # Controller endpoints
    CTRL_BASE = '/ctrl'
    CTRL_RESTART = f'{CTRL_BASE}/restart'
    CTRL_NETWORK = f'{CTRL_BASE}/network'
    BACKUP_BASE = f'{CTRL_BASE}/backup'
    BACKUP_CREATE = f'{BACKUP_BASE}/create'
    BACKUP_STATE = f'{BACKUP_BASE}/state'
    
    # I/O system endpoints
    IOSYSTEM_BASE = f'{BASE_PATH}/iosystem'
    SIGNALS_BASE = f'{IOSYSTEM_BASE}/signals'
    SIGNALS_SEARCH = f'{SIGNALS_BASE}/signal-search'
    SIGNALS_VALUE = f'{IOSYSTEM_BASE}/{{signal_path}}'
    SIGNALS_SETVALUE = f'{IOSYSTEM_BASE}/{{signal_path}}/set-value'

    # Vision system endpoints
    VISION_BASE = f'{BASE_PATH}/vision'
    VISION_JOB_NAME = f'{VISION_BASE}/{{camera_name}}/job-name'
    VISION_INFO = f'{VISION_BASE}/{{camera_index}}/info'
    VISION_RESTART = f'{VISION_BASE}/{{camera_name}}/restart'
    VISION_LED = f'{VISION_BASE}/{{camera_name}}/led'
    VISION_REFRESH = f'{VISION_BASE}/refresh'
    VISION_HOSTNAME = f'{VISION_BASE}/{{camera_name}}/hostname'
    VISION_NAME = f'{VISION_BASE}/{{camera_index}}/name'
    VISION_NETWORK = f'{VISION_BASE}/{{camera_name}}/network'
    VISION_USER = f'{VISION_BASE}/{{camera_index}}/user'
    VISION_STATUS = f'{VISION_BASE}/{{camera_name}}/status'
    
    # RAPID endpoints
    RAPID_BASE = f'{BASE_PATH}/rapid'
    RAPID_EXECUTION = f'{RAPID_BASE}/execution'
    RAPID_EXECUTION_START = f'{RAPID_EXECUTION}/start'
    RAPID_EXECUTION_STOP = f'{RAPID_EXECUTION}/stop'
    RAPID_EXECUTION_RESETPP = f'{RAPID_EXECUTION}/resetpp'
    RAPID_EXECUTION_CYCLE = f'{RAPID_EXECUTION}/cycle'
    RAPID_MODULES = f'{RAPID_BASE}/modules'
    RAPID_ROBTARGET = f'{RAPID_BASE}/tasks/{{task}}/motion/robtarget'
    RAPID_JOINTTARGET = f'{RAPID_BASE}/tasks/{{task}}/motion/jointtarget'
    RAPID_PROGRAM = f'{RAPID_BASE}/tasks/{{task}}/program'
    RAPID_MODULES_TASK = f'{RAPID_BASE}/tasks/{{task}}/modules'
    RAPID_SYMBOL_RESOURCES = f'{RAPID_BASE}/symbols'
    RAPID_SYMBOL_SEARCH = f'{RAPID_SYMBOL_RESOURCES}/search'
    RAPID_SYMBOL_DATA = f'{RAPID_BASE}/symbol/{{symbolurl}}/data'
    RAPID_ALIASIO = f'{RAPID_BASE}/aliasio'
    RAPID_TASKS = f'{RAPID_BASE}/tasks'
    RAPID_TASK_ACTIVATE = f'{RAPID_TASKS}/{{task}}/activate'
    RAPID_TASK_DEACTIVATE = f'{RAPID_TASKS}/{{task}}/deactivate'
    
    # Motion system endpoints
    MOTION_BASE = f'{BASE_PATH}/motionsystem'
    MOTION_MECHUNITS = f'{MOTION_BASE}/mechunits'
    MOTION_JOINTTARGET = f'{MOTION_BASE}/jointtarget'
    MOTION_JOG = f'{MOTION_BASE}/jog'
    MOTION_POSITION_TARGET = f'{MOTION_BASE}/position-target'
    MOTION_POSITION_JOINT = f'{MOTION_BASE}/position-joint'
    MOTION_ERRORSTATE = f'{MOTION_BASE}/errorstate'
    MOTION_NONEXECUTION = f'{MOTION_BASE}/nonmotionexecution'
    MOTION_COLLISION_PREDICTION = f'{MOTION_BASE}/collisionprediction'
    MOTION_MECHUNIT_BASE = f'{MOTION_BASE}/mechunits'
    MOTION_MECHUNIT_PATHSUPERVISION = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/pathsupervision'
    MOTION_MECHUNIT_PATHSUPERVISION_MODE = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/pathsupervision/mode'
    MOTION_MECHUNIT_PATHSUPERVISION_LEVEL = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/pathsupervision/level'
    MOTION_MECHUNIT_MOTIONSUPERVISION = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/motionsupervision'
    MOTION_MECHUNIT_MOTIONSUPERVISION_MODE = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/motionsupervision/mode'
    MOTION_MECHUNIT_MOTIONSUPERVISION_LEVEL = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/motionsupervision/level'
    MOTION_MECHUNIT_SMBDATA = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/smbdata'
    MOTION_MECHUNIT_SMBDATA_SET = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/smbdata/set'
    MOTION_MECHUNIT_SMBDATA_CLEAR = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/smbdata/clear'
    MOTION_MECHUNIT_POSITION = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/position'
    MOTION_MECHUNIT_LEAD_THROUGH = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/lead-through'
    MOTION_MECHUNIT_LEAD_THROUGH_LOAD = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/lead-through/load'
    MOTION_MECHUNIT_FINE_CALIBRATE = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/fine-calibrate'
    MOTION_MECHUNIT_UPDATE_REVCOUNTER = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/update-revcounter'
    MOTION_MECHUNIT_JOINTS_FROM_POSE = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/joints-from-pose'
    MOTION_MECHUNIT_POSE_FROM_JOINTS = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/pose-from-joints'
    MOTION_MECHUNIT_ALL_JOINTS_SOLUTION = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/all-joints-solution'
    MOTION_MECHUNIT_JOINTS_FROM_CARTESIAN = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/joints-from-cartesian'
    MOTION_MECHUNIT_PJOINTS = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/pjoints'
    MOTION_MECHUNIT_BASEFRAME = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/baseframe'
    MOTION_MECHUNIT_AXES = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/axes'
    MOTION_MECHUNIT_AXIS_POSE = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/axes/{{axis_num}}/pose'
    MOTION_MECHUNIT_AXIS_COMMUTATE = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/axes/{{axis_num}}/commutate'
    MOTION_MECHUNIT_AXIS_SYNCREVCOUNTER = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/axes/{{axis_num}}/syncrevcounter'
    MOTION_MECHUNIT_CARTESIAN = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/cartesian'
    MOTION_MECHUNIT_CALIB = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/calib'
    MOTION_MECHUNIT_CALIB_SINGLEUSERLIN = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/calib/singleuserlin'
    MOTION_MECHUNIT_ROBTARGET = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/robtarget'
    MOTION_MECHUNIT_JOINTTARGET = f'{MOTION_MECHUNIT_BASE}/{{mechunit}}/jointtarget'
    MOTION_MECHUNIT_MOVEINAUTO_TOKEN = f'{MOTION_BASE}/moveinauto/token'


class ABBBaseService:
    """Base class for all ABB services"""
    
    def __init__(self, api: ABBRobotAPI):
        """
        Initialize with a reference to the ABB Robot API
        
        Args:
            api: An instance of the ABB Robot API
        """
        self.api = api
        self.logger = api.logger
    
    def _validate_input(self, value: Any, valid_values: List[Any], 
                       param_name: str) -> Dict[str, Any]:
        """
        Validate input parameters against a list of valid values
        
        Args:
            value: Value to validate
            valid_values: List of valid values
            param_name: Name of the parameter for error messages
            
        Returns:
            Error response dict if invalid, None if valid
        """
        if value not in valid_values:
            self.logger.error(f"Invalid {param_name}: {value}. Must be one of {valid_values}")
            return {'status_code': 400, 'error': f'Invalid {param_name}: {value}'}
        return None


class Panel(ABBBaseService):
    """Panel control functions for ABB robots"""

    def __init__(self, api: ABBRobotAPI):
        """
        Initialize with a reference to the ABB Robot API
        
        Args:
            api: An instance of the ABB Robot API
        """
        super().__init__(api)
        # Initialize subscription helper
        self.sub_helper = SubscriptionHelper(self.api, self.logger)

    def get_speed_ratio(self) -> Dict[str, Any]:
        """
        Get the speed ratio
        
        Returns:
            Response information
        """
        return self.api.get(ABBEndpoints.SPEED_RATIO)
        
    def set_speed_ratio(self, ratio: int) -> Dict[str, Any]:
        """
        Set the speed ratio
        
        Args:
            ratio: Speed ratio to set (0-100)
            
        Returns:
            Response information
        """
        # Validate input
        if not isinstance(ratio, int) or ratio < 0 or ratio > 100:
            self.logger.error(f"Invalid speed ratio: {ratio}. Must be integer between 0-100")
            return {'status_code': 400, 'error': 'Invalid speed ratio'}
            
        data = {'speed-ratio': str(ratio)}
        return self.api.post(ABBEndpoints.SPEED_RATIO, data=data)

    def get_controller_state(self) -> Dict[str, Any]:
        """
        Get the current controller state
        
        Returns:
            Response information
        """
        return self.api.get(ABBEndpoints.CTRL_STATE)

    def set_controller_state(self, state: str) -> Dict[str, Any]:
        """
        Set the controller state (motoron or motoroff)
        
        Args:
            state: 'motorOn' or 'motorOff'
            
        Returns:
            Response information
        """
        valid_states = ['motorOn', 'motorOff']
        error = self._validate_input(state, valid_states, "controller state")
        if error:
            return error
            
        data = {'ctrl-state': state}
        return self.api.post(ABBEndpoints.CTRL_STATE, data=data)

    def get_operation_mode(self) -> Dict[str, Any]:
        """
        Get the current operation mode
        
        Returns:
            Response information
        """
        return self.api.get(ABBEndpoints.OPMODE)
    
    def set_operation_mode(self, mode: str) -> Dict[str, Any]:
        """
        Set the operation mode
        
        Args:
            mode: Operation mode to set (e.g., 'auto', 'manual')
            
        Returns:
            Response information
        """
        valid_modes = ['auto', 'man', 'manf']
        error = self._validate_input(mode, valid_modes, "operation mode")
        if error:
            return error
            
        data = {'opmode': mode}
        return self.api.post(ABBEndpoints.OPMODE, data=data)

    def set_ackoperation_mode(self, mode: str) -> Dict[str, Any]:
        """
        Acknowledge operation mode change
        
        Args:
            mode: Operation mode to acknowledge
            
        Returns:
            Response information
        """
        valid_modes = ['auto', 'coldet', 'manf']
        error = self._validate_input(mode, valid_modes, "operation mode")
        if error:
            return error
        
        data = {'opmode': mode}
        return self.api.post(ABBEndpoints.OPMODE_ACK, data=data)

    def set_mastership_request(self) -> Dict[str, Any]:
        """
        Request mastership of the robot controller
        
        Returns:
            Response information
        """
        return self.api.post(ABBEndpoints.MASTERSHIP_REQUEST)

    def set_mastership_release(self) -> Dict[str, Any]:
        """
        Release mastership of the robot controller
        
        Returns:
            Response information
        """
        return self.api.post(ABBEndpoints.MASTERSHIP_RELEASE)

    def get_collision_state(self) -> Dict[str, Any]:
        """
        Get the collision detection state
        
        Returns:
            Response information
        """
        return self.api.get(ABBEndpoints.COLLISION)

    def get_panel_state_and_subscribe(self, 
                                    resources: Optional[Dict[str, Any]] = None, 
                                    callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Get the current panel state and then subscribe to panel events
        
        Args:
            resources: Dictionary of panel resources to subscribe to
            callback: Function to call when events are received
            
        Returns:
            Dictionary with initial panel state and subscription ID
        """
        self.logger.warning("DEPRECATED: get_panel_state_and_subscribe is deprecated. Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.")
        
        initial_state, subscription_id = self.sub_helper.get_panel_state_and_subscribe(resources, callback)
        
        return {
            'initial_state': initial_state,
            'subscription_id': subscription_id
        }
        
    # subscribe_to_panel_events method has been removed.
    # Subscription functionality is now centralized in ABBRobot.subscription_manager


class User(ABBBaseService):
    """User management functions for ABB robots"""

    def get_rmmp_user_info(self) -> Dict[str, Any]:
        """
        Get the RMPP user information
        """
        return self.api.get(ABBEndpoints.RMPP_USER_INFO)
    
    def set_rmmp_user_info(self, privilege: str) -> Dict[str, Any]:
        """
        Set the RMPP user information
        """ 
        valid_privileges = ['modify', 'exec']
        error = self._validate_input(privilege, valid_privileges, "privilege")
        if error:
            return error
        data = {'privilege': privilege}
        return self.api.post(ABBEndpoints.RMPP_USER_INFO, data=data)
    
    def get_pool_rmmp_user_info(self) -> Dict[str, Any]:
        """
        Get the pool RMPP user information
        """
        return self.api.get(ABBEndpoints.RMPP_USER_INFO_POOL)

    def logout(self) -> Dict[str, Any]:
        """
        Logout the user
        """
        return self.api.post(ABBEndpoints.LOGOUT)

    def set_user(self, username: str, application: str, location: str) -> Dict[str, Any]:
        """
        Register the user as a Local Client
        
        Args:
            username: The username to register
            application: The application name to register
            location: The location of the user
            
        Returns:
            Response information
        """
        # Check if required information is provided
        if not all([username, application, location]):
            self.logger.error("Username, application, and location must be provided.")
            return {'status_code': 400, 'error': 'Missing required fields'}

        # User registration data
        data = {
            'username': username,
            'application': application,
            'location': location,
            'ulocale': 'local'  # Set ulocale to 'local' for Local Client permissions
        }

        # Send POST request to register user
        return self.api.post(ABBEndpoints.USERS_REGISTER, data=data)

    def set_local_user(self, username: str, application: str, location: str, local_key: str) -> Dict[str, Any]:
        """
        Set the local user
                    required:
              - username
              - application
              - location
              - local-key
            properties:
              username:
                description: The username to register
                type: string
              application:
                description: The application name to register
                type: string
              location:
                description: The location of the user
                type: string
              local-key:
                description: Local presence certificate key
                type: string
        """
        data = {
            'username': username,
            'application': application,
            'location': location,
            'local-key': local_key
        }
        return self.api.post(ABBEndpoints.USERS_REGISTER_LOCAL, data=data)


class Controller(ABBBaseService):
    """Controller management functions for ABB robots"""
    
    def set_restart(self, mode: str) -> Dict[str, Any]:
        """
        Restart the controller
        
        Args:
            mode: Restart mode
                - 'restart': Restart controller, save state
                - 'shutdown': Shut down main computer
                - 'xstart': Restart and start Boot Application
                - 'istart': Restart with original system settings
                - 'pstart': Restart, discard RAPID programs
                - 'bstart': Restart, load last auto-saved state
                
        Returns:
            Response information
        """
        valid_modes = ['restart', 'shutdown', 'xstart', 'istart', 'pstart', 'bstart']
        error = self._validate_input(mode, valid_modes, "restart mode")
        if error:
            return error
            
        data = {'restart-mode': mode}
        return self.api.post(ABBEndpoints.CTRL_RESTART, data=data)

    def get_network(self) -> Dict[str, Any]:
        """
        Get the current network settings
        
        Returns:
            Response information
        """
        return self.api.get(ABBEndpoints.CTRL_NETWORK)
        
    def get_backup_state(self) -> Dict[str, Any]:
        """
        Get the current backup state
        
        Returns:
            Response information
        """
        return self.api.get(ABBEndpoints.BACKUP_STATE)
        
    def set_backup_create(self, mode: str, backup_path: str = '/backup') -> Dict[str, Any]:
        """
        Create a backup of the current system state
        
        Args:
            mode: 'TRUE' for archiving, 'FALSE' for regular backup
            backup_path: Path where backup should be stored
            
        Returns:
            Response information
        """
        valid_modes = ['TRUE', 'FALSE']
        error = self._validate_input(mode, valid_modes, "backup mode")
        if error:
            return error

        data = {
            'backup': backup_path,
            'archive': mode
        }

        return self.api.post(ABBEndpoints.BACKUP_CREATE, data=data)


class IO(ABBBaseService):
    """IO Service for ABB Robot Systems"""
    
    def __init__(self, api: 'ABBRobotAPI'):
        """
        Initialize with a reference to the ABB Robot API
        
        Args:
            api: An instance of the ABB Robot API
        """
        super().__init__(api)
        # Initialize processor for signal data
        self.processor = IOSignalProcessor(self.logger)
        # Initialize subscription helper
        self.sub_helper = SubscriptionHelper(self.api, self.logger)
    
    def search_signals(self, name: Optional[str] = None, device: Optional[str] = None,
                     network: Optional[str] = None, category: Optional[str] = None,
                     type: Optional[str] = None, invert: Optional[str] = None, 
                     blocked: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for signals matching specific criteria
        
        Args:
            name: Signal name pattern
            device: Device name pattern
            network: Network name pattern
            category: Category name pattern
            type: Signal type
            invert: 'true' or 'false' to invert signal
            blocked: 'true' or 'false' for blocked signals
            
        Returns:
            Search results with matched signals
        """
        # Build search parameters
        params = {}
        if name is not None:
            params['name'] = name
        if device is not None:
            params['device'] = device
        if network is not None:
            params['network'] = network
        if category is not None:
            params['category'] = category
        if type is not None:
            params['type'] = type
        if invert is not None:
            params['invert'] = invert
        if blocked is not None:
            params['blocked'] = blocked
            
        # Call API with search parameters
        return self.api.post(ABBEndpoints.SIGNALS_SEARCH, data=params)
        
    def get_signal_paths(self, name: Optional[str] = None, 
                        exact_match: bool = False) -> List[str]:
        """
        Get signal paths for a given name pattern
        
        Args:
            name: Signal name or name pattern to search for
            exact_match: If True, only return exact matches
            
        Returns:
            List of signal paths matching the criteria
        """
        return self.processor.get_signal_paths(
            api=self.api,
            endpoint_signals_search=ABBEndpoints.SIGNALS_SEARCH,
            name=name,
            exact_match=exact_match
        )
    
    def get_signal_value(self, signal_path: str) -> Dict[str, Any]:
        """
        Get the current value of a signal
        
        Args:
            signal_path: Signal path or name
            
        Returns:
            Signal value and state information
        """
        # Check if signal_path is a name rather than a path
        if signal_path and '/' not in signal_path:
            # Try to find the signal path for this name
            matching_paths = self.get_signal_paths(signal_path, exact_match=True)
            if matching_paths:
                signal_path = matching_paths[0]
        
        # Normalize signal path
        signal_path = self.processor.normalize_signal_path(signal_path)
        self.logger.debug(f"Getting signal value for {signal_path}")
        
        # Get signal value using formatted endpoint
        formatted_endpoint = ABBEndpoints.SIGNALS_VALUE.format(signal_path=self.processor.short_signal_path(signal_path))
        return self.api.get(formatted_endpoint)
            
    def set_signal_value(self, signal_path: str, value: Any) -> Dict[str, Any]:
        """
        Set the value of a signal
        
        Args:
            signal_path: Signal path or name
            value: Value to set
            
        Returns:
            Response information
        """
        # Check if signal_path is a name rather than a path
        if signal_path and '/' not in signal_path:
            # Try to find the signal path for this name
            matching_paths = self.get_signal_paths(signal_path, exact_match=True)
            if matching_paths:
                signal_path = matching_paths[0]
        
        # Normalize signal path
        signal_path = self.processor.normalize_signal_path(signal_path)
        self.logger.debug(f"Setting signal value for {signal_path} to {value}")
        
        # Use the SIGNALS_SETVALUE endpoint
        formatted_endpoint = ABBEndpoints.SIGNALS_SETVALUE.format(signal_path=self.processor.short_signal_path(signal_path))
        
        # Set signal value
        data = {'lvalue': str(value)}
        return self.api.post(formatted_endpoint, data=data)
        
    def list_signals(self, filter_pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        List all signals, optionally filtered by pattern
        
        Args:
            filter_pattern: Pattern to filter signals
            
        Returns:
            List of signals
        """
        params = {}
        if filter_pattern:
            params['filter'] = filter_pattern
            
        return self.api.get(ABBEndpoints.SIGNALS_BASE, params=params)
    
    def parse_io_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse IO signal event XML data into a structured format
        
        Args:
            xml_str: XML string from WebSocket event
            
        Returns:
            Dictionary with parsed signal data
        """
        return self.processor.parse_io_event_xml(xml_str)
        
    def get_signal_value_and_subscribe(self, signal_path: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Get the current value of a signal and then subscribe to changes
        
        Args:
            signal_path: Signal path to get value from and subscribe to
            callback: Callback function for events
            
        Returns:
            Dictionary with initial signal value and subscription ID
        """
        self.logger.warning("DEPRECATED: get_signal_value_and_subscribe is deprecated. Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.")
        
        initial_value, subscription_id = self.sub_helper.get_io_signal_value_and_subscribe(signal_path, callback)
        
        return {
            'initial_value': initial_value,
            'subscription_id': subscription_id
        }
        
    def unsubscribe_from_signal(self, subscription_id: str) -> bool:
        """
        DEPRECATED: Use ABBRobot.unsubscribe() instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Unsubscribe from a signal subscription
        
        Args:
            subscription_id: Subscription ID to cancel
            
        Returns:
            True if successful
        """
        self.logger.warning("DEPRECATED: unsubscribe_from_signal is deprecated. Use ABBRobot.unsubscribe() instead.")
        return self.api.unsubscribe(subscription_id)
        
    def get_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot's subscription management instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Check the status of a subscription
        
        Args:
            subscription_id: ID of the subscription to check
            
        Returns:
            Status information about the subscription
        """
        self.logger.warning("DEPRECATED: get_subscription_status is deprecated. Use ABBRobot's subscription management instead.")
        return self.api.check_subscription_status(subscription_id)
        
    def list_all_subscriptions(self) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot's subscription management instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        List all active subscriptions
        
        Returns:
            Dictionary of subscription IDs and their status
        """
        self.logger.warning("DEPRECATED: list_all_subscriptions is deprecated. Use ABBRobot's subscription management instead.")
        return self.api.list_active_subscriptions()


class MotionSystem(ABBBaseService):
    """Motion System functions for ABB robots"""
    
    def __init__(self, api: ABBRobotAPI):
        """
        Initialize with a reference to the ABB Robot API
        
        Args:
            api: An instance of the ABB Robot API
        """
        super().__init__(api)
        # Initialize subscription helper
        self.sub_helper = SubscriptionHelper(self.api, self.logger)

    def get_request_jogging_auto(self) -> Dict[str, Any]:
        """
        Get the request jogging auto
        """
        return self.api.get(ABBEndpoints.MOTION_MECHUNIT_MOVEINAUTO_TOKEN)

    def set_mechunit_for_jogging(self, mechunit: str) -> Dict[str, Any]:
        """
        Set the mechanical unit for jogging
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information
        """
        endpoint = f'{ABBEndpoints.MOTION_BASE}/{mechunit}'
        return self.api.post(endpoint)
    
    def set_robot_position_target(self, pos_x: str, pos_y: str, pos_z: str, orient_q1: str, 
                               orient_q2: str, orient_q3: str, orient_q4: str, config_j1: str, config_j4: str, 
                               config_j6: str, config_jx: str, extjoint_1: str, extjoint_2: str, extjoint_3: str, 
                               extjoint_4: str, extjoint_5: str, extjoint_6: str) -> Dict[str, Any]:
        """
        Set the position target for a mechanical unit
        """

        data = {
            'pos-x': pos_x,
            'pos-y': pos_y,
            'pos-z': pos_z,
            'orient-q1': orient_q1,
            'orient-q2': orient_q2,
            'orient-q3': orient_q3,
            'orient-q4': orient_q4,
            'config-j1': config_j1,
            'config-j4': config_j4,
            'config-j6': config_j6,
            'config-jx': config_jx,
            'extjoint-1': extjoint_1,
            'extjoint-2': extjoint_2,
            'extjoint-3': extjoint_3,
            'extjoint-4': extjoint_4,
            'extjoint-5': extjoint_5,
            'extjoint-6': extjoint_6
        }   
        
        return self.api.post(ABBEndpoints.MOTION_POSITION_TARGET, data=data)
    
    def get_mechunits(self) -> Dict[str, Any]:
        """
        Get the list of mechanical units
        
        Returns:
            Response information with mechanical units
        """
        return self.api.get(ABBEndpoints.MOTION_MECHUNITS)
    
    def get_mechunit_jointtarget(self, mechunit: str) -> Dict[str, Any]:
        """
        Get joint target values for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with joint target values
        """
        params = {'moc': mechunit}
        return self.api.get(ABBEndpoints.MOTION_JOINTTARGET, params=params)
    
    def jog_multiple_axes(self, axis1: str, axis2: str, axis3: str, axis4: str, axis5: str, axis6: str,
                          ccount: str, inc_mode: str, token: str) -> Dict[str, Any]:
        """
        Jog multiple axes of a mechanical unit
        
        Args:
            axis1: Axis number for axis 1
            axis2: Axis number for axis 2
            axis3: Axis number for axis 3
            axis4: Axis number for axis 4
            axis5: Axis number for axis 5
            axis6: Axis number for axis 6
            ccount: Change count
            inc_mode: Increment mode {User | Medium | Small | Large}
            token: Token(GET URL /rw/motionsystem/moveinauto/token) can be used
                  for Perform Jogging (default value = zero), this is optional
        Returns:
            Response information
        """
        data = {
            'axis1': axis1,
            'axis2': axis2,
            'axis3': axis3,
            'axis4': axis4,
            'axis5': axis5,
            'axis6': axis6,
            'ccount': ccount,
            'inc-mode': inc_mode,
            'token': token
        }
        return self.api.post(ABBEndpoints.MOTION_JOG, data=data)
     
    def get_error_state(self) -> Dict[str, Any]:
        """
        Get the motion system error state
        
        Returns:
            Response information with error state
        """
        return self.api.get(ABBEndpoints.MOTION_ERRORSTATE)
    
    def get_nonmotion_execution(self) -> Dict[str, Any]:
        """
        Get the non-motion execution mode
        
        Returns:
            Response information with non-motion execution mode
        """
        return self.api.get(ABBEndpoints.MOTION_NONEXECUTION)
    
    def set_nonmotion_execution(self, mode: str) -> Dict[str, Any]:
        """
        Set the non-motion execution mode
        
        Args:
            mode: Mode to set ('on' or 'off')
            
        Returns:
            Response information
        """
        valid_modes = ['ON', 'OFF']
        error = self._validate_input(mode.lower(), valid_modes, "non-motion execution mode")
        if error:
            return error
            
        data = {'mode': mode.lower()}
        return self.api.post(ABBEndpoints.MOTION_NONEXECUTION, data=data)
    
    def get_collision_prediction(self) -> Dict[str, Any]:
        """
        Get the collision prediction mode
        
        Returns:
            Response information with collision prediction mode
        """
        return self.api.get(ABBEndpoints.MOTION_COLLISION_PREDICTION)
    
    def set_collision_prediction(self, mode: str) -> Dict[str, Any]:
        """
        Set the collision prediction mode
        
        Args:
            mode: Mode to set ('on' or 'off')
            
        Returns:
            Response information
        """
        valid_modes = ['true', 'false']
        error = self._validate_input(mode.lower(), valid_modes, "collision prediction mode")
        if error:
            return error
            
        data = {'mode': mode.lower()}
        return self.api.post(ABBEndpoints.MOTION_COLLISION_PREDICTION, data=data)
    
    def get_motion_state_and_subscribe(self, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Get the current motion system state and then subscribe to changes
        
        Args:
            callback: Function to call when events are received
            
        Returns:
            Dictionary with initial motion system state and subscription ID
        """
        self.logger.warning("DEPRECATED: get_motion_state_and_subscribe is deprecated. Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.")
        
        # Use subscription parser for motion events if a callback is provided
        parser = self.api.robot.subscription_parser if hasattr(self.api, 'robot') else None
        
        def motion_callback(xml_str: str) -> None:
            if callback and parser:
                # Parse XML event data
                parsed_data = parser.parse_motion_event_xml(xml_str)
                if parsed_data:
                    # Call user callback with parsed data
                    callback(parsed_data)
            elif callback:
                # Call user callback with raw data if no parser
                callback(xml_str)
        
        initial_state, subscription_id = self.sub_helper.get_motion_state_and_subscribe(motion_callback)
        
        return {
            'initial_state': initial_state,
            'subscription_id': subscription_id
        }
    
    def get_mechunit_pathsupervision(self, mechunit: str) -> Dict[str, Any]:
            """
            Get path supervision information for a mechanical unit
            
            Args:
                mechunit: Name of the mechanical unit
                
            Returns:
                Response information with path supervision details
            """
            endpoint = ABBEndpoints.MOTION_MECHUNIT_PATHSUPERVISION.format(mechunit=mechunit)
            return self.api.get(endpoint)

    def set_mechunit_pathsupervision_mode(self, mechunit: str, mode: str) -> Dict[str, Any]:
        """
        Set path supervision mode for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            mode: Mode to set ('on' or 'off')
            
        Returns:
            Response information
        """
        valid_modes = ['ON', 'OFF']
        error = self._validate_input(mode.lower(), valid_modes, "path supervision mode")
        if error:
            return error
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_PATHSUPERVISION_MODE.format(mechunit=mechunit)
        data = {'mode': mode.lower()}
        return self.api.post(endpoint, data=data)

    def set_mechunit_pathsupervision_level(self, mechunit: str, level: str) -> Dict[str, Any]:
        """
        Set path supervision level for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            level: Level to set ('fine', 'medium', 'coarse')
            
        Returns:
            Response information
        """
        valid_levels = [str(i) for i in range(1, 301)]  # cho phép từ '1' đến '300'
        error = self._validate_input(level, valid_levels, "path supervision level")
        if error:
            return error
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_PATHSUPERVISION_LEVEL.format(mechunit=mechunit)
        data = {'level': level}
        return self.api.post(endpoint, data=data)

    def get_mechunit_motionsupervision(self, mechunit: str) -> Dict[str, Any]:
            """
            Get motion supervision information for a mechanical unit
            
            Args:
                mechunit: Name of the mechanical unit
                
            Returns:
                Response information with motion supervision details
            """
            endpoint = ABBEndpoints.MOTION_MECHUNIT_MOTIONSUPERVISION.format(mechunit=mechunit)
            return self.api.get(endpoint)

    def set_mechunit_motionsupervision_mode(self, mechunit: str, mode: str) -> Dict[str, Any]:
        """
        Set motion supervision mode for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            mode: Mode to set ('on' or 'off')
            
        Returns:
            Response information
        """
        valid_modes = ['true', 'false']
        error = self._validate_input(mode.lower(), valid_modes, "motion supervision mode")
        if error:
            return error
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_MOTIONSUPERVISION_MODE.format(mechunit=mechunit)
        data = {'mode': mode.lower()}
        return self.api.post(endpoint, data=data)

    def set_mechunit_motionsupervision_level(self, mechunit: str, level: str) -> Dict[str, Any]:
        """
        Set motion supervision level for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            level: Level to set ('fine', 'medium', 'coarse')
            
        Returns:
            Response information
        """
        valid_levels = [str(i) for i in range(1, 301)]  # cho phép từ '1' đến '300'
        error = self._validate_input(level, valid_levels, "motion supervision level")
        if error:
            return error
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_MOTIONSUPERVISION_LEVEL.format(mechunit=mechunit)
        data = {'sensitivity': level}
        return self.api.post(endpoint, data=data)

    def get_mechunit_lead_through(self, mechunit: str) -> Dict[str, Any]:
        """
        Get lead-through status for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with lead-through status
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_LEAD_THROUGH.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def set_mechunit_lead_through(self, mechunit: str, status: str, disableautoloadcompensation: str, 
                              axis1: float, axis2: float, axis3: float, axis4: float, axis5: float, axis6: float) -> Dict[str, Any]:
        """
        Set lead-through mode for a mechanical unit
        
        Args:
        Example:  Jog mode is Linear: Softness vector max
                        value[100,100,100,0,0,0,0] Jog mode Axis 1 to 6: Softness
                        vector max value[100,100,100,100,100,100,0] Jog mode Reorient:
                        Softness vector max value[ 0,0,0,100,100,100,0]
        status:
                        description: '{active|inactive} active if activate lead through'
                        type: string
                    disableautoloadcompensation:
                        description: >-
                        {active | Inactive}, active if use precision mode. Supported
                        from RW 7.6.
                        type: string
            
        Returns:
            Response information
        """
        valid_status = ['active', 'inactive']
        valid_disableautoloadcompensation = ['active', 'inactive']

        error = self._validate_input(status, valid_status, "status")
        if error:
            return error
        error = self._validate_input(disableautoloadcompensation, valid_disableautoloadcompensation, "disableautoloadcompensation")
        if error:
            return error
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_LEAD_THROUGH.format(mechunit=mechunit)
        data = {
            'status': status,
            'disableautoloadcompensation': disableautoloadcompensation,
            'softness': f'{axis1},{axis2},{axis3},{axis4},{axis5},{axis6},0'  # Định dạng chính xác theo yêu cầu API
        }
        return self.api.post(endpoint, data=data)
    
    def get_mechunit_lead_through_load(self, mechunit: str) -> Dict[str, Any]:
        """
        Get load for lead-through mode
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_LEAD_THROUGH_LOAD.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def set_mechunit_lead_through_load(self, mechunit: str) -> Dict[str, Any]:
        """
        Set load for lead-through mode
        
        Args:
            mechunit: Name of the mechanical unit
            load: Load weight in kg
            cog_x: X coordinate of center of gravity
            cog_y: Y coordinate of center of gravity
            cog_z: Z coordinate of center of gravity
            inertia_x: Inertia around X axis
            inertia_y: Inertia around Y axis
            inertia_z: Inertia around Z axis
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_LEAD_THROUGH_LOAD.format(mechunit=mechunit)

        return self.api.post(endpoint)

    def set_mechunit_position(self, mechunit: str, axis1: float, axis2: float, axis3: float, axis4: float, axis5: float, axis6: float) -> Dict[str, Any]:
            """
            Get current position of a mechanical unit
                    VC ONLY

            Args:
                mechunit: Name of the mechanical unit
                rob_joint:
                  [rob_joint1-value,rob_joint2-value,rob_joint3-value,rob_joint4-value,rob_joint5-value,rob_joint6-value]
                type: string
                ext_joint:
                description: >-
                  [ext_joint1-value,ext_joint2-value,ext_joint3-value,ext_joint4-value,ext_joint5-value,ext_joint6-value]
            Returns:
                Response information with position data
            """
            data = {
                'rob_joint': f'{axis1},{axis2},{axis3},{axis4},{axis5},{axis6}',
                'ext_joint': ''  # để chuỗi rỗng nếu không có external axes
            }
            endpoint = ABBEndpoints.MOTION_MECHUNIT_POSITION.format(mechunit=mechunit)
            return self.api.post(endpoint, data=data)

    def set_calculate_mechunit_joints_from_pose(self, mechunit: str, pos_x: float, pos_y: float, pos_z: float,
                                   ext_joint1: float, ext_joint2: float, ext_joint3: float, ext_joint4: float,
                                   ext_joint5: float, ext_joint6: float, orient_q1: float, orient_q2: float,
                                   orient_q3: float, orient_q4: float, tool_frame_position: str, tool_frame_orientation: str,
                                    old_rob_joint1: float, old_rob_joint2: float, old_rob_joint3: float, old_rob_joint4: float,
                                    old_rob_joint5: float, old_rob_joint6: float, old_ext_joint1: float, old_ext_joint2: float,
                                    old_ext_joint3: float, old_ext_joint4: float, old_ext_joint5: float, old_ext_joint6: float,
                                    robot_fixed_object: str, robot_configuration: str, elog_at_error: str) -> Dict[str, Any]:
        """
        Get joint values from a cartesian pose
        Args:
        data = {
            "curr_position": "100,200,300",
            "curr_ext_joints": "0,0,0,0,0,0",
            "tool_frame_position": "10,20,30",
            "curr_orientation": "1,0,0,0",
            "tool_frame_orientation": "1,0,0,0",
            "old_rob_joints": "0,0,0,0,0,0",
            "old_ext_joints": "0,0,0,0,0,0",
            "robot_fixed_object": "TRUE",
            "robot_configuration": "0,0,0,0",
            "elog_at_error": "FALSE"
        }

            
        Returns:
            Response information with joint values
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_JOINTS_FROM_POSE.format(mechunit=mechunit)
        data = {
            'curr_position': f'{pos_x},{pos_y},{pos_z}',
            'curr_ext_joints': f'{ext_joint1},{ext_joint2},{ext_joint3},{ext_joint4},{ext_joint5},{ext_joint6}',
            'tool_frame_position': f'{tool_frame_position}',
            'curr_orientation': f'{orient_q1},{orient_q2},{orient_q3},{orient_q4}',
            'tool_frame_orientation': f'{tool_frame_orientation}',
            'old_rob_joints': f'{old_rob_joint1},{old_rob_joint2},{old_rob_joint3},{old_rob_joint4},{old_rob_joint5},{old_rob_joint6}',
            'old_ext_joints': f'{old_ext_joint1},{old_ext_joint2},{old_ext_joint3},{old_ext_joint4},{old_ext_joint5},{old_ext_joint6}',
            'robot_fixed_object': f'{robot_fixed_object}',
            'robot_configuration': f'{robot_configuration}',
            'elog_at_error': f'{elog_at_error}'
        }
        return self.api.post(endpoint, data=data)

    def set_mechunit_pose_from_joints(self, mechunit: str, tool_frame_position: str, tool_frame_orientation: str, 
                                      rob_joint1: float, rob_joint2: float, rob_joint3: float, rob_joint4: float,
                                      rob_joint5: float, rob_joint6: float, ext_joint1: float, ext_joint2: float,
                                      ext_joint3: float, ext_joint4: float, ext_joint5: float, ext_joint6: float,
                                      robot_fixed_object: str, elog_at_error: str) -> Dict[str, Any]:
        """
        Get cartesian pose from joint values
        
        Args:
            mechunit: Name of the mechanical unit
            tool_frame_position: Tool frame position
            tool_frame_orientation: Tool frame orientation
            rob_joints: Robot joints
            ext_joints: External joints
            robot_fixed_object: Robot fixed object
            elog_at_error: Error log at error
             type: object
            required:
              - tool_frame_position
              - tool_frame_orientation
              - rob_joints
              - ext_joints
              - robot_fixed_object
              - elog_at_error
            properties:
              tool_frame_position:
                description: '[x, y, z]'
                type: string
              tool_frame_orientation:
                description: '[u0, u1, u2, u3]'
                type: string
              rob_joints:
                description: '[j1,j2,j3,j4,j5,j6]'
                type: string
              ext_joints:
                description: '[j1,j2,j3,j4,j5,j6]'
                type: string
              robot_fixed_object:
                description: TRUE|FALSE
                type: string
              elog_at_error:
                description: TRUE|FALSE
                type: string
            example: >-
              tool_frame_position=string&tool_frame_orientation=string&rob_joints=string&ext_joints=string&robot_fixed_object=string&elog_at_error=string
        Returns:
            Response information with cartesian pose
        """

        endpoint = ABBEndpoints.MOTION_MECHUNIT_POSE_FROM_JOINTS.format(mechunit=mechunit)
        data = {    
            'tool_frame_position': f'{tool_frame_position}',
            'tool_frame_orientation': f'{tool_frame_orientation}',
            'rob_joints': f'{rob_joint1},{rob_joint2},{rob_joint3},{rob_joint4},{rob_joint5},{rob_joint6}',
            'ext_joints': f'{ext_joint1},{ext_joint2},{ext_joint3},{ext_joint4},{ext_joint5},{ext_joint6}',
            'robot_fixed_object': f'{robot_fixed_object}',
            'elog_at_error': f'{elog_at_error}'
        }
        return self.api.post(endpoint, data=data)

    def set_mechunit_all_joints_solution(self, mechunit: str, pos_x: float, pos_y: float, pos_z: float,
                                         ext_joint1: float, ext_joint2: float, ext_joint3: float, ext_joint4: float,
                                         ext_joint5: float, ext_joint6: float, tool_frame_position: str,
                                         orient_q1: float, orient_q2: float, orient_q3: float, orient_q4: float,
                                         tool_frame_orientation: str, robot_fixed_object: str, robot_configuration: str) -> Dict[str, Any]:
        """
        Get all possible joint solutions for a cartesian pose
        
        Args:
        required:
              - curr_position
              - curr_ext_joints
              - tool_frame_position
              - curr_orientation
              - tool_frame_orientation
              - robot_fixed_object
              - robot_configuration
            properties:
              curr_position:
                description: '[x,y,z]'
                type: string
              curr_ext_joints:
                description: '[j1,j2,j3,j4,j5,j6]'
                type: string
              tool_frame_position:
                description: '[x, y, z]'
                type: string
              curr_orientation:
                description: '[u0, u1, u2, u3]'
                type: string
              tool_frame_orientation:
                description: '[u0, u1, u2, u3]'
                type: string
              robot_fixed_object:
                description: TRUE|FALSE
                type: string
              robot_configuration:
                description: >-
                  [quarter_rev_j1, quarter_rev_j4, quarter_rev_j6,
                  quarter_rev_jx]
                type: string
            
        Returns:
            Response information with all joint solutions
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_ALL_JOINTS_SOLUTION.format(mechunit=mechunit)
        data = {
            'curr_position': f'{pos_x},{pos_y},{pos_z}',
            'curr_ext_joints': f'{ext_joint1},{ext_joint2},{ext_joint3},{ext_joint4},{ext_joint5},{ext_joint6}',
            'tool_frame_position': f'{tool_frame_position}',
            'curr_orientation': f'{orient_q1},{orient_q2},{orient_q3},{orient_q4}',
            'tool_frame_orientation': f'{tool_frame_orientation}',
            'robot_fixed_object': f'{robot_fixed_object}',
            'robot_configuration': f'{robot_configuration}',
        }

        return self.api.post(endpoint, data=data)

    def set_mechunit_joints_from_cartesian(self, mechunit: str , pos_x: float, pos_y: float, pos_z: float, 
                                            orient_q1: float, orient_q2: float, orient_q3: float, orient_q4: float,
                                            ext_joint1: float, ext_joint2: float, ext_joint3: float, ext_joint4: float, 
                                            ext_joint5: float, ext_joint6: float, tool_frame_position: str,
                                            tool_frame_orientation: str, robot_fixed_object: str,
                                            robot_configuration: str, elog_at_error: str,
                                            old_rob_joint1: float, old_rob_joint2: float, old_rob_joint3: float, old_rob_joint4: float,
                                            old_rob_joint5: float, old_rob_joint6: float, old_ext_joint1: float, old_ext_joint2: float,
                                            old_ext_joint3: float, old_ext_joint4: float, old_ext_joint5: float, old_ext_joint6: float) -> Dict[str, Any]:
        """
        Get joint values from cartesian position using Euler angles
        
        Args:
              - curr_position
              - curr_ext_joints
              - tool_frame_position
              - curr_orientation
              - tool_frame_orientation
              - old_rob_joints
              - old_ext_joints
              - robot_fixed_object
              - robot_configuration
              - elog_at_error
            properties:
              curr_position:
                description: '[x,y,z]'
                type: string
              curr_ext_joints:
                description: '[j1,j2,j3,j4,j5,j6]'
                type: string
              tool_frame_position:
                description: '[x, y, z]'
                type: string
              curr_orientation:
                description: '[u0, u1, u2, u3]'
                type: string
              tool_frame_orientation:
                description: '[u0, u1, u2, u3]'
                type: string
              old_rob_joints:
                description: '[j1,j2,j3,j4,j5,j6]'
                type: string
              old_ext_joints:
                description: '[j1,j2,j3,j4,j5,j6]'
                type: string
              robot_fixed_object:
                description: TRUE|FALSE
                type: string
              robot_configuration:
                description: >-
                  [quarter_rev_j1, quarter_rev_j4, quarter_rev_j6,
                  quarter_rev_jx]
                type: string
              elog_at_error:
                description: TRUE|FALSE
                type: string
            
        Returns:
            Response information with joint values
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_JOINTS_FROM_CARTESIAN.format(mechunit=mechunit)
        data = {
            'curr_position': f'{pos_x},{pos_y},{pos_z}',
            'curr_ext_joints': f'{ext_joint1},{ext_joint2},{ext_joint3},{ext_joint4},{ext_joint5},{ext_joint6}',
            'tool_frame_position': f'{tool_frame_position}',
            'curr_orientation': f'{orient_q1},{orient_q2},{orient_q3},{orient_q4}',
            'tool_frame_orientation': f'{tool_frame_orientation}',
            'old_rob_joints': f'{old_rob_joint1},{old_rob_joint2},{old_rob_joint3},{old_rob_joint4},{old_rob_joint5},{old_rob_joint6}',
            'old_ext_joints': f'{old_ext_joint1},{old_ext_joint2},{old_ext_joint3},{old_ext_joint4},{old_ext_joint5},{old_ext_joint6}',
            'robot_fixed_object': f'{robot_fixed_object}',
            'robot_configuration': f'{robot_configuration}',
            'elog_at_error': f'{elog_at_error}',
        }
        return self.api.post(endpoint, data=data)

    def set_position_joint(self, axis1: float, axis2: float, axis3: float,
                            axis4: float, axis5: float, axis6: float) -> Dict[str, Any]:
        """
        Set joint position target for a mechanical unit
        Returns:
            parameters:
            - name: request-body
                in: body
                description: Data parameter(s)
                schema:
                type: object
                required:
                    - robjoint
                    - extjoint
                properties:
                    robjoint:
                    description: robot axes values, format=robjoint1-value,robjoint2-value,...
                    type: string
                    extjoint:
                    description: external axes values, format=extjoint1-value,extjoint2-value,...
                    type: string
        """
        endpoint = ABBEndpoints.MOTION_POSITION_JOINT
            
        data = {
                'robjoint': f'{axis1},{axis2},{axis3},{axis4},{axis5},{axis6}',
                'extjoint': f'0,0,0,0,0,0'
            }

            
        return self.api.post(endpoint, data=data)
    
    def get_mechunit_baseframe(self, mechunit: str) -> Dict[str, Any]:
        """
        Get baseframe information for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with baseframe data
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_BASEFRAME.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def set_mechunit_baseframe(self, mechunit: str, x: float, y: float, z: float, q1: float, q2: float, q3: float, q4: float) -> Dict[str, Any]:
        """
        Get baseframe information for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
                      description: Standard response for successful HTTP requests
          schema:
            properties:
              x:
                description: '{x-cordinate}'
              'y':
                description: '{y-cordinate}'
              z:
                description: '{z-cordinate}'
              q1:
                description: '{quaternion angle 1}'
              q2:
                description: '{quaternion angle 2}'
              q3:
                description: '{quaternion angle 3}'
              q4:
                description: '{quaternion angle 4}'
            
        Returns:
            Response information with baseframe data
        """
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_BASEFRAME.format(mechunit=mechunit)
        data = {
            'x': f'{x}',
            'y': f'{y}',
            'z': f'{z}',
            'q1': f'{q1}',
            'q2': f'{q2}',
            'q3': f'{q3}',
            'q4': f'{q4}',
        }
        return self.api.post(endpoint, data=data)

    def get_mechunit_axes(self, mechunit: str) -> Dict[str, Any]:
        """
        Get axes information for a mechanical unit
        
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with axes data
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_AXES.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def get_mechunit_axis_pose(self, mechunit: str, axis_num: int) -> Dict[str, Any]:
        """
        Get axis pose information
        
        Args:
            mechunit: Name of the mechanical unit
          schema:
            type: object
            required:
              - x
              - 'y'
              - z
              - q1
              - q2
              - q3
              - q4
            properties:
              x:
                description: '{x_position}'
                type: string
              'y':
                description: '{y_position}'
                type: string
              z:
                description: '{z_position}'
                type: string
              q1:
                description: '{q1_value}'
                type: string
              q2:
                description: '{q2_value}'
                type: string
              q3:
                description: '{q3_value}'
                type: string
              q4:
                description: '{q4_value}'
                type: string
            example: x=string&y=string&z=string&q1=string&q2=string&q3=string&q4=string
            
        Returns:
            Response information with axis pose data
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_AXIS_POSE.format(mechunit=mechunit, axis_num=axis_num)
        return self.api.get(endpoint)

    def set_mechunit_axis_pose(self, mechunit: str, axis_num: int, x: float, y: float, z: float, q1: float, q2: float, q3: float, q4: float) -> Dict[str, Any]:
        """
        Get axis pose information
        
        Args:
            mechunit: Name of the mechanical unit
            axis_num: Axis number
            
        Returns:
            Response information with axis pose data
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_AXIS_POSE.format(mechunit=mechunit, axis_num=axis_num)
        data = { 
            'x': f'{x}',
            'y': f'{y}',
            'z': f'{z}',
            'q1': f'{q1}',
            'q2': f'{q2}',
            'q3': f'{q3}',
            'q4': f'{q4}',
        }
        return self.api.post(endpoint, data=data)

    def set_mechunit_axis_commutate(self, mechunit: str, axis_num: int) -> Dict[str, Any]:
        """
        Commutate axis for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            axis_num: Axis number
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_AXIS_COMMUTATE.format(mechunit=mechunit, axis_num=axis_num)
        return self.api.get(endpoint)

    def set_mechunit_axis_syncrevcounter(self, mechunit: str, axis_num: int, sync_type: str) -> Dict[str, Any]:
        """
        Synchronize revolution counter for an axis
        
        Args:
            mechunit: Name of the mechanical unit
            axis_num: Axis number
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_AXIS_SYNCREVCOUNTER.format(mechunit=mechunit, axis_num=axis_num)
        data = {'syncType' : sync_type}
        return self.api.post(endpoint, data=data)

    def set_mechunit_fine_calibrate(self, mechunit: str, axis: int) -> Dict[str, Any]:
        """
        Perform fine calibration for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_FINE_CALIBRATE.format(mechunit=mechunit)
        data = {
            'axis': f'{axis}'  # ví dụ: '1' hoặc 'axis_1' tùy theo yêu cầu của API
        }

        return self.api.post(endpoint, data=data)

    def set_mechunit_update_revcounter(self, mechunit: str, axis: int) -> Dict[str, Any]:
        """
        Update revolution counter for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            axis: Axis number       
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_UPDATE_REVCOUNTER.format(mechunit=mechunit)
        data = {
            'axis': f'{axis}'  # ví dụ: '1' hoặc 'axis_1' tùy theo yêu cầu của API
        }
        return self.api.post(endpoint, data=data)

    def get_mechunit_calib(self, mechunit: str) -> Dict[str, Any]:
        """
        Get calibration information for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with calibration data
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_CALIB.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def set_mechunit_calib_singleuserlin(self, mechunit: str, tolerance: float, point1: List[float], point2: List[float], point3: List[float], point4: List[float], 
                                         point5: List[float], point6: List[float], point7: List[float], point8: List[float], point9: List[float], point10: List[float]) -> Dict[str, Any]:
        """
        Set single user linear calibration for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            tolerance: Total allowable error while calibrating
            point1: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point2: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point3: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point4: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point5: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point6: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point7: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point8: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point9: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            point10: [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and Orientation
            properties:
              tolerance:
                description: Total allowable error while calibrating
                type: string
              point1:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point2:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point3:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point4:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point5:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point6:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point7:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point8:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point9:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
              point10:
                description: >-
                  [x, y, z, q1, q2, q3, q4, axis_value] Base frame position and
                  Orientation
                type: string
            example: >-
              tolerance=0&point1=[492.6,517.9,359.6,0.499999,1.146672E-07,0.866026,1.05773E-07,0]&
              point2=[492.6,304.9,359.6,0.499999,1.146672E-07,0.866026,1.05773E-07,213]&
              point3=[492.6,48.8,359.6,0.499999,1.146672E-07,0.866026,1.05773E-07,256]&
              point4=[492.6,-272.1,359.6,0.499999,1.146672E-07,0.866026,1.05773E-07,321]
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_CALIB_SINGLEUSERLIN.format(mechunit=mechunit)
        data = {
            'tolerance': tolerance, 
            'point1': point1,
            'point2': point2,
            'point3': point3,
            'point4': point4,
            'point5': point5,
            'point6': point6,
            'point7': point7,
            'point8': point8,
            'point9': point9,
            'point10': point10, 
        }
        return self.api.post(endpoint, data=data)
    
    def get_mechunit_smbdata(self, mechunit: str) -> Dict[str, Any]:
        """
        Get SMB data for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with SMB data
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_SMBDATA.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def set_mechunit_smbdata(self, mechunit: str, type: str) -> Dict[str, Any]:
        """
        Set SMB data for a mechanical unit
        
        Args:
            type: robot-to-controller | controller-to-robot
        Returns:
            Response information
        """
        # validate type 
        valid_types = ['robot-to-controller', 'controller-to-robot']
        error = self._validate_input(type, valid_types, "type")
        if error:
            return error
        
        endpoint = ABBEndpoints.MOTION_MECHUNIT_SMBDATA_SET.format(mechunit=mechunit)
        data = {
            'type': type,
        }
        return self.api.post(endpoint, data=data)

    def clear_mechunit_smbdata(self, mechunit: str, type: str) -> Dict[str, Any]:
        """
        Clear SMB data for a mechanical unit
        
        Args: description: '{robot|controller}'

        Returns:
            Response information
        """
        valid_types = ['robot', 'controller']
        error = self._validate_input(type, valid_types, "type")
        if error:
            return error

        endpoint = ABBEndpoints.MOTION_MECHUNIT_SMBDATA_CLEAR.format(mechunit=mechunit)
        data = {
            'type': type,
        }
        return self.api.post(endpoint, data=data)

    def get_mechunit_cartesian(self, mechunit: str, tool: Optional[str] = None, 
                          wobj: Optional[str] = None, coordinate: Optional[str] = None, 
                          elog_at_err: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cartesian position of a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            tool: Optional tool name (e.g., 'tool0')
            wobj: Optional work object name (e.g., 'Wobj')
            coordinate: Optional coordinate system ('Base', 'World', 'Tool', or 'Wobj')
            elog_at_err: Optional error logging flag ('0' or '1')
            
        Returns:
            Response information with cartesian position
        """
        # Validate parameters only when they are provided
        if coordinate is not None:
            valid_coordinates = ['Base', 'World', 'Tool', 'Wobj']
            error = self._validate_input(coordinate, valid_coordinates, "coordinate")
            if error:
                return error
                
        if elog_at_err is not None:
            valid_elog_at_err = ['1', '0']
            error = self._validate_input(elog_at_err, valid_elog_at_err, "elog_at_err")
            if error:
                return error
                
        endpoint = ABBEndpoints.MOTION_MECHUNIT_CARTESIAN.format(mechunit=mechunit)
        
        params = {}
        if tool:
            params['tool'] = tool
        if wobj:
            params['wobj'] = wobj
        if coordinate:
            params['coordinate'] = coordinate
        if elog_at_err:
            params['elog-at-err'] = elog_at_err
            
        return self.api.get(endpoint, params=params)

    def get_mechunit_robtarget(self, mechunit: str, tool: Optional[str] = None, 
                          wobj: Optional[str] = None, coordinate: Optional[str] = None) -> Dict[str, Any]:
        """
        Get robot target position for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            parameters:
        - name: mechunit
          in: path
          description: '{mechunit}, Mechunit is case sensitive'
          required: true
          type: string
        - name: tool
          in: query
          description: '{tool_name}'
          required: false
          type: string
        - name: wobj
          in: query
          description: '{wobj_name}'
          required: false
          type: string
        - name: coordinate
          in: query
          description: '{Base | World | Tool | Wobj}'
          required: false
          type: string
        Returns:
            Response information with robot target position
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_ROBTARGET.format(mechunit=mechunit)
        params = {}
        if tool:
            params['tool'] = tool
        if wobj:
            params['wobj'] = wobj
        if coordinate:
            params['coordinate'] = coordinate

        return self.api.get(endpoint, params=params)

    def get_mechunit_jointtarget(self, mechunit: str) -> Dict[str, Any]:
        """
        Get joint target position for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with joint target position
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_JOINTTARGET.format(mechunit=mechunit)
        return self.api.get(endpoint)

    def get_mechunit_pjoints(self, mechunit: str) -> Dict[str, Any]:
        """
        Get physical joint values for a mechanical unit
        
        Args:
            mechunit: Name of the mechanical unit
            
        Returns:
            Response information with physical joint values
        """
        endpoint = ABBEndpoints.MOTION_MECHUNIT_PJOINTS.format(mechunit=mechunit)
        return self.api.get(endpoint)
    
class Vision(ABBBaseService):
    """Vision System functions for ABB robots"""
    
    def __init__(self, api: ABBRobotAPI):
        """
        Initialize with a reference to the ABB Robot API
        
        Args:
            api: An instance of the ABB Robot API
        """
        super().__init__(api)
        self.vision_base = ABBEndpoints.VISION_BASE
        # Initialize subscription helper
        self.sub_helper = SubscriptionHelper(self.api, self.logger)
    
    def get_vision_info(self) -> Dict[str, Any]:
        """
        Get information about the vision system
        
        Returns:
            Response information including number of cameras
        """
        return self.api.get(self.vision_base)
    
    def get_camera_job_name(self, camera_name: str) -> Dict[str, Any]:
        """
        Get the name of the job on a specific camera
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            Response information including job name
        """
        endpoint = ABBEndpoints.VISION_JOB_NAME.format(camera_name=camera_name)
        return self.api.get(endpoint)
    
    def get_camera_info(self, camera_index: str) -> Dict[str, Any]:
        """
        Get detailed information about a camera
        
        Args:
            camera_index: Index of the camera
            
        Returns:
            Response information with camera details
        """
        endpoint = ABBEndpoints.VISION_INFO.format(camera_index=camera_index)
        return self.api.get(endpoint)
    
    def restart_camera(self, camera_name: str) -> Dict[str, Any]:
        """
        Restart a camera
        
        Args:
            camera_name: Name of the camera to restart
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.VISION_RESTART.format(camera_name=camera_name)
        return self.api.post(endpoint)
    
    def set_flash_camera_led(self, camera_name: str) -> Dict[str, Any]:
        """
        Flash the LED of a camera to identify it
        
        Args:
            camera_name: Name of the camera to flash its LED
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.VISION_LED.format(camera_name=camera_name)
        return self.api.post(endpoint)
    
    def refresh_camera(self) -> Dict[str, Any]:
        """
        Refresh the camera list
        
        Returns:
            Response information
        """
        return self.api.post(ABBEndpoints.VISION_REFRESH)
    
    def set_camera_hostname(self, camera_name: str, hostname: str) -> Dict[str, Any]:
        """
        Set the hostname of a camera
        
        Args:
            camera_name: Name of the camera
            hostname: New hostname for the camera
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.VISION_HOSTNAME.format(camera_name=camera_name)
        data = {'host-name': hostname}
        return self.api.post(endpoint, data=data)
    
    def set_camera_name(self, camera_index: str, camera_name: str) -> Dict[str, Any]:
        """
        Set the name of a camera
        
        Args:
            camera_index: Index of the camera
            camera_name: New name for the camera
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.VISION_NAME.format(camera_index=camera_index)
        data = {'name': camera_name}
        return self.api.post(endpoint, data=data)

    def set_camera_user(self, camera_index: str, user: str, password: str) -> Dict[str, Any]:
        """
        Set the user credentials of a camera
        
        Args:
            camera_index: Index of the camera
            user: Username for camera authentication
            password: Password for camera authentication
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.VISION_USER.format(camera_index=camera_index)
        data = {'user': user, 'password': password}
        return self.api.post(endpoint, data=data)

    def get_camera_network(self, camera_name: str) -> Dict[str, Any]:
        """
        Get network settings of a camera
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            Response information with network settings
        """
        endpoint = ABBEndpoints.VISION_NETWORK.format(camera_name=camera_name)
        return self.api.get(endpoint)

    def set_camera_network(self, camera_name: str, method: str, address: str, netmask: str, gateway: str) -> Dict[str, Any]:
        """
        Set network settings of a camera
        
        Args:
            camera_name: Name of the camera
            method: IP config method, Should be one of 'fixip' or 'dhcp'
            address: IP address, Applicable only for setting fix IP
            netmask: Subnetmask address, Applicable only for setting fix IP
            gateway: Default Gateway, Applicable only for setting fix IP
            
        Returns:
            Response information
        """
        valid_methods = ['fixip', 'dhcp']
        error = self._validate_input(method, valid_methods, "network method")
        if error:
            return error
            
        endpoint = ABBEndpoints.VISION_NETWORK.format(camera_name=camera_name)
        data = {
            'method': method,
            'address': address,
            'netmask': netmask,
            'gateway': gateway
        }
        return self.api.post(endpoint, data=data)
    
    def get_vision_state_and_subscribe(self, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Get the current vision system state and then subscribe to changes
        
        Args:
            callback: Function to call when events are received
            
        Returns:
            Dictionary with initial vision system state and subscription ID
        """
        self.logger.warning("DEPRECATED: get_vision_state_and_subscribe is deprecated. Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.")
        
        initial_state, subscription_id = self.sub_helper.get_vision_state_and_subscribe(callback)
        
        return {
            'initial_state': initial_state,
            'subscription_id': subscription_id
        }
    
    # subscribe_to_vision_changes method has been removed.
    # Subscription functionality is now centralized in ABBRobot.subscription_manager


class RAPID(ABBBaseService):
    """RAPID programming and execution control for ABB robots"""
    
    def __init__(self, api: ABBRobotAPI):
        """
        Initialize with a reference to the ABB Robot API
        
        Args:
            api: An instance of the ABB Robot API
        """
        super().__init__(api)
        self.rapid_base = ABBEndpoints.RAPID_BASE
        # Initialize subscription helper
        self.sub_helper = SubscriptionHelper(self.api, self.logger)
        
    def get_execution_state(self) -> Dict[str, Any]:
        """
        Get the RAPID execution state
        
        Returns:
            Response information with execution state
        """
        return self.api.get(ABBEndpoints.RAPID_EXECUTION)
    
    def set_execution_start(self, regain: str, execmode: str, cycle: str, condition: str, stopatbp: str, alltaskbytsp: str) -> Dict[str, Any]:
        """
        Start RAPID execution
        
        Args:
            regain: {continue | regain | clear | continueconsume}
            execmode: {continue | stepin | stepover | stepout | stepback | steplast | stepmotion}
            cycle: {forever | asis | once}
            condition: {none | callchain}
            stopatbp: {disabled | enabled} (stop at breakpoint)
            alltaskbytsp: {true | false}
            
        Returns:
            Response information
        """
        valid_regain = ['continue', 'regain', 'clear', 'continueconsume']
        valid_execmode = ['continue', 'stepin', 'stepover', 'stepout', 'stepback', 'steplast', 'stepmotion']
        valid_cycle = ['forever', 'asis', 'once']
        valid_condition = ['none', 'callchain']
        valid_stopatbp = ['disabled', 'enabled']
        valid_alltaskbytsp = ['true', 'false']
        
        error = self._validate_input(regain, valid_regain, "regain")
        if error:
            return error
        error = self._validate_input(execmode, valid_execmode, "execmode")
        if error:
            return error
        error = self._validate_input(cycle, valid_cycle, "cycle")
        if error:
            return error
        error = self._validate_input(condition, valid_condition, "condition")
        if error:
            return error
        error = self._validate_input(stopatbp, valid_stopatbp, "stopatbp")
        if error:
            return error
        error = self._validate_input(alltaskbytsp, valid_alltaskbytsp, "alltaskbytsp")
        if error:
            return error
        
        data = {
            'regain': regain, 
            'execmode': execmode, 
            'cycle': cycle, 
            'condition': condition, 
            'stopatbp': stopatbp, 
            'alltaskbytsp': alltaskbytsp
        }
        return self.api.post(ABBEndpoints.RAPID_EXECUTION_START, data=data)
    
    def set_execution_stop(self, stopmode: str, usetsp: str) -> Dict[str, Any]:
        """
        Stop RAPID execution
        
        Args:
            stopmode: {cycle | instr | stop | qstop} (default: stop)
            usetsp: {normal | alltsk} (default: normal)
            
        Returns:
            Response information
        """
        valid_stopmode = ['cycle', 'instr', 'stop', 'qstop']
        valid_usetsp = ['normal', 'alltsk']
        
        error = self._validate_input(stopmode, valid_stopmode, "stopmode")
        if error:
            return error
        error = self._validate_input(usetsp, valid_usetsp, "usetsp")
        if error:
            return error
        
        data = {'stopmode': stopmode, 'usetsp': usetsp}
        return self.api.post(ABBEndpoints.RAPID_EXECUTION_STOP, data=data)
    
    def set_execution_resetpp(self) -> Dict[str, Any]:
        """
        Reset RAPID program pointer
        
        Returns:
            Response information
        """
        return self.api.post(ABBEndpoints.RAPID_EXECUTION_RESETPP)
       
    def set_execution_cycle(self, cycle: str) -> Dict[str, Any]:
        """
        Set the RAPID execution cycle
        
        Args:
            cycle: Execution cycle to set ('once', 'forever')
            
        Returns:
            Response information
        """
        valid_cycles = ['once', 'forever']
        error = self._validate_input(cycle, valid_cycles, "execution cycle")
        if error:
            return error
            
        data = {'cycle': cycle}
        return self.api.post(ABBEndpoints.RAPID_EXECUTION_CYCLE, data=data)
    
    def get_modules(self) -> Dict[str, Any]:
        """
        Get the list of RAPID modules
        
        Returns:
            Response information with modules
        """
        return self.api.get(ABBEndpoints.RAPID_MODULES)
    
    def get_robtarget_from_task(self, task: str, tool: Optional[str] = None, wobj: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the RAPID robtarget from a task
        
        Args:
            task: Task name
            tool: Optional tool name
            wobj: Optional work object name
            
        Returns:
            Response information with robtarget
        """
        endpoint = ABBEndpoints.RAPID_ROBTARGET.format(task=task)
        params = {}
        if tool is not None:
            params['tool'] = tool
        if wobj is not None:
            params['wobj'] = wobj
        return self.api.get(endpoint, params=params)
    
    def get_jointtarget_from_task(self, task: str) -> Dict[str, Any]:
        """
        Get the RAPID jointtarget from a task
        
        Args:
            task: Task name
            
        Returns:
            Response information with jointtarget
        """
        endpoint = ABBEndpoints.RAPID_JOINTTARGET.format(task=task)
        return self.api.get(endpoint)
    
    def get_rapid_modules(self, task: str) -> Dict[str, Any]:
        """
        Get the RAPID modules from a task
        
            Args:
                task: Task name

            Returns:
                    Response information with rapid program
        """
        endpoint = ABBEndpoints.RAPID_MODULES_TASK.format(task=task)
        return self.api.get(endpoint)


    def get_rapid_program(self, task: str, continue_on_err: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the RAPID program from a task
        
        Args:
            task: Task name
            continue_on_err: {1|0} Default value is 0. In case input is 1, 
                             the API continues execution even if any error occurs.
            
        Returns:
            Response information with rapid program
        """
        if continue_on_err is not None:
            valid_continue_on_err = ['1', '0']
            error = self._validate_input(continue_on_err, valid_continue_on_err, "continue-on-err")
            if error:
                return error
                
        endpoint = ABBEndpoints.RAPID_PROGRAM.format(task=task)
        params = {}
        if continue_on_err is not None:
            params['continue-on-err'] = continue_on_err
        return self.api.get(endpoint, params=params)

    def get_rapid_symbool_resources(self) -> Dict[str, Any]:
        """
        Get the list of RAPID symbol resources
        
        Returns:
            Response information with symbol resources
        """
        endpoint = ABBEndpoints.RAPID_SYMBOL_RESOURCES
        return self.api.get(ABBEndpoints.RAPID_SYMBOL_RESOURCES)

    def set_rapid_symbol_search(self, view: str = None, vartyp: str = None, blockurl: str = None, recursive: str = None, posl: str = None, posc: str = None, stack: str = None, onlyused: str = None, 
                                skipshared: str = None, regexp: str = None, symtyp: str = None, dattyp: str = None) -> Dict[str, Any]:
        """
        Search for RAPID symbols
        
        Args:
            search: Search string
                    The dataparam "typurl" is available from RW version 7.1 onwards.
      consumes:
        - application/x-www-form-urlencoded;v=2.0
      produces:
        - application/xhtml+xml;v=2.0
        - application/hal+json;v=2.0
      parameters:
        - name: request-body
          in: body
          description: Data parameter(s).At least one data parameter should be provided.
          schema:
            type: object
            properties:
              view:
                description: >-
                  {block | scope | stack }, For both scope and stack you must
                  use blockurl with task, for stack even program pointer should
                  be set.
                type: string
              vartyp:
                description: '{udef | rw | ro | loop | any},Variable type to be searched.'
                type: string
              blockurl:
                description: >-
                  {string},Relative URL describing the block where the search
                  should start.
                type: string
              recursive:
                description: >-
                  {TRUE | FALSE},True if search should be recursive otherwise
                  false.
                type: string
              posl:
                description: '{position row},Line position in module.'
                type: string
              posc:
                description: >-
                  {position col},Column position in module (if posl and posc are
                  both 0 is the blockurl used instead).
                type: string
              stack:
                description: '{integer},stackframe to search when searching in stack.'
                type: string
              onlyused:
                description: '{TRUE|FALSE},True if only used symbols should be returned.'
                type: string
              skipshared:
                description: >-
                  {TRUE|FALSE},True when shared symbols should be
                  skipped,otherwise False.
                type: string
              regexp:
                description: '{regular expression}'
                type: string
              symtyp:
                description: >-
                  { atm | rec | ali | rcp | con | var | per | par | lab | for |
                  fun | prc | trp | mod | tsk | any | udef}. Type of Symbol to
                  be searched.atm-Atomic type, rec-Record type, ali-Alias type,
                  rcp-Record component, con-Constant, var-Variable,
                  per-Persistent, par-Parameter, lab-Label, for-For statement,
                  fun-Function, prc-Procedure, trp-Trap, mod-Module, tsk-Task,
                  any-any of the above symbol type
                type: string
              typurl:
                description: '{string}. URL to type symbol, to filter user defined data type'
                type: string
              dattyp:
                description: '{string},Datatype which has to be filtered.'
                type: string
            example: >-
              view=string&vartyp=string&blockurl=string&recursive=string&posl=string&posc=string&stack=string&onlyused=string&skipshared=string&regexp=string&symtyp=string&dattyp=string
        """
        valid_view = ['block', 'scope', 'stack']
        valid_vartyp = ['udef', 'rw', 'ro', 'loop', 'any']
        valid_recursive = ['TRUE', 'FALSE']
        valid_onlyused = ['TRUE', 'FALSE']
        valid_skipshared = ['TRUE', 'FALSE']
        valid_symtyp = ['atm', 'rec', 'ali', 'rcp', 'con', 'var', 'per', 'par', 'lab', 'for', 'fun', 'prc', 'trp', 'mod', 'tsk', 'any', 'udef']

        error = self._validate_input(view, valid_view, "view")
        if error:
            return error
        error = self._validate_input(vartyp, valid_vartyp, "vartyp")
        if error:
            return error    
        error = self._validate_input(recursive, valid_recursive, "recursive")
        if error:
            return error
        error = self._validate_input(onlyused, valid_onlyused, "onlyused")
        if error:
            return error
        error = self._validate_input(skipshared, valid_skipshared, "skipshared")
        if error:
            return error
        error = self._validate_input(symtyp, valid_symtyp, "symtyp")
        if error:
            return error
        
        data = {
            'view': view,
            'vartyp': vartyp,
            'blockurl': blockurl,
            'recursive': recursive,
            'posl': posl,
            'posc': posc,
            'stack': stack,
            'onlyused': onlyused,
            'skipshared': skipshared,
            'regexp': regexp,
            'symtyp': symtyp,
            'dattyp': dattyp
        }
        endpoint = ABBEndpoints.RAPID_SYMBOL_SEARCH
        return self.api.post(endpoint, data=data)

    def get_rapid_symbol_data(self, symbolurl: str, value: Optional[str] = None) -> Dict[str, Any]:
        """
        Get data of a RAPID symbol
        
        Args:
            symbolurl: Symbol URL
            value: Optional - 'raw' returns a non-stringify json value
            
        Returns:
            Response information with symbol data
        """
        endpoint = ABBEndpoints.RAPID_SYMBOL_DATA.format(symbolurl=symbolurl)
        params = {}
        if value is not None:
            params['value'] = value
        return self.api.get(endpoint, params=params)
    
    def set_rapid_symbol_data(self, symbolurl: str, data: str, initval: Optional[str] = None, log: Optional[str] = None) -> Dict[str, Any]:
        """
        Set the data of a RAPID symbol
        
        Args:
            symbolurl: Symbol URL
            data: Value to set (wrapped in "value": data)
            initval: Optional - set initial value instead of current
            log: Optional - write change to event log

        Returns:
            Response information
        """
        endpoint = ABBEndpoints.RAPID_SYMBOL_DATA.format(symbolurl=symbolurl)
        data = {
            "value": data
        }

        return self.api.post(endpoint, data=data)
    
    def get_aliasio(self, start: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get the list of RAPID alias I/O signals
        
        Args:
            start: Start position
            limit: Number of aliasios to return
            
        Returns:
            Response information with alias I/Os
        """
        params = {}
        if start is not None:
            params['start'] = str(start)
        if limit is not None:
            params['limit'] = str(limit)
        return self.api.get(ABBEndpoints.RAPID_ALIASIO, params=params)
    
    def get_tasks(self) -> Dict[str, Any]:
        """
        Get the list of RAPID tasks
        
        Returns:
            Response information with tasks
        """
        return self.api.get(ABBEndpoints.RAPID_TASKS)
    
    def set_task_activate(self, task: str) -> Dict[str, Any]:
        """
        Activate a RAPID task
        
        Args:
            task: Task name
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.RAPID_TASK_ACTIVATE.format(task=task)
        return self.api.post(endpoint)
    
    
    def set_task_deactivate(self, task: str) -> Dict[str, Any]:
        """
        Deactivate a RAPID task
        
        Args:
            task: Task name
            
        Returns:
            Response information
        """
        endpoint = ABBEndpoints.RAPID_TASK_DEACTIVATE.format(task=task)
        return self.api.post(endpoint)

    def get_execution_state_and_subscribe(self, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        DEPRECATED: Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.
        
        This method is maintained for backward compatibility but will be removed in future versions.
        
        Get the current execution state and then subscribe to changes
        
        Args:
            callback: Function to call when execution state changes
            
        Returns:
            Dictionary with initial execution state and subscription ID
        """
        self.logger.warning("DEPRECATED: get_execution_state_and_subscribe is deprecated. Use ABBRobot.setup_combined_subscription() and subscribe_to_collected_resources() instead.")
        
        initial_state, subscription_id = self.sub_helper.get_rapid_execution_state_and_subscribe(callback)
        
        return {
            'initial_state': initial_state,
            'subscription_id': subscription_id
        }
    
    def get_tasks_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get comprehensive information about all RAPID tasks
        
        Returns:
            Dictionary with task information including execution state
        """
        # First get list of all tasks
        tasks_response = self.get_tasks()
        if tasks_response.get('status_code') != 200:
            self.logger.error(f"Failed to get tasks: {tasks_response}")
            return {'tasks': []}
            
        # Get execution state
        exec_state = self.get_execution_state()
        
        # Combine information
        tasks_info = []
        
        if 'content' in tasks_response:
            task_list = tasks_response.get('content', {}).get('tasks', [])
            for task in task_list:
                task_name = task.get('name')
                if task_name:
                    # Try to get program info for this task
                    try:
                        program_info = self.get_rapid_program(task_name)
                        task['program_info'] = program_info.get('content', {})
                    except Exception as e:
                        self.logger.warning(f"Failed to get program info for task {task_name}: {e}")
                        
                    # Add to result list
                    tasks_info.append(task)
                    
        return {
            'tasks': tasks_info,
            'execution_state': exec_state.get('content', {})
        }

class ABBRobot:
    """
    Main class for ABB Robot Web Services API
    
    This class provides access to all ABB Robot Web Services functionality
    through a unified interface. It includes services for:
    - Panel controls (speed ratio, controller state, operation mode)
    - IO system functions for signal management
    - Motion system control and monitoring
    - RAPID programming and execution
    - Vision system functions
    - User management functions
    - Controller-specific functions
    
    The class also provides a centralized subscription management system
    through the subscription_manager property. This should be used for
    all new code instead of the individual subscription methods in each
    service class (which are now deprecated).
    
    Example usage of the centralized subscription system:
    
    ```python
    # Set up combined subscription
    robot.setup_combined_subscription(
        collect_signals=True,
        collect_panel=True,
        collect_rapid=True
    )
    
    # Get initial values
    initial_values = robot.get_initial_values()
    
    # Create subscription for all resources
    subscription_id = robot.subscribe_to_collected_resources()
    
    # Unsubscribe when done
    robot.unsubscribe_all()
    ```
    
    The class also provides utilities for managing subscriptions:
    - check_subscription_status(subscription_id): Get the status of a subscription
    - list_active_subscriptions(): List all active subscriptions
    - ping_subscription(subscription_id): Check if a subscription is still active
    - unsubscribe(subscription_id): Unsubscribe from a specific subscription
    """
    
    def __init__(self, host: str = 'localhost:80', 
                username: str = 'Default User', 
                password: str = 'robotics', 
                protocol: str = 'https://', 
                debug: bool = False):
        """
        Initialize the ABB Robot API
        
        Args:
            host: Host name and port of the robot controller
            username: Username for authentication
            password: Password for authentication
            protocol: Protocol to use (http:// or https://)
            debug: Enable debug logging
        """
        from .abb_base import ABBRobotAPI
        
        self.api = ABBRobotAPI(
            host=host,
            username=username,
            password=password,
            protocol=protocol,
            debug=debug
        )
        
        self.logger = self.api.logger
        
        # Initialize all services
        self.panel = Panel(self.api)
        self.user = User(self.api)
        self.controller = Controller(self.api)
        self.io = IO(self.api)
        self.motion = MotionSystem(self.api)
        self.rapid = RAPID(self.api)
        self.vision = Vision(self.api)
        
        # Initialize subscription helper - used for individual service subscriptions
        self.subscription_helper = SubscriptionHelper(self.api, self.logger)
        
        # Initialize central subscription manager - for combined subscriptions
        self.subscription_manager = SubscriptionManager(self.api, self.logger)
        
        # Initialize subscription parser for parsing event XML
        from .abb_robot_utils import SubscriptionParser
        self.subscription_parser = SubscriptionParser(self.logger)
        
        # Set default values
        self.connected = False
        
    def connect(self) -> bool:
        """
        Connect to the robot controller
        
        Returns:
            True if connection was successful
        """
        return self.api.connect()
        
    def disconnect(self) -> bool:
        """
        Disconnect from the robot controller
        
        Returns:
            True if disconnect was successful
        """
        return self.api.disconnect()
        
    def get(self, uri: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send a GET request to the robot controller
        
        Args:
            uri: The URI to request
            headers: Additional headers to include
            
        Returns:
            Response information dictionary
        """
        return self.api.get(uri, headers)
        
    def post(self, uri: str, 
            data: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send a POST request to the robot controller
        
        Args:
            uri: The URI to request
            data: The data to send
            headers: Additional headers to include
            
        Returns:
            Response information dictionary
        """
        return self.api.post(uri, data, headers)
        
    def subscribe(self, resources: Dict[str, Any], callback: Optional[Callable] = None) -> str:
        """
        Subscribe to robot controller events
        
        Args:
            resources: Dictionary of resources to subscribe to
            callback: Callback function for events
            
        Returns:
            Subscription ID if successful
        """
        return self.api.subscribe(resources, callback)
        
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a subscription
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            True if successfully unsubscribed
        """
        return self.api.unsubscribe(subscription_id)
    
    def check_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """
        Check the status of a subscription
        
        Args:
            subscription_id: ID of the subscription to check
            
        Returns:
            Status information about the subscription
        """
        return self.api.check_subscription_status(subscription_id)
    
    def list_active_subscriptions(self) -> Dict[str, Any]:
        """
        List all active subscriptions
        
        Returns:
            Dictionary of subscription IDs and their status
        """
        return self.api.list_active_subscriptions()
    
    def ping_subscription(self, subscription_id: str) -> bool:
        """
        Check if a subscription is still active
        
        Args:
            subscription_id: ID of the subscription to check
            
        Returns:
            True if subscription is active
        """
        return self.api.ping_subscription(subscription_id)
    
    def parse_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse event XML from WebSocket subscription
        
        Args:
            xml_str: XML string to parse
            
        Returns:
            Parsed event data
        """
        # Create a subscription parser to parse XML
        parser = SubscriptionParser(self.logger)
        return parser.parse_event_xml(xml_str)
        
    def setup_combined_subscription(self, collect_signals: bool = True,
                                  collect_panel: bool = True,
                                  collect_rapid: bool = True,
                                  collect_motion: bool = True,
                                  collect_vision: bool = True,
                                  collect_user: bool = True,
                                  io_signals: Optional[List[str]] = None) -> None:
        """
        Set up a combined subscription that collects resources from multiple services 
        and gets their initial values before subscribing.
        
        This method prepares the subscriptions but doesn't actually create them.
        Call subscribe_to_collected_resources() to create the actual subscription.
        
        Args:
            collect_signals: Collect IO signals
            collect_panel: Collect panel resources
            collect_rapid: Collect RAPID execution resources
            collect_motion: Collect motion system resources
            collect_vision: Collect vision system resources
            io_signals: List of specific IO signal paths to collect
            
        Returns:
            None
        """
        # Reset the subscription manager
        self.subscription_manager.reset()
        
        # Add IO signals if requested
        if collect_signals:
            if io_signals:
                # Add specific IO signals
                for signal_path in io_signals:
                    self.logger.info(f"Adding IO signal {signal_path} to combined subscription")
                    self.subscription_manager.add_io_signal(f'{signal_path};state', {'p': '1'})
        if collect_user:
            self.logger.info("Adding user management resources to combined subscription")
            self.subscription_manager.add_resource(ABBEndpoints.RMPP_USER_INFO, {'p': '1'})
        # Add panel resources if requested
        if collect_panel:
            self.logger.info("Adding panel resources to combined subscription")
            # Use specific parameters for subscription to improve event data format
            self.subscription_manager.add_resource(ABBEndpoints.CTRL_STATE, {'p': '1', 'resource': 'ctrl-state'})
            self.subscription_manager.add_resource(ABBEndpoints.OPMODE, {'p': '1', 'resource': 'opmode'})
            self.subscription_manager.add_resource(ABBEndpoints.SPEED_RATIO, {'p': '1', 'resource': 'speedratio'})
            
        # Add RAPID execution resources if requested
        if collect_rapid:
            self.logger.info("Adding RAPID execution resources to combined subscription")
            self.subscription_manager.add_resource(f'{ABBEndpoints.RAPID_EXECUTION};ctrlexecstate', {'p': '1'})
            
        # Add motion system resources if requested
        if collect_motion:
            self.logger.info("Adding motion system resources to combined subscription")
            self.subscription_manager.add_resource(f'{ABBEndpoints.MOTION_ERRORSTATE};erroreventchange', {'p': '1'})
            
        # Add vision system resources if requested
        if collect_vision:
            self.logger.info("Adding vision system resources to combined subscription")
            self.subscription_manager.add_resource(ABBEndpoints.VISION_BASE, {'p': '1'})
    
    def subscribe_to_collected_resources(self, callback: Optional[Callable] = None) -> str:
        """
        Subscribe to all collected resources with a single subscription
        
        Args:
            callback: Optional callback function for subscription events
            
        Returns:
            Subscription ID
        """
        self.logger.info("Creating subscription for all collected resources")
        
        if callback:
            # If a callback is provided, use it for the subscription
            return self.api.subscribe(self.subscription_manager.resources, callback)
        else:
            # Otherwise use the default subscription manager
            return self.subscription_manager.subscribe_all()
    
    def get_initial_values(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all initial values collected before subscription
        
        Returns:
            Dictionary of resource paths to initial values
        """
        return self.subscription_manager.get_initial_values()
        
    def unsubscribe_all(self) -> bool:
        """
        Unsubscribe from all subscriptions created by the subscription manager
        
        Returns:
            True if all unsubscriptions were successful
        """
        self.logger.info("Unsubscribing from all subscriptions")
        return self.subscription_manager.unsubscribe_all()

