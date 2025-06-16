"""
ABB Robot Web Services (RWS) Base API Library

A comprehensive library for interacting with ABB robot controllers via their REST API
and WebSocket interfaces. This library provides standardized methods for:
- Authentication and session management
- HTTP GET/POST requests to the robot controller
- WebSocket subscriptions for real-time event monitoring

Author: Sunny24
Date: May 21, 2025
"""

import logging
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import xml.etree.ElementTree as ET
from ws4py.client.threadedclient import WebSocketClient
import time
from threading import Event, Thread
from typing import Dict, Optional, Any, List, Callable, Union

# Disable SSL certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define XML namespace used in ABB responses
NAMESPACE = '{http://www.w3.org/1999/xhtml}'

class ABBRobotAPI:
    """Main class for interacting with ABB Robot Web Services"""
    
    def __init__(self, host: str = 'localhost:80', 
                username: str = 'Default User', 
                password: str = 'robotics', 
                protocol: str = 'https://', 
                debug: bool = False):
        """
        Initialize the ABB Robot API client
        
        Args:
            host: The hostname/IP and port of the robot controller
            username: The username for authentication
            password: The password for authentication
            protocol: The protocol to use (http:// or https://)
            debug: Enable debug logging
        """
        self.host = host
        self.username = username
        self.password = password
        self.protocol = protocol
        self.base_url = f"{protocol}{host}"
        self.basic_auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.cookies = None
        self.active_subscriptions = {}
        
        # Set up logging
        self.logger = logging.getLogger('ABBRobotAPI')
        if debug:
            self._setup_debug_logging()
    
    def _setup_debug_logging(self) -> None:
        """Configure detailed debug logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
        
        # Enable requests/urllib3 logging
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.addHandler(handler)
        requests_log.propagate = True
    
    def connect(self) -> bool:
        """
        Establish a connection to the robot controller
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            headers = {'Accept': 'application/hal+json;v=2.0'}
            self.logger.info(f"Connecting to {self.base_url}")
            
            response = self.session.get(
                self.base_url, 
                auth=self.basic_auth, 
                headers=headers, 
                verify=False,
                timeout=10  # Add timeout for connection
            )
            
            if response.status_code == 200:
                self.logger.info(f"Connected successfully to {self.host}")
                self.cookies = response.cookies
                return True
            else:
                self.logger.error(f"Connection failed. Status code: {response.status_code}")
                return False
                
        except requests.ConnectionError as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False
        except requests.Timeout as e:
            self.logger.error(f"Connection timeout: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during connection: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Close the session and all active subscriptions"""
        try:
            # Close all active subscriptions
            for subscription_id, subscription in list(self.active_subscriptions.items()):
                self.unsubscribe(subscription_id)
            
            # Close the session
            self.session.close()
            self.logger.info("Disconnected from robot controller")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {str(e)}")
    
    def get(self, uri: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a GET request to the robot controller
        
        Args:
            uri: The URI to request (e.g., "/rw/panel/ctrl-state")
            headers: Additional headers to include
            params: Query parameters to include in the URL
            
        Returns:
            Response object with status_code, headers, content, etc.
        """
        if headers is None:
            headers = {}
        
        default_headers = {'Accept': 'application/hal+json;v=2.0'}
        headers = {**default_headers, **headers}
        
        url = f"{self.base_url}{uri}"
        self.logger.info(f"GET request to {url}")
        
        try:
            response = self.session.get(
                url, 
                headers=headers,
                params=params,
                verify=False,
                timeout=30  # Add reasonable timeout
            )
            
            return self._process_response(response)
            
        except requests.Timeout as e:
            self.logger.error(f"GET request timeout: {str(e)}")
            return {'status_code': 408, 'error': f"Request timeout: {str(e)}"}
        except requests.ConnectionError as e:
            self.logger.error(f"GET connection error: {str(e)}")
            return {'status_code': 503, 'error': f"Connection error: {str(e)}"}
        except Exception as e:
            self.logger.error(f"GET request error: {str(e)}")
            return {'status_code': 0, 'error': str(e)}
    
    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Process HTTP response and format it consistently
        
        Args:
            response: The HTTP response object
            
        Returns:
            Formatted response dictionary
        """
        result = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'elapsed': response.elapsed.total_seconds()
        }
        
        # Process response content based on content type
        content_type = response.headers.get('Content-Type', '')
        
        # Try to handle 406 Not Acceptable error
        if response.status_code == 406:
            self.logger.warning("406 Not Acceptable, retrying with XML Accept header.")
            modified_headers = dict(response.request.headers)
            modified_headers['Accept'] = 'application/xml'
            
            new_response = self.session.get(
                response.url, 
                headers=modified_headers, 
                verify=False,
                timeout=30
            )
            
            return self._process_response(new_response)
            
        # Process based on content type
        if 'application/json' in content_type or 'application/hal+json' in content_type:
            try:
                result['content'] = response.json()
            except ValueError:
                result['content'] = response.text
                self.logger.warning(f"Failed to parse JSON response: {response.text[:200]}")
        elif 'application/xml' in content_type or 'text/xml' in content_type:
            result['content'] = response.text
            try:
                result['xml'] = ET.fromstring(response.text)
            except ET.ParseError:
                self.logger.warning(f"Failed to parse XML response: {response.text[:200]}")
        else:
            result['content'] = response.text

        if response.status_code >= 400:
            self.logger.error(f"Request failed. Status: {response.status_code}, Response: {response.text[:500]}")
        else:
            self.logger.debug(f"Response: Status={response.status_code}, Time={result['elapsed']}s")
            
        return result
    
    def post(self, uri: str, data: Optional[Dict[str, Any]] = None, 
             headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send a POST request to the robot controller
        
        Args:
            uri: The URI to request
            data: The data to send
            headers: Additional headers to include
            
        Returns:
            Response object with status_code, headers, content, etc.
        """
        if headers is None:
            headers = {}
        if data is None:
            data = {}
            
        # Default headers for ABB Robot Web Services
        default_headers = {
            'Accept': 'application/hal+json;v=2.0',
            'Content-Type': 'application/x-www-form-urlencoded;v=2.0'
        }
        headers = {**default_headers, **headers}
        
        url = f"{self.base_url}{uri}"
        self.logger.info(f"POST request to {url}")
        
        try:
            response = self.session.post(
                url, 
                data=data, 
                headers=headers, 
                verify=False,
                timeout=30
            )
            
            return self._process_response(response)
            
        except requests.Timeout as e:
            self.logger.error(f"POST request timeout: {str(e)}")
            return {'status_code': 408, 'error': str(e)}
        except requests.ConnectionError as e:
            self.logger.error(f"POST connection error: {str(e)}")
            return {'status_code': 503, 'error': str(e)}
        except Exception as e:
            self.logger.error(f"POST request error: {str(e)}")
            return {'status_code': 0, 'error': str(e)}
    
    def subscribe(self, resources, callback=None):
        """
        Subscribe to robot controller events
        
        Args:
            resources (dict): A dictionary of resources to subscribe to
                Example: {
                    '/rw/panel/ctrl-state': {'p': '1'},
                    '/rw/panel/opmode': {'p': '1'},
                    '/rw/panel/speedratio': {'p': '1'}
                }
            callback (callable): Function to call when events are received
                Function signature: callback(event_data, resource_path)
                
        Returns:
            str: Subscription ID if successful, None otherwise
        """
        if not self.cookies:
            if not self.connect():
                return None
                
        # Validate resource paths
        valid_resources = {}
        for resource_path, options in resources.items():
            # Check if resource path is valid
            if not resource_path.startswith('/'):
                self.logger.warning(f"Resource path doesn't start with '/': {resource_path}. Adding prefix.")
                resource_path = f"/{resource_path}"
                
            # Check if resource path starts with /rw/
            if not resource_path.startswith('/rw/'):
                self.logger.warning(f"Resource path doesn't start with '/rw/': {resource_path}")
                # We won't modify this since it might be intentional in some cases
            
            valid_resources[resource_path] = options
        
        # Format the resources for the subscription request
        data = {'resources': [str(i) for i in range(1, len(valid_resources)+1)]}
        
        # Log the resource key mapping
        self.logger.debug("Resource mapping:")
        index = 1
        for resource_path, options in valid_resources.items():
            data[f'{index}'] = resource_path
            self.logger.debug(f"  {index} -> {resource_path}")
            for option_key, option_value in options.items():
                data[f'{index}-{option_key}'] = option_value
                self.logger.debug(f"  {index}-{option_key} -> {option_value}")
            index += 1
        
        self.logger.debug(f"Subscription data: {data}")
        
        # Create the subscription
        response = self.post('/subscription', data=data)
        
        if response['status_code'] != 201:
            self.logger.error(f"Failed to create subscription. Status: {response['status_code']}")
            self.logger.error(f"Response content: {response.get('content', 'No content')}")
            return None
        
        # Get the WebSocket URL from the Location header
        if 'Location' not in response['headers']:
            self.logger.error("Location header not found in subscription response")
            return None
            
        websocket_url = response['headers']['Location']
        self.logger.debug(f"Websocket URL: {websocket_url}")
        
        # Create the cookie header for the WebSocket
        cookie_header = []
        for cookie_name, cookie_value in self.session.cookies.items():
            cookie_header.append(f"{cookie_name}={cookie_value}")
        cookie_str = "; ".join(cookie_header)
        
        # Create a unique ID for this subscription
        subscription_id = str(time.time())
        
        # Create and start the WebSocket client
        ws_client = RWSWebSocketClient(
            websocket_url, 
            headers=[('Cookie', cookie_str)],
            callback=callback,
            logger=self.logger
        )
        
        # Store the subscription
        self.active_subscriptions[subscription_id] = {
            'client': ws_client,
            'resources': valid_resources,
            'websocket_url': websocket_url
        }
        
        # Start the WebSocket client in a separate thread
        ws_thread = Thread(target=ws_client.start)
        ws_thread.daemon = True
        ws_thread.start()
        
        self.logger.info(f"Subscription {subscription_id} created successfully")
        return subscription_id
    
    def unsubscribe(self, subscription_id):
        """
        Unsubscribe from events
        
        Args:
            subscription_id (str): The ID of the subscription to cancel
            
        Returns:
            bool: True if successful, False otherwise
        """
        if subscription_id not in self.active_subscriptions:
            self.logger.warning(f"Subscription {subscription_id} not found")
            return False
        
        try:
            # Get WebSocket client
            ws_client = self.active_subscriptions[subscription_id]['client']
            
            # Check if WebSocket is still connected
            is_connected = hasattr(ws_client, 'connected') and ws_client.connected.is_set()
            self.logger.debug(f"WebSocket connected state before unsubscribe: {is_connected}")
            
            # Remove from active subscriptions dictionary first
            subscription_info = self.active_subscriptions.pop(subscription_id)
            self.logger.info(f"Removed subscription {subscription_id} from active subscriptions")
            
            # Safely close the WebSocket
            try:
                if hasattr(ws_client, 'close'):
                    # Attempt graceful close with timeout
                    ws_client.close(code=1000, reason="Client requested unsubscribe")
                    self.logger.info(f"WebSocket for subscription {subscription_id} closed gracefully")
                else:
                    self.logger.warning(f"WebSocket client has no close method")
            except Exception as close_error:
                # Continue even if close fails - we've already removed it from our tracking
                self.logger.warning(f"Error closing WebSocket: {str(close_error)}")
                
            # Consider successful if we removed from our dictionary
            self.logger.info(f"Unsubscribed from {subscription_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unsubscribing from {subscription_id}: {str(e)}")
            # Still remove from dict if it exists to prevent memory leaks
            if subscription_id in self.active_subscriptions:
                self.active_subscriptions.pop(subscription_id, None)
                self.logger.info(f"Removed subscription {subscription_id} after error")
            return False
            
    def check_subscription_status(self, subscription_id):
        """
        Check the status of a subscription
        
        Args:
            subscription_id (str): The ID of the subscription to check
            
        Returns:
            dict: Status information about the subscription
        """
        if subscription_id not in self.active_subscriptions:
            return {
                'exists': False,
                'error': 'Subscription not found'
            }
            
        subscription = self.active_subscriptions[subscription_id]
        ws_client = subscription['client']
        
        is_connected = hasattr(ws_client, 'connected') and ws_client.connected.is_set()
        
        return {
            'exists': True,
            'connected': is_connected,
            'resources': subscription['resources'],
            'websocket_url': subscription['websocket_url'],
            'error_count': getattr(ws_client, 'error_count', 0)
        }
        
    def list_active_subscriptions(self):
        """
        List all active subscriptions
        
        Returns:
            dict: Dictionary of subscription IDs and their status
        """
        result = {}
        for sub_id in self.active_subscriptions:
            result[sub_id] = self.check_subscription_status(sub_id)
        return result
        
    def ping_subscription(self, subscription_id):
        """
        Ping a subscription to check if it's still alive
        
        Args:
            subscription_id (str): The ID of the subscription to check
            
        Returns:
            bool: True if subscription is active, False otherwise
        """
        status = self.check_subscription_status(subscription_id)
        if not status['exists'] or not status['connected']:
            self.logger.warning(f"Subscription {subscription_id} is not active")
            return False
            
        self.logger.info(f"Subscription {subscription_id} is active")
        return True

    # Utility methods for parsing event data
    def parse_event_xml(self, xml_str):
        """
        Parse event XML data
        
        Args:
            xml_str (str): XML string to parse
            
        Returns:
            dict: Parsed event data
        """
        try:
            root = ET.fromstring(xml_str)
            result = {}
            
            # Find all li elements with class starting with 'pnl-'
            for li in root.findall(f".//{NAMESPACE}li"):
                class_name = li.attrib.get('class', '')
                
                if class_name.startswith('pnl-') and class_name.endswith('-ev'):
                    # Example: pnl-ctrlstate-ev -> controller_state
                    middle = class_name[len('pnl-'):-len('-ev')]
                    key = middle.replace('ctrlstate', 'controller_state').replace('opmode', 'operation_mode').replace('speedratio', 'speed_ratio')
                    
                    # Find child span to get value
                    span = li.find(f"./{NAMESPACE}span")
                    if span is not None:
                        result[key] = span.text

            return result
        except Exception as e:
            self.logger.error(f"Error parsing event XML: {str(e)}")
            return {}


class RWSWebSocketClient(WebSocketClient):
    """WebSocket client for ABB Robot Web Services subscriptions"""
    
    def __init__(self, url, headers=None, callback=None, logger=None):
        """
        Initialize the WebSocket client
        
        Args:
            url (str): The WebSocket URL
            headers (list): List of header tuples (name, value)
            callback (callable): Function to call when events are received
            logger (Logger): Logger instance
        """
        super().__init__(url, protocols=['rws_subscription'], headers=headers)
        self.callback = callback
        self.logger = logger or logging.getLogger('RWSWebSocketClient')
        self.connected = Event()
        self.closing = False
        self.error_count = 0
        self.max_errors = 3
        self.logger.debug(f"WebSocket client initialized with URL: {url}")
        
        # Log headers for debugging without sensitive info
        debug_headers = []
        for key, value in (headers or []):
            if key.lower() == 'cookie':
                debug_headers.append((key, "***REDACTED***"))
            else:
                debug_headers.append((key, value))
        self.logger.debug(f"WebSocket headers: {debug_headers}")
    
    def opened(self):
        """Called when the WebSocket connection is established"""
        self.logger.info(f"WebSocket connection established: {self.url}")
        self.error_count = 0
        self.connected.set()
        self.closing = False
    
    def closed(self, code, reason=None):
        """Called when the WebSocket connection is closed"""
        self.connected.clear()
        
        # Check if this was a clean close
        if self.closing:
            self.logger.info(f"WebSocket connection closed cleanly: code={code}, reason={reason}")
        else:
            self.logger.warning(f"WebSocket connection closed unexpectedly: code={code}, reason={reason}")
        
        # Reset state
        self.closing = False
    
    def close(self, code=1000, reason="Client initiated close"):
        """
        Safely close the WebSocket connection
        
        Args:
            code (int): WebSocket close code
            reason (str): Reason for closing
        """
        if self.connected.is_set():
            self.logger.info(f"Closing WebSocket connection: {reason}")
            self.closing = True
            try:
                super().close(code=code, reason=reason)
                self.logger.debug("WebSocket close method completed")
            except Exception as e:
                self.logger.error(f"Error in WebSocket close: {str(e)}")
        else:
            self.logger.info("WebSocket close called but connection not active")
    
    def received_message(self, message):
        """Called when a message is received from the WebSocket"""
        if message.is_text:
            event_data = message.data.decode("utf-8")
            self.logger.debug(f"WebSocket event received: {event_data[:200]}...")
            
            if self.callback:
                try:
                    self.callback(event_data)
                except Exception as e:
                    self.logger.error(f"Error in WebSocket callback: {str(e)}")
                    self.error_count += 1
                    if self.error_count > self.max_errors:
                        self.logger.warning(f"Too many callback errors ({self.error_count}), closing connection")
                        self.close(code=1011, reason="Too many callback errors")
        else:
            self.logger.warning(f"Received non-text message type: {type(message)}")
    
    def start(self):
        """Start the WebSocket client"""
        try:
            self.logger.info("Starting WebSocket client...")
            self.connect()
            self.logger.debug("WebSocket connect() called, waiting for connection...")
            
            # Wait for connection with timeout
            if not self.connected.wait(timeout=10):  # Increased timeout to 10 seconds
                self.logger.error("WebSocket connection timed out after 10 seconds")
                return
                
            self.logger.info("WebSocket connected successfully, running event loop")
            self.run_forever()
            self.logger.info("WebSocket run_forever() completed")
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {str(e)}")
            # Try to clean up
            try:
                if self.connected.is_set():
                    self.close(code=1001, reason="Connection error")
            except:
                pass
