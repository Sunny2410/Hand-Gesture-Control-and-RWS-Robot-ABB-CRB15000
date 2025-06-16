import socket
import threading
from collections import deque
from datetime import datetime
import json
import time
import sys
import math
from PyQt5.QtCore import QThread, pyqtSignal
import traceback
import struct
import logging
class DataSyncServer:
    def __init__(self, L1=0.3, L2=0.25):
        self._buffers = {
            3000: deque(maxlen=1000),
            5000: deque(maxlen=1000)
        }
        self._lock = threading.Lock()
        self._running = False
        self._connections = []
        self.sync_threshold = 0.01  # 10 ms
        self.L1 = L1  # Chiều dài tay trên (m) dọc trục X
        self.L2 = L2  # Chiều dài cẳng tay (m) dọc trục X
        self.logger = self._setup_logger()
        self.last_print_time = time.time()
        self.print_interval = 0.5  # Giới hạn in 2 lần/giây

    @staticmethod
    def _setup_logger():
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def start_server(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(2)
            try:
                s.bind(('0.0.0.0', port))
                s.listen()
                self.logger.info(f"Server started on port {port}")
                while self._running:
                    try:
                        conn, addr = s.accept()
                        with self._lock:
                            self._connections.append(conn)
                        threading.Thread(
                            target=self._handle_client,
                            args=(conn, port),
                            daemon=True
                        ).start()
                    except socket.timeout:
                        continue
            except Exception as e:
                self.logger.error(f"Port {port} error: {str(e)}")
                return

    def _handle_client(self, conn, port):
        data_buffer = b''
        try:
            while self._running:
                data = conn.recv(1024)
                if not data:
                    break
                data_buffer += data
                self._process_buffer(data_buffer, port)
        except (ConnectionResetError, BrokenPipeError):
            self.logger.warning("Client connection reset")
        finally:
            self._cleanup_connection(conn)

    def _process_buffer(self, data_buffer, port):
        while b'\n' in data_buffer:
            line, data_buffer = data_buffer.split(b'\n', 1)
            if line:
                self._process_line(line, port)

    def _process_line(self, line, port):
        try:
            packet = json.loads(line.decode().strip())
            if self._validate_packet(packet):
                timestamp = self._parse_timestamp(packet.get('timestamp'))
                with self._lock:
                    self._buffers[port].append({
                        'timestamp': timestamp,
                        'data': packet,
                        'port': port
                    })
        except json.JSONDecodeError:
            self.logger.debug("Invalid JSON format")
        except ValueError as e:
            self.logger.debug(f"Invalid timestamp: {str(e)}")

    def _validate_packet(self, packet):
        required_keys = {'pitch', 'roll', 'yaw', 'sequence', 'timestamp'}
        return required_keys.issubset(packet.keys())

    def _parse_timestamp(self, ts_str):
        for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
            try:
                # Thêm ngày hiện tại để so sánh chính xác
                now = datetime.now()
                dt = datetime.strptime(ts_str, fmt)
                return dt.replace(year=now.year, month=now.month, day=now.day)
            except ValueError:
                continue
        raise ValueError("Invalid timestamp format")

    def _sync_data(self):
        while self._running:
            with self._lock:
                buf1 = deque(self._buffers[3000])
                buf2 = deque(self._buffers[5000])

            synced_pairs = []
            
            while buf1 and buf2:
                item1 = buf1[0]
                item2 = buf2[0]
                delta = abs((item1['timestamp'] - item2['timestamp']).total_seconds())
                
                if delta <= self.sync_threshold:
                    synced_pairs.append((item1, item2))
                    buf1.popleft()
                    buf2.popleft()
                elif item1['timestamp'] < item2['timestamp']:
                    buf1.popleft()
                else:
                    buf2.popleft()
            
            # Xử lý tất cả các cặp đồng bộ
            for item1, item2 in synced_pairs:
                self._print_synced_data(item1, item2)
                
            time.sleep(0.05)

    def _print_synced_data(self, item1, item2):
        try:
            current_time = time.time()
            if current_time - self.last_print_time < self.print_interval:
                return
                
            self.last_print_time = current_time
            ts = item1['timestamp'].strftime("%H:%M:%S.%f")[:-3]
            sep = "+" + "-"*20 + "+" + "-"*20 + "+"
            
            print(f"\n{sep}\n| {'Timestamp':^38} |\n{sep}")
            print(f"| {ts:^38} |")
            print(sep)
            print(f"| {'Port 3000':^18} | {'Port 5000':^18} |")
            print(sep)
            self._print_row("Roll", item1['data']['roll'], item2['data']['roll'])
            self._print_row("Pitch", item1['data']['pitch'], item2['data']['pitch'])
            self._print_row("Yaw", item1['data']['yaw'], item2['data']['yaw'])
            print(sep)

            # Tính toán tọa độ cổ tay với hệ trục mới
            wrist_pos = self._calculate_wrist_position(
                np.radians(float(item1['data']['roll'])),
                np.radians(float(item1['data']['pitch'])),
                np.radians(float(item1['data']['yaw'])),
                np.radians(float(item2['data']['roll'])),
                np.radians(float(item2['data']['pitch'])),
                np.radians(float(item2['data']['yaw']))
            )
            
            # Hiển thị tọa độ theo hệ trục mới
            print(f"| {'Wrist Position (mm)':^38} |")
            print(sep)
            print(f"| X (dọc tay): {wrist_pos[0]*1000:>8.3f} |")
            print(f"| Y (ngang):   {wrist_pos[1]*1000:>8.3f} |")
            print(f"| Z (cao):     {wrist_pos[2]*1000:>8.3f} |")
            print(sep)

        except KeyError as e:
            self.logger.error(f"Missing key in data: {str(e)}")
        except Exception as e:
            self.logger.error(f"Calculation error: {str(e)}")

    @staticmethod
    def _print_row(label, v1, v2):
        print(f"| {label:<6} {float(v1):>10.2f}° | {label:<6} {float(v2):>10.2f}° |")

    def _euler_to_rotation_matrix(self, roll, pitch, yaw):
        """Ma trận quay chính xác cho hệ trục mới"""
        # Tạo ma trận quay riêng lẻ
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])
        
        Ry = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])
        
        Rz = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])
        
        # Kết hợp theo thứ tự ZYX (yaw, pitch, roll)
        return Rz @ Ry @ Rx

    def _calculate_wrist_position(self, imu1_roll, imu1_pitch, imu1_yaw,
                                 imu2_roll, imu2_pitch, imu2_yaw):
        """Tính toán tọa độ với hệ trục mới và quy tắc cộng vector"""
        # Vector chiều dài dọc trục X mới (dọc tay)
        vec_shoulder = np.array([self.L1, 0, 0])
        vec_forearm = np.array([self.L2, 0, 0])

        # Ma trận quay
        R_shoulder = self._euler_to_rotation_matrix(imu1_roll, imu1_pitch, imu1_yaw)
        R_forearm = self._euler_to_rotation_matrix(imu2_roll, imu2_pitch, imu2_yaw)

        # Tính toán vị trí: vị trí khuỷu tay + vị trí cổ tay so với khuỷu tay
        elbow_pos = R_shoulder @ vec_shoulder
        wrist_pos_rel = R_forearm @ vec_forearm
        
        wrist_pos = elbow_pos + wrist_pos_rel
        return wrist_pos.round(6)

    def start(self):
        self._running = True
        threading.Thread(target=self._sync_data, daemon=True).start()
        
        ports = (3000, 5000)
        for port in ports:
            threading.Thread(
                target=self.start_server,
                args=(port,),
                daemon=True
            ).start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        self._running = False
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    self.logger.error(f"Error closing connection: {str(e)}")
            self._connections.clear()
        self.logger.info("Server shutdown gracefully")
        sys.exit(0)

    def _cleanup_connection(self, conn):
        with self._lock:
            if conn in self._connections:
                try:
                    conn.close()
                    self._connections.remove(conn)
                except ValueError:
                    pass



import math # Đã có từ trước, cần cho radians
import numpy as np # Thêm thư viện numpy

# (Các import khác nếu có từ code gốc của bạn như 'struct' nên được giữ lại)
# import struct # Nếu bạn vẫn cần xử lý binary không phải JSON

class ESP32Socket(QThread):
    """Socket server to receive wrist data from two ESP32 devices"""
    
    # Signal to emit when wrist position data is received
    wrist_data_received = pyqtSignal(dict)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)
    debug_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.sockets = []
        self.local_port1 = 8080
        self.local_port2 = 8081
        self.receive_timeout = 1.0
        self.debug_mode = False  # Control debug message verbosity
        
        # Physical arm parameters (đơn vị mm theo set_arm_parameters)
        self.L1 = 300.0  # Upper arm length (mm)
        self.L2 = 250.0  # Forearm length (mm)
        
        # Data buffers for each port
        self.buffers = {
            self.local_port1: deque(maxlen=100),
            self.local_port2: deque(maxlen=100)
        }
        
        # Latest wrist position data
        self.wrist_position = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "rx": 0.0,
            "ry": 0.0,
            "rz": 0.0
        }
        
        # Data from each ESP32 - Thêm yaw
        self.upperarm_data = {
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0  # Thêm yaw
        }
        
        self.forearm_data = {
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0  # Thêm yaw
        }
        
        # Calibration and scaling
        self.calibration_values = {
            "x_offset": 0.0, "y_offset": 0.0, "z_offset": 0.0,
            "rx_offset": 0.0, "ry_offset": 0.0, "rz_offset": 0.0
        }
        
        self.scaling_factors = {
            "x_scale": 1.0, "y_scale": 1.0, "z_scale": 1.0,
            "rx_scale": 0.1, "ry_scale": 0.1, "rz_scale": 0.1 # Giữ nguyên scale cho rx, ry, rz
        }
        
        # Connection status
        self.connected = False
        self.connections = []
        self.lock = threading.Lock()
        self.last_data_time = time.time()
        self.data_timeout = 1.0  # Seconds before considering connection lost
        
        self.fallback_timer = None # Giữ nguyên
    
    def configure_dual_ports(self, unused_ip=None, local_port1=8080, local_port2=8081):
        """Configure the ESP32 socket server with two local ports"""
        self.local_port1 = local_port1
        self.local_port2 = local_port2
        
        self.buffers = {
            self.local_port1: deque(maxlen=100),
            self.local_port2: deque(maxlen=100)
        }
        
        self.status_update.emit(f"ESP32 socket configured to listen on ports {self.local_port1} and {self.local_port2}")
        if self.debug_mode:
            self.debug_update.emit(f"ESP32 socket configured to listen on ports {self.local_port1} and {self.local_port2}")
    
    def set_debug_mode(self, enabled=False):
        self.debug_mode = enabled
        self.status_update.emit(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def calibrate(self, position_data):
        self.calibration_values = {
            "x_offset": position_data["x"], "y_offset": position_data["y"], "z_offset": position_data["z"],
            "rx_offset": position_data["rx"], "ry_offset": position_data["ry"], "rz_offset": position_data["rz"]
        }
        self.status_update.emit(f"Calibration set: {self.calibration_values}")
        
    def set_scaling(self, scaling_factors):
        self.scaling_factors.update(scaling_factors)
        self.status_update.emit(f"Scaling factors updated: {self.scaling_factors}")
    
    def set_calibration(self, calibration_values):
        self.calibration_values.update(calibration_values)
        self.status_update.emit(f"Calibration values updated: {self.calibration_values}")
    
    def set_arm_parameters(self, l1=None, l2=None):
        """Set arm length parameters in mm"""
        if l1 is not None:
            self.L1 = float(l1)
        if l2 is not None:
            self.L2 = float(l2)
        self.status_update.emit(f"Arm parameters updated: L1={self.L1}mm, L2={self.L2}mm")
    
    def get_current_position(self):
        return self.wrist_position.copy()

    def send_zero_position(self):
        zero_position = {
            "x": self.calibration_values["x_offset"] * self.scaling_factors["x_scale"],
            "y": self.calibration_values["y_offset"] * self.scaling_factors["y_scale"],
            "z": self.calibration_values["z_offset"] * self.scaling_factors["z_scale"],
            "rx": self.calibration_values["rx_offset"] * self.scaling_factors["rx_scale"],
            "ry": self.calibration_values["ry_offset"] * self.scaling_factors["ry_scale"],
            "rz": self.calibration_values["rz_offset"] * self.scaling_factors["rz_scale"],
            "device_id": 0 
        }
        self.wrist_position = zero_position
        self.wrist_data_received.emit(self.wrist_position)
    
    def check_connection_status(self):
        current_time = time.time()
        if len(self.connections) == 0 or (current_time - self.last_data_time) > self.data_timeout:
            if self.connected: # Chỉ emit nếu trạng thái thay đổi
                self.status_update.emit("ESP32 connection lost. Sending zero position.")
            self.connected = False
            self.send_zero_position()
        elif not self.connected and len(self.connections) > 0:
             self.connected = True # Cập nhật lại khi có dữ liệu
             self.status_update.emit("ESP32 reconnected.")


    def run(self):
        self.running = True
        self.status_update.emit("ESP32 socket server started")
        self.start_servers()
        self.last_data_time = time.time()
        
        while self.running:
            self.check_connection_status()
            time.sleep(0.1)
            
        self.close_all_sockets()
        self.running = False
        self.connected = False
        self.status_update.emit("ESP32 communication stopped")
    
    def start_servers(self):
        for port in [self.local_port1, self.local_port2]:
            threading.Thread(target=self.start_server, args=(port,), daemon=True).start()
    
    def start_server(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(2.0) # Giữ timeout cho accept
            
            try:
                s.bind(('0.0.0.0', port))
                s.listen()
                self.status_update.emit(f"Listening for ESP32 data on port {port}")
                with self.lock:
                    self.sockets.append(s)
                
                while self.running:
                    try:
                        conn, addr = s.accept()
                        with self.lock:
                            self.connections.append(conn)
                        self.status_update.emit(f"ESP32 connected to port {port} from {addr[0]}:{addr[1]}")
                        self.connected = True
                        self.last_data_time = time.time()
                        
                        threading.Thread(target=self.handle_client, args=(conn, port), daemon=True).start()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            self.error.emit(f"Socket accept error on port {port}: {str(e)}")
                        break
            except Exception as e:
                self.error.emit(f"Failed to bind to port {port}: {str(e)}")
                return
        except Exception as e:
            self.error.emit(f"Error creating socket for port {port}: {str(e)}")

    def handle_client(self, conn, port):
        data_buffer = b''
        device_id = 1 if port == self.local_port1 else 2
        
        try:
            conn.settimeout(self.receive_timeout) # Timeout cho conn.recv
            while self.running:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break 
                    
                    data_buffer += data
                    self.last_data_time = time.time() # Cập nhật khi nhận được bất kỳ byte nào
                    if not self.connected : # Nếu trước đó disconnected, cập nhật lại
                        self.connected = True
                        self.status_update.emit(f"ESP32 data resumed on port {port}.")

                    while b'\n' in data_buffer:
                        line, data_buffer = data_buffer.split(b'\n', 1)
                        if not line:
                            continue
                        
                        try:
                            packet_str = line.decode().strip()
                            if not packet_str: continue # Bỏ qua dòng trống sau khi strip
                            packet = json.loads(packet_str)
                            self.process_data(packet, device_id)
                        # Bỏ qua phần xử lý binary nếu bạn chỉ dùng JSON từ ESP32 gửi lên roll, pitch, yaw
                        # except json.JSONDecodeError:
                        #     # ... (phần xử lý binary của bạn nếu có)
                        except Exception as e:
                            if self.debug_mode:
                                self.debug_update.emit(f"Error processing JSON data from ESP32 on port {port}: {str(e)}. Line: '{line.decode().strip()}'")
                except socket.timeout: # Timeout khi chờ recv
                    if self.debug_mode:
                        self.debug_update.emit(f"Socket recv timeout on port {port}. Checking connection.")
                    # Không break ngay, vòng lặp ngoài check_connection_status sẽ xử lý
                    # Nếu muốn ngắt kết nối client này ngay lập tức khi timeout thì break ở đây
                    # self.check_connection_status() # Có thể gọi check ở đây nếu muốn phản ứng nhanh hơn
                    continue # Tiếp tục chờ dữ liệu mới
                except ConnectionResetError:
                    self.status_update.emit(f"ESP32 on port {port} reset connection.")
                    break # Thoát vòng lặp client
                except Exception as e: # Các lỗi khác của recv
                    if self.running:
                        self.error.emit(f"Error receiving data on port {port}: {str(e)}")
                    break # Thoát vòng lặp client
        finally:
            conn.close()
            with self.lock:
                if conn in self.connections:
                    self.connections.remove(conn)
            # Không set self.connected = False ở đây, vì có thể client kia vẫn kết nối.
            # self.check_connection_status() sẽ cập nhật đúng.
            self.status_update.emit(f"ESP32 client on port {port} handler finished.")


    def process_data(self, packet, device_id):
        try:
            if self.debug_mode:
                self.debug_update.emit(f"Processing data from device {device_id}: {packet}")
            
            with self.lock:
                timestamp_str = packet.get('timestamp')
                timestamp = self.parse_timestamp(timestamp_str) if timestamp_str else datetime.now()
                
                buffer_key = self.local_port1 if device_id == 1 else self.local_port2
                self.buffers[buffer_key].append({
                    'timestamp': timestamp, 'data': packet, 'device_id': device_id
                })
            
            # Kiểm tra packet có roll, pitch, và yaw
            if all(k in packet for k in ['roll', 'pitch', 'yaw']):
                if self.debug_mode:
                    self.debug_update.emit(f"Processing roll/pitch/yaw data from device {device_id}")
                
                current_data = {
                    'roll': float(packet['roll']),
                    'pitch': float(packet['pitch']),
                    'yaw': float(packet['yaw'])
                }

                if device_id == 1:
                    self.upperarm_data = current_data
                    if self.debug_mode:
                        self.debug_update.emit(f"Updated upper arm data: {self.upperarm_data}")
                else: # device_id == 2
                    self.forearm_data = current_data
                    if self.debug_mode:
                        self.debug_update.emit(f"Updated forearm data: {self.forearm_data}")
                
                # Nếu có đủ dữ liệu từ cả hai thiết bị, tính toán vị trí cổ tay
                # Kiểm tra xem self.upperarm_data và self.forearm_data đã được cập nhật ít nhất một lần chưa
                # bằng cách kiểm tra một key bất kỳ không phải giá trị mặc định (ví dụ timestamp nếu có)
                # Hoặc đơn giản là check xem chúng có phải là dict rỗng không nếu bạn khởi tạo chúng là {}
                # Ở đây, chúng được khởi tạo với giá trị, nên chỉ cần gọi tính toán
                if self.upperarm_data and self.forearm_data: # Đảm bảo cả hai đã có dữ liệu
                    try:
                        wrist_pos_xyz = self.calculate_wrist_position(self.upperarm_data, self.forearm_data)
                        
                        raw_position = {
                            "x": wrist_pos_xyz[0],
                            "y": wrist_pos_xyz[1],
                            "z": wrist_pos_xyz[2],
                            "rx": 0.0, # Giữ nguyên rx, ry, rz là 0 vì yaw đã dùng cho x,y,z
                            "ry": 0.0,
                            "rz": 0.0,
                            "device_id": device_id # ID của thiết bị cuối cùng gửi dữ liệu kích hoạt tính toán
                        }
                        
                        self.wrist_position = {
                            "x": (raw_position["x"] + self.calibration_values["x_offset"]) * self.scaling_factors["x_scale"],
                            "y": (raw_position["y"] + self.calibration_values["y_offset"]) * self.scaling_factors["y_scale"],
                            "z": (-raw_position["z"] + self.calibration_values["z_offset"]) * self.scaling_factors["z_scale"],
                            "rx": (raw_position["rx"] + self.calibration_values["rx_offset"]) * self.scaling_factors["rx_scale"],
                            "ry": (raw_position["ry"] + self.calibration_values["ry_offset"]) * self.scaling_factors["ry_scale"],
                            "rz": (raw_position["rz"] + self.calibration_values["rz_offset"]) * self.scaling_factors["rz_scale"],
                            "device_id": raw_position["device_id"]
                        }
                        
                        self.wrist_data_received.emit(self.wrist_position)
                    except Exception as e:
                        if self.debug_mode:
                            import traceback
                            self.debug_update.emit(f"Error calculating wrist position with yaw: {str(e)}")
                            self.debug_update.emit(f"Traceback: {traceback.format_exc()}")
            
            # Xử lý legacy cho dữ liệu vị trí trực tiếp (nếu cần)
            elif all(k in packet for k in ["x", "y", "z", "rx", "ry", "rz"]):
                # ... (giữ nguyên phần này nếu bạn vẫn cần) ...
                if self.debug_mode:
                    self.debug_update.emit(f"Processing legacy position data from device {device_id}")
                # (Code xử lý legacy position data của bạn ở đây)
            else:
                if self.debug_mode:
                    self.debug_update.emit(f"Received packet from device {device_id} but missing required r/p/y or x/y/z/rx/ry/rz fields")
                    self.debug_update.emit(f"Packet keys: {list(packet.keys())}")

        except Exception as e:
            if self.debug_mode:
                import traceback
                self.debug_update.emit(f"Error processing ESP32 data packet: {str(e)}")
                self.debug_update.emit(f"Traceback: {traceback.format_exc()}")

    def _euler_to_rotation_matrix(self, roll_rad, pitch_rad, yaw_rad):
        """
        Calculate rotation matrix from Euler angles (roll, pitch, yaw in radians).
        Order of rotation: ZYX (yaw, pitch, roll).
        Assumes roll is rotation around X, pitch around Y, yaw around Z of the new frame.
        """
        cos_r, sin_r = np.cos(roll_rad), np.sin(roll_rad)
        cos_p, sin_p = np.cos(pitch_rad), np.sin(pitch_rad)
        cos_y, sin_y = np.cos(yaw_rad), np.sin(yaw_rad)

        # Rotation matrix for X (roll)
        Rx = np.array([
            [1, 0, 0],
            [0, cos_r, -sin_r],
            [0, sin_r, cos_r]
        ])
        
        # Rotation matrix for Y (pitch)
        Ry = np.array([
            [cos_p, 0, sin_p],
            [0, 1, 0],
            [-sin_p, 0, cos_p]
        ])
        
        # Rotation matrix for Z (yaw)
        Rz = np.array([
            [cos_y, -sin_y, 0],
            [sin_y, cos_y, 0],
            [0, 0, 1]
        ])
        
        # Combined rotation matrix: R = Rz * Ry * Rx
        # This means, to get from world to body: apply Rz, then Ry, then Rx to the vector in body coordinates.
        # Or, to get from body to world: apply Rx_T, then Ry_T, then Rz_T to vector in world coordinates.
        # If the angles define orientation of body frame w.r.t world frame, 
        # then R transforms a vector from body to world.
        return Rz @ Ry @ Rx

    # Bỏ hàm calculate_arm_direction cũ đi hoặc comment lại
    # def calculate_arm_direction(self, roll_deg, pitch_deg): ...

    def calculate_wrist_position(self, upper_arm_orientation, forearm_orientation):
        """
        Calculate wrist position from two sensor orientation data points (roll, pitch, yaw).
        upper_arm_orientation: dict with 'roll', 'pitch', 'yaw' in degrees for upper arm.
        forearm_orientation: dict with 'roll', 'pitch', 'yaw' in degrees for forearm.
        L1, L2 are in mm. Result is (x, y, z) in mm.
        """
        try:
            if self.debug_mode:
                self.debug_update.emit(f"Calculating wrist with yaw. Upper: {upper_arm_orientation}, Forearm: {forearm_orientation}")

            # Convert degrees to radians
            ua_roll_rad = math.radians(upper_arm_orientation['roll'])
            ua_pitch_rad = math.radians(upper_arm_orientation['pitch'])
            ua_yaw_rad = math.radians(upper_arm_orientation['yaw'])

            fa_roll_rad = math.radians(forearm_orientation['roll'])
            fa_pitch_rad = math.radians(forearm_orientation['pitch'])
            fa_yaw_rad = math.radians(forearm_orientation['yaw'])

            # Define segment vectors in their local frames (along X-axis)
            # self.L1 and self.L2 are assumed to be in mm
            vec_upperarm_local = np.array([self.L1, 0, 0]) 
            vec_forearm_local = np.array([self.L2, 0, 0])

            # Calculate rotation matrices (transform from local segment frame to global frame)
            R_upperarm_to_global = self._euler_to_rotation_matrix(ua_roll_rad, ua_pitch_rad, ua_yaw_rad)
            R_forearm_to_global = self._euler_to_rotation_matrix(fa_roll_rad, fa_pitch_rad, fa_yaw_rad)

            # Calculate segment vectors in the global frame
            # Vector from shoulder (origin) to elbow
            vec_upperarm_global = R_upperarm_to_global @ vec_upperarm_local
            
            # Vector from elbow to wrist, assuming forearm IMU gives global orientation of forearm segment
            vec_forearm_global = R_forearm_to_global @ vec_forearm_local
            
            # Wrist position is the sum of the global upper arm vector and global forearm vector
            # (Shoulder is at origin [0,0,0])
            # P_elbow = vec_upperarm_global
            # P_wrist = P_elbow + vec_forearm_global 
            wrist_pos_global_coords = vec_upperarm_global + vec_forearm_global
            
            result = (
                wrist_pos_global_coords[0],
                wrist_pos_global_coords[1],
                wrist_pos_global_coords[2]
            )
            
            if self.debug_mode:
                self.debug_update.emit(f"Calculated wrist (x,y,z) with yaw: {result}")
            return result
        except KeyError as e: # Xử lý trường hợp thiếu key 'roll', 'pitch', 'yaw'
            if self.debug_mode:
                self.debug_update.emit(f"KeyError in calculate_wrist_position: Missing {str(e)} in sensor data.")
                self.debug_update.emit(f"Upper arm data: {upper_arm_orientation.keys()}")
                self.debug_update.emit(f"Forearm data: {forearm_orientation.keys()}")
            return (0.0, 0.0, 0.0) # Trả về vị trí mặc định
        except Exception as e:
            if self.debug_mode:
                import traceback
                self.debug_update.emit(f"Error in calculate_wrist_position (yaw): {str(e)}")
                self.debug_update.emit(f"Traceback: {traceback.format_exc()}")
            return (0.0, 0.0, 0.0) # Trả về vị trí mặc định

    def parse_timestamp(self, ts_str):
        if not ts_str: return datetime.now()
        # Giữ nguyên logic parse_timestamp của bạn, đảm bảo nó hoạt động với format từ ESP32
        # Ví dụ:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%H:%M:%S.%f", "%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"): # Thêm các format phổ biến
            try:
                dt_obj = datetime.strptime(ts_str, fmt)
                # Nếu timestamp chỉ có giờ phút giây, cần gán ngày hiện tại
                if dt_obj.year == 1900: # Năm mặc định của strptime nếu không có thông tin ngày
                    now = datetime.now()
                    return dt_obj.replace(year=now.year, month=now.month, day=now.day)
                return dt_obj
            except ValueError:
                continue
        if self.debug_mode:
            self.debug_update.emit(f"Could not parse timestamp: {ts_str}. Using current time.")
        return datetime.now() # Fallback

    def close_all_sockets(self):
        with self.lock:
            for conn in list(self.connections): # Tạo bản sao để duyệt vì self.connections có thể bị sửa đổi
                try: conn.shutdown(socket.SHUT_RDWR) # Thử shutdown trước
                except: pass
                try: conn.close()
                except: pass
                if conn in self.connections: self.connections.remove(conn)
            
            for s in list(self.sockets): # Tạo bản sao
                try: s.close()
                except: pass
                if s in self.sockets: self.sockets.remove(s)
            
            # self.connections.clear() # Đã remove ở trên
            # self.sockets.clear()   # Đã remove ở trên

    def stop(self):
        self.status_update.emit("Stopping ESP32 socket server")
        self.running = False
        # Không cần gọi close_all_sockets() ở đây nữa vì nó sẽ được gọi trong self.run() khi self.running=False
        # self.close_all_sockets() # Đã được gọi ở cuối self.run()
        
        # Chờ thread kết thúc
        if self.isRunning(): # Kiểm tra nếu thread đang chạy
             self.wait(2000) # Chờ tối đa 2 giây

# Phần còn lại của code (ví dụ: if __name__ == "__main__":) giữ nguyên nếu có.
if __name__ == "__main__":
    server = DataSyncServer(L1=0.3, L2=0.25)
    server.start()