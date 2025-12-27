import socket
import threading
import json
import time
import hashlib


from Agent.lsnmp_agent import LSNMPAgent
from Protocol.protocol import encode_complete_pdu, decode_complete_pdu, encrypt, decrypt


class UDPServer:
    def __init__(self, host='localhost', port=1161, shared_key="default_key_12345678"):
        self.host = host
        self.port = port
        self.agent = LSNMPAgent()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #Socket para enviar beacons
        self.beacon_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.beacon_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.key = hashlib.sha256(shared_key.encode()).digest()[:16]

        self.running = True
        self._start_beacon_service()
        self.agent.set_notification_callback(self.handle_sensor_notification)

    def start(self):
        try:
            self.socket.bind((self.host, self.port))
            print(f"UDP Server running on {self.host}:{self.port}")

            while True:
                data, addr = self.socket.recvfrom(1024)
                self.handle_request(data, addr)
        except Exception as e:
            print(f"Error starting upd server: {e}")

    def handle_request(self, data, addr):
        try:
            data = decrypt(data, self.key)
            request_data = decode_complete_pdu(data)
            iid_list = request_data['iid_list']
            #print(f"   📦 Request IIDs: {iid_list}")
            print(f"        DATA: {request_data}")

            #Verifica se é get ou set
            if request_data['type'] == 'set-request':
                message = self.agent._handle_set_request(request_data, addr)
            else:
                message = self.agent._handle_get_request(request_data, addr)

            response_data = message.encode_protocol()
            response_data = encrypt(response_data, self.key)
            print("Message= ", response_data)

            # 4. Envia via UDP
            self.socket.sendto(response_data, addr)
        except Exception as e:
            print(f"Error handling request: {e}")

    def handle_sensor_notification(self, notification_msg):
        """ CALLBACK FUNCTION - Called by Agente when a sernsor has new data"""
        try:
            #print(f"📡 [CALLBACK] Sensor notification received:")
            #print(f"   🆔 Sensor: {notification_msg.iid_list[0]}")
            #print(f"   💾 Value: {notification_msg.v_list[0]}")

            encoded_notification = notification_msg.encode_protocol()
            self.beacon_socket.sendto(encoded_notification, ('<broadcast>', 1163))
            #print(f"    Sensor notification broadcasted to managers")
        except Exception as e:
            print(f"X Error in sensor notification callback: {e}")

    def _start_beacon_service(self):
        """Server controla o loop de beacons"""
        beacon_thread = threading.Thread(target=self._beacon_loop)
        beacon_thread.daemon = True
        beacon_thread.start()
        print(f" Beacon servcie started - rate: {self.agent.beacon_rate}s")

    def _beacon_loop(self):
        """Loop do server que pede beacons do agent"""
        while self.running:
            beacon_rate = self.agent.beacon_rate

            if beacon_rate > 0:
                try:
                    beacon_msg = self.agent.generate_beacon()
                    encoded_beacon = beacon_msg.encode_protocol()
                    self.beacon_socket.sendto(encoded_beacon, ('<broadcast>', 1163))
                    print(f"Beacon enviado (rate: {beacon_rate}s)")
                except Exception as e:
                    print(f" Erro no beacon loop: {e}")
            time.sleep(beacon_rate)


if __name__== "__main__":
    server = UDPServer()
    server.start()
