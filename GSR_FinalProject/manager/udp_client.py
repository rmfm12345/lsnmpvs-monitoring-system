import random
import socket
import threading
import time
import json
import hashlib
import hmac
import base64
from datetime import datetime
from Protocol.protocol import encode_complete_pdu, decode_complete_pdu, encrypt, decrypt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import struct


class UDPClient:
    def __init__(self, host='localhost', port=1161, beacon_port=1163, shared_key="default_key_12345678"):
        self.host = host
        self.port = port
        self.beacon_port = beacon_port
        #Socket para requests normais
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(5)
        self.message_counter = random.randint(0, 50)
        #Socket SEPARADO para receber beacons
        self.beacon_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.beacon_socket.bind(('0.0.0.0', self.beacon_port))
        self.beacon_socket.settimeout(1.0)
        self.key = hashlib.sha256(shared_key.encode()).digest()[:16]
        
        self.running = True
        self.beacon_thread = None

    def send_request(self ,msg_type ,iid_list, v_list=[]):
        """Envia pedido para o Agent e recebe resposta"""
        request_bytes = encode_complete_pdu(
            msg_type=msg_type,
            msg_id= self.message_counter,
            timestamp= self._get_current_timestamp(),
            iid_list= iid_list,
            v_list = v_list,
            t_list= [],
            e_list= []
        )

        request_bytes = encrypt(request_bytes, self.key)
        # 2. Envia para agent

        self.socket.sendto(request_bytes, (self.host, self.port))

        # 3. Recebe response
        response_data, addr = self.socket.recvfrom(1024)
        response_data = decrypt(response_data, self.key)
        decoded_message = decode_complete_pdu(response_data)
        self.message_counter += 1
        return (decoded_message)
    
    def start_beacon_listener(self):
        """Inicia thread para escutar beacons em backgroud"""
        self.beacon_thread = threading.Thread(target=self._beacon_listener_loop)
        self.beacon_thread.daemon = True
        self.beacon_thread.start()
        print(f"    Beacon listener started")
        
    def _beacon_listener_loop(self):
        """Loop que escuta por beacons dos Agents"""
        while self.running:
            try:
                data, addr = self.beacon_socket.recvfrom(1024)
                beacon_msg = decode_complete_pdu(data)
                #Processa o beacon recebido
                self._handle_beacon(beacon_msg, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"> beacon receive error: {e}")

    def _handle_beacon(self, beacon_msg, addr):
        """Processa um beacon recebido"""
        #print(f"\n📡 BEACON received from {addr[0]}:")

        # 🎯 DETECT WHAT TYPE OF BEACON THIS IS
        iid_list = beacon_msg['iid_list']
        v_list = beacon_msg['v_list']

        if iid_list == ["1.1", "1.2", "1.5", "1.8"]:
            # 🔔 GLOBAL BEACON (Device Info)
            print(f"   🔔 GLOBAL BEACON:")
            print(f"   🆔 Agent ID: {v_list[1]}")
            print(f"   📊 Total Sensors: {v_list[2]}")
            print(f"   🟢 Status: {'Normal' if v_list[3] == 1 else 'Error'}")
            print(f"   🔧 MIB ID: {v_list[0]}")

        elif len(iid_list) == 1 and iid_list[0].startswith("2.3."):
            # 📡 INDIVIDUAL SENSOR NOTIFICATION
            sensor_iid = iid_list[0]
            sensor_value = v_list[0]
            print(f"   📡 SENSOR NOTIFICATION:")
            print(f"   🔸 Sensor: {sensor_iid}")
            print(f"   💾 Value: {sensor_value}%")
            print(f"   ⏰ Timestamp: {beacon_msg['timestamp']}")

        else:
            # ❌ UNKNOWN BEACON TYPE
            print(f"   ❓ UNKNOWN BEACON TYPE:")
            print(f"   IIDs: {iid_list}")
            print(f"   Values: {v_list}")

        print(f"   📨 Type: {beacon_msg['type']}")
        print(f"   🆔 MSG-ID: {beacon_msg['msg_id']}")
        
    def configure_beacon_rate(self, new_rate):
        """Configure o beacon rate do Agent"""
        try:
            response = self.send_request(
                msg_type="set-request",
                iid_list=["1.4"],
                v_list=[new_rate]
            )
            print(f"    Beacon rate configured to {new_rate}s")
            return response
        except Exception as e:
            print(f"X Error configuring beaocn rate: {e}")
            return None
        
    def get_sensor_value(self, iid_list):
        """Pede valores de sensores especificos"""
        try:
            response = self.send_request(
                msg_type="get-request",
                iid_list=iid_list
            )
            return response
        except Exception as e:
            print(f"X Error getting sensor values: {e}")

    def close(self):
        """Fecha todos os sockets"""
        self.running = False
        self.socket.close()
        self.beacon_socket.close()
        if self.beacon_thread:
            self.beacon_thread.join()
        print("🛑 UDP Client closed")

    def _get_current_timestamp(self):
        now = datetime.now()
        return f"{now.day}:{now.month}:{now.year}:{now.hour}:{now.minute}:{now.second}:{now.microsecond//1000}"


if __name__ == "__main__":
    client = UDPClient()

    # Envia request e imprime a mensagem raw recebida
    raw_message = client.send_request(["2.3.1", "2.3.2"])
    print(f"Message: {raw_message}")
    client.close()
