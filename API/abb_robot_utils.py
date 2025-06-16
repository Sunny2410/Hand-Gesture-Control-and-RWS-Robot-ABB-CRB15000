"""
ABB Robot Utilities

This file contains utility functions for working with ABB Robot services
including IO signals, subscriptions, and data processing across different modules.
It separates the data processing logic from the API calls to provide better organization.

Author: Sunny24
Date: May 21, 2025
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

# Define XML namespace used in ABB responses
NAMESPACE = '{http://www.w3.org/1999/xhtml}'

class IOSignalProcessor:
    """
    Utility class for processing IO signal data from ABB robots
    """
    
    def __init__(self, logger=None):
        """
        Initialize the IO Signal Processor
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger('IOSignalProcessor')
        self.signal_cache = {}  # Cache signal_name -> full path
    
    def short_signal_path(self, signal_path: str) -> str:
        """
        Normalize a signal path to the standard format
        """
        prefix = "/rw/iosystem/"
        if signal_path.startswith(prefix):
            return signal_path[len(prefix):]
        return signal_path

    def parse_io_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse IO signal event XML data into a structured format
        
        Args:
            xml_str: XML string from WebSocket event
            
        Returns:
            Dictionary with parsed signal data:
            {
                'signal_name': 'Name',
                'signal_path': 'Path',
                'lvalue': 'Value',
                'lstate': 'State',
                'quality': 'Quality',
                'time': 'Timestamp'
            }
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_str)
            result = {}
            
            # Find the signal event element (class="ios-signalstate-ev")
            for li in root.findall(f".//{NAMESPACE}li"):
                class_name = li.attrib.get('class', '')
                
                if 'ios-signalstate-ev' in class_name:
                    # Get signal name/path from title attribute
                    signal_path = li.attrib.get('title', '')
                    result['signal_path'] = signal_path
                    
                    # Extract signal name from path (last segment)
                    if signal_path and '/' in signal_path:
                        # Check if path ends with ';state' and remove it for the signal name
                        path_part = signal_path.split('/')[-1]
                        if ';state' in path_part:
                            result['signal_name'] = path_part.split(';')[0]
                        else:
                            result['signal_name'] = path_part
                    else:
                        # Default case
                        if ';state' in signal_path:
                            result['signal_name'] = signal_path.split(';')[0]
                        else:
                            result['signal_name'] = signal_path
                        
                    # Get self link 
                    a_self = li.find(f"./{NAMESPACE}a[@rel='self']")
                    if a_self is not None:
                        result['href'] = a_self.attrib.get('href', '')
                    
                    # Find all span elements to get signal details
                    for span in li.findall(f"./{NAMESPACE}span"):
                        if 'class' in span.attrib:
                            class_val = span.attrib['class']
                            result[class_val] = span.text
            
            # Log found data
            if result:
                self.logger.debug(f"Parsed IO event data: {result}")
            else:
                self.logger.warning(f"No IO signal data found in event XML")
                            
            return result
        except Exception as e:
            self.logger.error(f"Error parsing IO event XML: {str(e)}")
            self.logger.debug(f"Raw XML: {xml_str[:500]}")  # Log part of the raw XML for debugging
            return {}
            
    def normalize_signal_path(self, path: str) -> str:
        """
        Normalize a signal path to the standard format
        
        Args:
            path: Signal path to normalize
            
        Returns:
            Normalized signal path
        """
        # Ensure path starts with the correct prefix
        if not path.startswith('/'):
            path = f"/{path}"
            
        if not path.startswith('/rw/'):
            # If the path already has another format, apply correction
            if path.startswith('/iosystem/'):
                path = f"/rw{path}"
            elif path.startswith('/signals/'):
                path = f"/rw/iosystem{path}"
                
        return path
        
    def process_search_results(self, results: Dict[str, Any], 
                              search_name: Optional[str] = None,
                              exact_match: bool = False) -> List[str]:
        """
        Process signal search results
        
        Args:
            results: Search results from API
            search_name: Original name searched for (used with exact_match)
            exact_match: If True, only return exact matches
            
        Returns:
            List of signal paths
        """
        signal_paths = []
        
        if '_embedded' in results and 'resources' in results['_embedded']:
            signals = results['_embedded']['resources']
            self.logger.info(f"Found {len(signals)} signals based on search criteria.")
            
            # Process signals based on exact match flag
            for sig in signals:
                href = sig.get('_links', {}).get('self', {}).get('href')
                if not href:
                    continue
                    
                # Skip if exact match is requested but this signal doesn't match
                if exact_match and search_name is not None:
                    signal_name = href.split('/')[-1] if '/' in href else href
                    if 'name' not in sig or sig['name'] != search_name:
                        continue
            
                # Normalize path
                href = self.normalize_signal_path(href)
                
                # Add to results
                signal_paths.append(href)
                
                # Cache signal if name is available
                if 'name' in sig:
                    self.signal_cache[sig['name']] = href
        else:
            self.logger.warning("No signals found based on the search criteria.")
            
        self.logger.info(f"Returning {len(signal_paths)} signals after filtering")
        return signal_paths
            
    def build_search_params(self, name: Optional[str] = None, device: Optional[str] = None,
                           network: Optional[str] = None, category: Optional[str] = None,
                           category_pon: Optional[str] = None, type: Optional[str] = None,
                           invert: Optional[str] = None, blocked: Optional[str] = None,
                           suffix: str = '') -> Dict[str, str]:
        """
        Build search parameters dictionary for signal search
        
        Args:
            name: Signal name pattern
            device: Device name pattern
            network: Network name pattern
            category: Category name pattern
            category_pon: Category PON name pattern
            type: Signal type
            invert: 'true' or 'false' to invert signal
            blocked: 'true' or 'false' for blocked signals
            suffix: Suffix to add to parameter names (e.g., '2' for second criteria)
            
        Returns:
            Dictionary of search parameters
        """
        params = {}
        
        # Add parameters if provided
        if name is not None:
            params[f'name{suffix}'] = name
        if device is not None:
            params[f'device{suffix}'] = device  
        if network is not None:
            params[f'network{suffix}'] = network
        if category is not None:
            params[f'category{suffix}'] = category
        if category_pon is not None:
            params[f'category-pon{suffix}'] = category_pon
        if type is not None:
            params[f'type{suffix}'] = type
        if invert is not None:
            params[f'invert{suffix}'] = invert
        if blocked is not None:
            params[f'blocked{suffix}'] = blocked
            
        return params
    
    def get_signal_paths(self, api, endpoint_signals_search: str, name: Optional[str] = None, 
                       exact_match: bool = False) -> List[str]:
        """
        Get signal paths for a given name pattern
        
        Args:
            api: The ABB Robot API instance to use for requests
            endpoint_signals_search: The endpoint for signal search
            name: Signal name or name pattern to search for
            exact_match: If True, only return exact matches
            
        Returns:
            List of signal paths matching the criteria
        """
        # Build search parameters
        params = self.build_search_params(name=name)
        
        # Call API with search parameters
        results = api.post(endpoint_signals_search, data=params)
        
        # Process search results
        if not isinstance(results, dict) or 'status_code' not in results or results['status_code'] != 200:
            self.logger.error(f"Failed to get signal paths. Response: {results}")
            return []

        if 'content' in results:
            signal_paths = self.process_search_results(
                results['content'], 
                search_name=name, 
                exact_match=exact_match
            )
            return signal_paths
        else:
            self.logger.error("No content in signal search response")
            return []


class SubscriptionParser:
    """
    Utility class for parsing subscription data from ABB robots
    """
    
    def __init__(self, logger=None):
        """
        Initialize the Subscription Parser
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger('SubscriptionParser')
        
    def _sanitize_xml(self, xml_str: str) -> str:
        """
        Sanitize XML string for parsing to handle potential encoding issues
        
        Args:
            xml_str: Raw XML string
            
        Returns:
            Sanitized XML string
        """
        try:
            # Check if the XML is already well-formed
            try:
                ET.fromstring(xml_str)
                return xml_str  # XML is valid, return as is
            except ET.ParseError:
                # Try to clean up the XML
                self.logger.warning("XML parse error, attempting to clean XML")
                
                # Replace problematic characters
                sanitized = xml_str.replace('&', '&amp;')
                
                # Ensure it has a root element
                if not sanitized.strip().startswith('<?xml') and not sanitized.strip().startswith('<'):
                    sanitized = f'<root>{sanitized}</root>'
                
                # Test if sanitized version can be parsed
                try:
                    ET.fromstring(sanitized)
                    return sanitized
                except ET.ParseError as e:
                    self.logger.error(f"Failed to sanitize XML: {e}")
                    # Return original as fallback
                    return xml_str
        except Exception as e:
            self.logger.error(f"Error sanitizing XML: {e}")
            return xml_str

    def parse_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse general event XML data
        
        Args:
            xml_str: XML string to parse
            
        Returns:
            Parsed event data
        """
        try:
            # Check if XML is empty or None
            if not xml_str:
                self.logger.warning("Empty XML string received")
                return {}
            
            # Sanitize XML before parsing
            xml_str = self._sanitize_xml(xml_str)
                
            root = ET.fromstring(xml_str)
            result = {}
            
            # Log number of li elements found for debug
            all_li = root.findall(f".//{NAMESPACE}li")
            self.logger.debug(f"Found {len(all_li)} li elements in XML")
            
            # Find all li elements with class for panel events
            for li in all_li:
                class_name = li.attrib.get('class', '')
                self.logger.debug(f"Found li element with class: {class_name}")
                
                # Panel events - check for different class patterns
                if class_name.startswith('pnl-') and class_name.endswith('-ev'):
                    # Extract key from class name
                    middle = class_name[len('pnl-'):-len('-ev')]
                    key = middle.replace('ctrlstate', 'controller_state').replace('opmode', 'operation_mode').replace('speedratio', 'speed_ratio')
                    
                    # Find child span to get value
                    span = li.find(f".//{NAMESPACE}span")
                    if span is not None:
                        result[key] = span.text
                        self.logger.debug(f"Found panel event: {key}={span.text}")
                    else:
                        # Try to find value in other ways
                        value_span = li.find(f".//{NAMESPACE}span[@class='value']")
                        if value_span is not None:
                            result[key] = value_span.text
                            self.logger.debug(f"Found panel event (value span): {key}={value_span.text}")
                        else:
                            # Just look for any span as a last resort
                            for span in li.findall(f".//{NAMESPACE}span"):
                                if span.text and span.text.strip():
                                    result[key] = span.text.strip()
                                    self.logger.debug(f"Found panel event (any span): {key}={span.text}")
                                    break
                
                # Direct check for specific panel data based on title attribute
                title = li.attrib.get('title', '')
                if '/rw/panel/ctrl-state' in title or title.endswith('ctrl-state'):
                    # Check for specific span class or any span as fallback
                    span = li.find(f".//{NAMESPACE}span[@class='ctrlstate']") or li.find(f".//{NAMESPACE}span")
                    if span is not None and span.text:
                        result['controller_state'] = span.text.lower()  # Normalize to lowercase
                        self.logger.debug(f"Found controller state from title: {span.text}")
                
                elif '/rw/panel/opmode' in title or title.endswith('opmode'):
                    # Check for specific span class or any span as fallback
                    span = li.find(f".//{NAMESPACE}span[@class='opmode']") or li.find(f".//{NAMESPACE}span")
                    if span is not None and span.text:
                        result['operation_mode'] = span.text
                        self.logger.debug(f"Found operation mode from title: {span.text}")
                
                elif '/rw/panel/speedratio' in title or title.endswith('speedratio'):
                    # Check for specific span class or any span as fallback
                    span = li.find(f".//{NAMESPACE}span[@class='speedratio']") or li.find(f".//{NAMESPACE}span")
                    if span is not None and span.text:
                        result['speed_ratio'] = span.text
                        self.logger.debug(f"Found speed ratio from title: {span.text}")
                        
                # Also check for any spans with specific class names that indicate panel data
                for span in li.findall(f".//{NAMESPACE}span"):
                    span_class = span.attrib.get('class', '')
                    if span_class == 'ctrlstate' and span.text:
                        result['controller_state'] = span.text.lower()  # Normalize to lowercase
                        self.logger.debug(f"Found controller state from span class: {span.text}")
                    elif span_class == 'opmode' and span.text:
                        result['operation_mode'] = span.text
                        self.logger.debug(f"Found operation mode from span class: {span.text}")
                    elif span_class == 'speedratio' and span.text:
                        result['speed_ratio'] = span.text
                        self.logger.debug(f"Found speed ratio from span class: {span.text}")
                        
            # If we found any results, log them
            if result:
                self.logger.info(f"Parsed event data: {result}")
            else:
                self.logger.warning("No panel data found in event XML")
                
            return result
        except Exception as e:
            self.logger.error(f"Error parsing event XML: {str(e)}")
            try:
                # Log a portion of the XML for debugging
                self.logger.debug(f"XML content (first 500 chars): {xml_str[:500]}")
            except:
                self.logger.debug("Could not print XML content")
            import traceback
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            return {}

    def parse_motion_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse motion system event XML data
        
        Args:
            xml_str: XML string from WebSocket event
            
        Returns:
            Dictionary with parsed motion system data
        """
        try:
            root = ET.fromstring(xml_str)
            result = {}
            
            # Process motion system events
            for li in root.findall(f".//{NAMESPACE}li"):
                class_name = li.attrib.get('class', '')
                
                if class_name.startswith('mot-') and class_name.endswith('-ev'):
                    # Extract key from class name
                    key = class_name[len('mot-'):-len('-ev')].replace('-', '_')
                    
                    # Find value in span
                    span = li.find(f"./{NAMESPACE}span")
                    if span is not None:
                        result[key] = span.text
                        
            return result
        except Exception as e:
            self.logger.error(f"Error parsing motion event XML: {str(e)}")
            return {}
            
    def parse_user_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse user event XML data
        
        Args:
            xml_str: XML string from WebSocket event
            
        Returns:
            Dictionary with parsed user data
        """
        try:
            root = ET.fromstring(xml_str)
            result = {}

            # Process user events
            for li in root.findall(f".//{NAMESPACE}li"):
                class_name = li.attrib.get('class', '')
                
                if class_name.startswith('user-') and class_name.endswith('-ev'):
                    # Extract key from class name
                    key = class_name[len('user-'):-len('-ev')].replace('-', '_')
                    
                    # Find value in span
                    span = li.find(f"./{NAMESPACE}span")
                    if span is not None:
                        result[key] = span.text
                        
            return result
        except Exception as e:
            self.logger.error(f"Error parsing user event XML: {str(e)}")
            return {}

    def parse_rapid_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse RAPID event XML data
        
        Args:
            xml_str: XML string from WebSocket event
            
        Returns:
            Dictionary with parsed RAPID data
        """
        try:
            root = ET.fromstring(xml_str)
            result = {}
            
            # Process RAPID events
            for li in root.findall(f".//{NAMESPACE}li"):
                class_name = li.attrib.get('class', '')
                
                if class_name.startswith('rap-') and class_name.endswith('-ev'):
                    # Extract key from class name
                    key = class_name[len('rap-'):-len('-ev')].replace('-', '_')
                    
                    # Find value in span
                    span = li.find(f"./{NAMESPACE}span")
                    if span is not None:
                        result[key] = span.text
                        
            return result
        except Exception as e:
            self.logger.error(f"Error parsing RAPID event XML: {str(e)}")
            return {}
            
    def parse_vision_event_xml(self, xml_str: str) -> Dict[str, Any]:
        """
        Parse Vision event XML data
        
        Args:
            xml_str: XML string from WebSocket event
            
        Returns:
            Dictionary with parsed vision data
        """
        try:
            root = ET.fromstring(xml_str)
            result = {}
            
            # Process Vision events
            for li in root.findall(f".//{NAMESPACE}li"):
                class_name = li.attrib.get('class', '')
                
                if class_name.startswith('vis-') and class_name.endswith('-ev'):
                    # Extract key from class name
                    key = class_name[len('vis-'):-len('-ev')].replace('-', '_')
                    
                    # Find value in span
                    span = li.find(f"./{NAMESPACE}span")
                    if span is not None:
                        result[key] = span.text
                        
            return result
        except Exception as e:
            self.logger.error(f"Error parsing Vision event XML: {str(e)}")
            return {}


class SubscriptionManager:
    """
    Centralized manager for subscriptions with initial value gathering
    """
    
    def __init__(self, api, logger=None):
        """
        Initialize the Subscription Manager
        
        Args:
            api: The ABB Robot API instance
            logger: Optional logger instance
        """
        self.api = api
        self.logger = logger or logging.getLogger('SubscriptionManager')
        self.io_processor = IOSignalProcessor(self.logger)
        
        # Store resources to subscribe to
        self.resources = {}
        
        # Store initial values for resources
        self.initial_values = {}
        
        # Store subscription IDs
        self.subscription_ids = []
        
        # Store callbacks for resources
        self.callbacks = {}
    
    def reset(self):
        """
        Reset the subscription manager
        """
        self.resources = {}
        self.initial_values = {}
        self.callbacks = {}
        
    def add_resource(self, resource: str, params: Optional[Dict[str, str]] = None, 
                    callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Add a resource to subscribe to and get its initial value
        
        Args:
            resource: Resource to subscribe to
            params: Subscription parameters
            callback: Callback function for this resource
            
        Returns:
            Initial value of the resource
        """
        # Set default params if not provided
        if params is None:
            params = {'p': '1'}
            
        # Get initial value
        initial_value = self.api.get(resource)
        
        # Store resource, initial value, and callback
        self.resources[resource] = params
        self.initial_values[resource] = initial_value
        
        if callback:
            self.callbacks[resource] = callback
            
        return initial_value
    
    def add_io_signal(self, signal_path: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Add an IO signal to subscribe to and get its initial value
        
        Args:
            signal_path: Signal path
            callback: Callback function for this signal
            
        Returns:
            Initial value of the signal
        """
        # Normalize signal path
        signal_path = self.io_processor.normalize_signal_path(signal_path)
        
        # Get initial value and add resource
        return self.add_resource(signal_path, {'p': '1'}, callback)
    
    def subscribe_all(self, callback: Optional[Callable] = None) -> str:
        """
        Subscribe to all collected resources with a single subscription
        
        Args:
            callback: Optional callback function to override the router callback
            
        Returns:
            Subscription ID
        """
        if not self.resources:
            self.logger.warning("No resources to subscribe to")
            return ""
            
        # If a specific callback is provided, use it instead of the router
        if callback:
            subscription_id = self.api.subscribe(self.resources, callback)
        else:
            # Create a wrapper callback that routes events to individual callbacks
            def router_callback(xml_str: str) -> None:
                try:
                    # Parse XML to determine which resource triggered the event
                    root = ET.fromstring(xml_str)
                    
                    # Extract resource info from event data
                    for li in root.findall(f".//{NAMESPACE}li"):
                        # Get the resource path from title attribute or href
                        resource_path = None
                        title = li.attrib.get('title', '')
                        if title:
                            resource_path = title
                        else:
                            # Try to get href from self link
                            a_self = li.find(f"./{NAMESPACE}a[@rel='self']")
                            if a_self is not None:
                                resource_path = a_self.attrib.get('href', '')
                        
                        if resource_path:
                            # Find the matching callback
                            for res, callback in self.callbacks.items():
                                # Simple check if resource path contains the resource
                                # Could be improved for more precise matching
                                if res in resource_path or resource_path in res:
                                    if callback:
                                        # Call the callback with the event data
                                        callback(xml_str)
                                    break
                except Exception as e:
                    self.logger.error(f"Error in subscription router: {str(e)}")
            
            # Subscribe to all resources at once
            subscription_id = self.api.subscribe(self.resources, router_callback)
        
        if subscription_id:
            self.logger.info(f"Created subscription {subscription_id} for {len(self.resources)} resources")
            self.subscription_ids.append(subscription_id)
        else:
            self.logger.error("Failed to create subscription")
            
        return subscription_id
        
    def get_initial_values(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all collected initial values
        
        Returns:
            Dictionary of resource paths to initial values
        """
        return self.initial_values
    
    def unsubscribe_all(self) -> bool:
        """
        Unsubscribe from all subscriptions
        
        Returns:
            True if all unsubscriptions were successful
        """
        success = True
        for subscription_id in self.subscription_ids:
            result = self.api.unsubscribe(subscription_id)
            if not result:
                self.logger.error(f"Failed to unsubscribe from {subscription_id}")
                success = False
                
        # Clear subscription IDs
        self.subscription_ids = []
        
        return success

class SubscriptionHelper:
    """
    Helper for managing subscriptions and retrieving initial values
    """
    
    def __init__(self, api, logger=None):
        """
        Initialize the Subscription Helper
        
        Args:
            api: The ABB Robot API instance
            logger: Optional logger instance
        """
        self.api = api
        self.logger = logger or logging.getLogger('SubscriptionHelper')
        
    def get_initial_value_and_subscribe(self, endpoint: str, 
                                      callback: Optional[Callable] = None, 
                                      resource_params: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, Any], str]:
        """
        Get the initial value of a resource and then subscribe to changes
        
        Args:
            endpoint: The endpoint to get value from and subscribe to
            callback: Function to call when events are received
            resource_params: Parameters for resource subscription
            
        Returns:
            Tuple of (initial value, subscription ID)
        """
        # Get initial value
        initial_value = self.api.get(endpoint)
        
        # Set up subscription
        if resource_params is None:
            resource_params = {'p': '1'}
            
        resources = {endpoint: resource_params}
        subscription_id = self.api.subscribe(resources, callback)
        
        return initial_value, subscription_id
    
    def get_io_signal_value_and_subscribe(self, signal_path: str, 
                                         callback: Optional[Callable] = None) -> Tuple[Dict[str, Any], str]:
        """
        Get the initial value of an IO signal and then subscribe to changes
        
        Args:
            signal_path: Signal path
            callback: Function to call when events are received
            
        Returns:
            Tuple of (initial value, subscription ID)
        """
        # Check if we have access to the robot object
        try:
            from .abb_robot import ABBRobot, ABBEndpoints
            if hasattr(self.api, 'robot') and isinstance(self.api.robot, ABBRobot):
                # Use the IO class directly if available
                return self.api.robot.io.get_signal_value_and_subscribe(signal_path, callback)
            else:
                # Fallback to direct processing
                processor = IOSignalProcessor(self.logger)
                signal_path = processor.normalize_signal_path(signal_path)
                self.logger.debug(f"Getting initial value for signal {signal_path}")
                
                # Format endpoint using SIGNALS_VALUE
                formatted_endpoint = ABBEndpoints.SIGNALS_VALUE.format(signal_path=signal_path.lstrip('/rw/iosystem/'))
                initial_value = self.api.get(formatted_endpoint)
        except (ImportError, AttributeError):
            # Fallback to direct processing if robot or IO class is not available
            processor = IOSignalProcessor(self.logger)
            signal_path = processor.normalize_signal_path(signal_path)
            self.logger.debug(f"Getting initial value for signal {signal_path}")
            initial_value = self.api.get(signal_path)
        
        # Create resources dictionary for subscription
        resources = {signal_path: {'p': '1'}}
        
        # Create subscription
        subscription_id = self.api.subscribe(resources, callback)
        
        if subscription_id:
            self.logger.info(f"Created subscription to signal {signal_path}")
        else:
            self.logger.error(f"Failed to create subscription to signal {signal_path}")
            
        return initial_value, subscription_id
    
    def get_motion_state_and_subscribe(self, 
                                     callback: Optional[Callable] = None) -> Tuple[Dict[str, Any], str]:
        """
        Get the initial motion system state and then subscribe to changes
        
        Args:
            callback: Function to call when events are received
            
        Returns:
            Tuple of (initial state, subscription ID)
        """
        from .abb_robot import ABBEndpoints
        
        # Get initial values
        error_state = self.api.get(ABBEndpoints.MOTION_ERRORSTATE)
        nonexecution = self.api.get(ABBEndpoints.MOTION_NONEXECUTION)
        
        initial_state = {
            'error_state': error_state.get('content', {}),
            'nonexecution': nonexecution.get('content', {})
        }
        
        # Resources to monitor
        resources = {
            ABBEndpoints.MOTION_ERRORSTATE: {'p': '1'},
            ABBEndpoints.MOTION_NONEXECUTION: {'p': '1'}
        }
        
        subscription_id = self.api.subscribe(resources, callback)
        
        return initial_state, subscription_id
    
    def get_rapid_execution_state_and_subscribe(self, 
                                              callback: Optional[Callable] = None) -> Tuple[Dict[str, Any], str]:
        """
        Get the initial RAPID execution state and then subscribe to changes
        
        Args:
            callback: Function to call when execution state changes
            
        Returns:
            Tuple of (initial execution state, subscription ID)
        """
        from .abb_robot import ABBEndpoints
        
        # Get initial execution state
        initial_state = self.api.get(ABBEndpoints.RAPID_EXECUTION)
        
        # Create subscription
        resources = {
            f'{ABBEndpoints.RAPID_BASE}/execution;ctrlexecstate': "1"
        }
        subscription_id = self.api.subscribe(resources, callback)
        
        return initial_state, subscription_id
    
    def get_panel_state_and_subscribe(self, 
                                    resources: Optional[Dict[str, Any]] = None, 
                                    callback: Optional[Callable] = None) -> Tuple[Dict[str, Any], str]:
        """
        Get the initial panel state and then subscribe to panel events
        
        Args:
            resources: Dictionary of panel resources to subscribe to
            callback: Function to call when events are received
            
        Returns:
            Tuple of (initial panel state, subscription ID)
        """
        from .abb_robot import ABBEndpoints
        
        if resources is None:
            # Default resources to monitor common panel events
            resources = {
                ABBEndpoints.CTRL_STATE: "1",
                ABBEndpoints.OPMODE: "1",
                ABBEndpoints.SPEED_RATIO: "1"
            }
        
        # Get initial values
        initial_state = {}
        for resource in resources.keys():
            try:
                value = self.api.get(resource)
                initial_state[resource] = value.get('content', {})
            except Exception as e:
                self.logger.error(f"Error getting initial value for {resource}: {e}")
        
        # Create subscription
        subscription_id = self.api.subscribe(resources, callback)
        
        return initial_state, subscription_id
    
    def get_vision_state_and_subscribe(self,
                                     callback: Optional[Callable] = None) -> Tuple[Dict[str, Any], str]:
        """
        Get the initial vision system state and then subscribe to changes
        
        Args:
            callback: Function to call when events are received
            
        Returns:
            Tuple of (initial vision state, subscription ID)
        """
        from .abb_robot import ABBEndpoints
        
        # Get initial vision info
        initial_state = self.api.get(ABBEndpoints.VISION_BASE)
        
        # Create subscription
        resources = {
            f'{ABBEndpoints.VISION_BASE}': {'p': '1'}
        }
        subscription_id = self.api.subscribe(resources, callback)
        
        return initial_state, subscription_id 