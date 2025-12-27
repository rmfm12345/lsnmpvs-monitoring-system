import random
import threading
import json
import time
from pyexpat.errors import messages

from Agent.VirtualSensor import VirtualSensor
from datetime import datetime
from Protocol.protocol import encode_complete_pdu, decode_complete_pdu


class LSNMPAgent:
    def __init__(self):
        self.sampling_rates = {}
        self.beacon_rate = 30
        self.sensors = {
            # Sensores básicos (já tens)
            "1": VirtualSensor(0, 100, sampling_rate=0.1, sensor_type="Temperatura"),
            "2": VirtualSensor(-50, 50, sampling_rate=0.1, sensor_type="Humidade"),

            # Novos sensores para testar
            "3": VirtualSensor(0, 1000, sampling_rate=0.05, sensor_type="Luz"),
            "4": VirtualSensor(980, 1020, sampling_rate=0.2, sensor_type="Pressão"),
            "5": VirtualSensor(0, 100, sampling_rate=0.15, sensor_type="Qualidade do Ar"),
            "6": VirtualSensor(-20, 60, sampling_rate=0.08, sensor_type="Temperatura Externa"),
            "7": VirtualSensor(0, 500, sampling_rate=0.25, sensor_type="Ruído"),
            "8": VirtualSensor(0, 100, sampling_rate=0.3, sensor_type="Bateria")
        }
        self.notification_callback = None
        self.running = True
        self._start_notification_loop()
        self.start_time = time.time()

    def _start_notification_loop(self):
        """Start the notification loop in a backgroup thread"""
        thread = threading.Thread(target=self._notification_loop)
        thread.deamon = True
        thread.start()
        print(" Sensor notification loop started")

    def _notification_loop(self):
        while self.running:
            current_time = time.time()

            for sensor_iid, sensor in self.sensors.items():
                if sensor.should_sample(current_time):
                    value = sensor.read()
                    sensor.update_last_sample(current_time)

                    if self.notification_callback:
                        notification_msg = LSNMPMessage(
                            msg_type="notification",
                            iid_list=[f"2.3.{sensor_iid}"],
                            value_list=[value]
                        )
                        self.notification_callback(notification_msg)
            time.sleep(0.01)

    def set_notification_callback(self, callback):
        """Set the callback for sending notifications to server"""
        self.notification_callback = callback

    def generate_beacon(self):
        """Gera a mensagem beacon"""
        return LSNMPMessage(
            msg_type="notification",
            iid_list=["1.1", "1.2", "1.5", "1.8"],
            value_list=[
                self._get_device_value("1.1"),  # lMibId
                self._get_device_value("1.2"),  # device.id
                self._get_device_value("1.5"),  # nSensors
                self._get_device_value("1.8")   # opStatus
        ]
        )

    def get_value(self, iid):
        sensor = self.sensors.get(iid)
        if sensor:
            return sensor.read()
        return None

    def _get_device_value(self, iid):
        """Obtem valores do device group (1.1 a 1.9)"""
        device_values = {
            "1.1": 123,  # device.lMibId - ID do L-MIB
            "1.2": "Agent_001",  # device.id - ID do dispositivo
            "1.3": "Sensing Hub",  # device.type - Tipo de dispositivo
            "1.4": self.beacon_rate,  # device.beaconRate - Beacon rate em segundos
            "1.5": len(self.sensors),  # device.nSensors - Número de sensores
            "1.6": self._get_current_timestamp(),  # device.dateAndTime
            "1.7": self._get_uptime(),  # device.upTime
            "1.8": 1,  # device.opStatus (0=standby, 1=normal, 2=erro)
            "1.9": 0  # device.reset (0=normal, 1=reset)
        }
        return device_values.get(iid)

    def _handle_set_request(self, request_data, addr):
        """Processa SET request"""
        iid_list = request_data['iid_list']
        value_list = request_data['v_list']

        if iid_list == ["1.4"]:
            old_rate = self.beacon_rate
            self.beacon_rate = value_list[0]
            print(f"    Beacon rate atualizado: {old_rate}s -> {self.beacon_rate}s")
        elif iid_list == ["1.9"]:
            if value_list[0] == 1:
                self._reset_device()
        elif iid_list[0].startswith("2.7."):
            #esta mal, alterar depois
            sensor_id = iid_list[0]
            self.sampling_rates[sensor_id] = value_list[0]
            print(f"    Sampling rate {sensor_id}: {value_list[0]}Hz")

        return LSNMPMessage(
            msg_type="response",
            iid_list=iid_list,
            value_list=value_list
        )

    def _handle_get_request(self, data, addr):
        iid_list = data["iid_list"]
        values = []

        #Processa cada IID individualmente
        for iid in iid_list:
            if iid.startswith("1."):
                value = self._get_device_value(iid)
            elif iid.startswith("2.3."):
                sensor_index = iid.split('.')[2]
                sensor = self.sensors.get(sensor_index)  # ⬅️ Agora procura pelo índice correto
                value = sensor.read() if sensor else None
            elif iid.startswith("2."):
                value = self._get_sensor_table_value(iid)
            else:
                value = None

            values.append(value)

        message = LSNMPMessage(
            msg_type="response",
            iid_list=iid_list,
            value_list=values
        )
        return message

    def _get_sensor_table_value(self, iid):
        """Obtem valores da sensor table"""
        #Extrai o indice do sensor e o objeto
        parts = iid.split('.')
        if len(parts) != 3:
            return None

        structure, object_type, sensor_index = parts

        sensor_value_iid = f"{sensor_index}"
        sensor = self.sensors.get(sensor_index)
        if sensor_value_iid not in self.sensors:
            return None

        # Retorna o valor beaseado no tipo de objeto
        if object_type == "1":
            return f"Sensor_{sensor_index}"

        elif object_type == "2":
            if sensor_index in self.sensors:
                sensor = self.sensors[sensor_index]
                return sensor.type
            else:
                return None

        elif object_type == "4":
            sensor = self.sensors.get(sensor_value_iid)
            return sensor.min if sensor else None

        elif object_type == "5":
            sensor = self.sensors.get(sensor_value_iid)
            return sensor.max if sensor else None

        elif object_type == "6":
            if hasattr(sensor, 'last_sample_time') and sensor.last_sample_time > 0:
                elapsed_time = time.time() - sensor.last_sample_time
                # Constrói o timestamp Type 1 manualmente: days:hours:mins:secs:ms
                days = int(elapsed_time // 86400)
                hours = int((elapsed_time % 86400) // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)
                milliseconds = int((elapsed_time * 1000) % 1000)
                return f"{days}:{hours}:{minutes}:{seconds}:{milliseconds}"
            else:
                return "0:0:0:0:0"

        elif object_type == "7":
            sensor = self.sensors.get(sensor_value_iid)
            return int(sensor.sampling_rate * 10) if sensor else None
        else:
            return None

    def _get_sensor_table_values(self, iid):
        """Obtem valores de sensores table (2.1, 2.2, 2.4, 2.5, etc.)"""
        #Estrai o indice do sensor e o objecto
        parts = iid.split('.')
        if len(parts) != 3:
            return None

        structure, object_type, sensor_index = parts

        #Verifica se o sensor existe
        sensor_value_iid = f"2.3.{sensor_index}"
        if sensor_value_iid not in self.sensors:
            return None

        sensor = self.sensors[sensor_value_iid]

        #Retorna o valor baseado no tipo de objeto
        if object_type == "1":
            return f"Sensor_{sensor_index}"
        elif object_type == "2":
            return "Virtual Sensor"
        elif object_type == "4":
            return sensor.min
        elif object_type == "5":
            return sensor.max
        elif object_type == "6":
            return self._get_current_timestamp()
        elif object_type == "7":
            return int(sensor.sampling_rate * 10)
        else:
            return None

    def _reset_device(self):
        """Reset the device to default values"""
        print(" Device reset excuted")
        self.beacon_rate = 30
        self.start_time = time.time()
        for sensor_iid, sensor in self.sensors.items():
            if "2.3.1" in sensor_iid:
                sensor.sampling_rate = 1
            elif "2.3.2" in sensor_iid:
                sensor.sampling_rate = 0.001

    def _get_current_timestamp(self):
        """Retorna timestamp atual no formato day:month:year:hours:mins:secs:ms"""
        now = datetime.now()
        return f"{now.day}:{now.month}:{now.year}:{now.hour}:{now.minute}:{now.second}:{now.microsecond // 1000}"

    def _get_uptime(self):
        """Retorna uptime no formato hours:mins:secs:ms"""
        uptime_seconds = time.time() - self.start_time

        #Converte para horas, minutes, segundos, millissegundos
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        milliseconds = int((uptime_seconds * 1000) % 1000)

        return f"{days}:{hours}:{minutes}:{seconds}:{milliseconds}"

class LSNMPMessage:
    def __init__(self, msg_type, iid_list, value_list):
        self.tag = "LSNMPv2"
        self.type = msg_type
        self.timestamp = self._get_current_timestamp()
        self.msg_id = random.randint(1, 100)
        self.iid_list = iid_list
        self.v_list = value_list
        self.t_list = []
        self.e_list = []

    def _get_current_timestamp(self):
        now = datetime.now()
        return f"{now.day}:{now.month}:{now.year}:{now.hour}:{now.minute}:{now.second}:{now.microsecond//1000}"

    def encode_protocol(self):
        """Encoding with protocol"""
        return encode_complete_pdu(
        msg_type=self.type,
        timestamp=self.timestamp,
        msg_id=self.msg_id,
        iid_list=self.iid_list,
        v_list=self.v_list,
        t_list=self.t_list,
        e_list=self.e_list
        )

    @classmethod
    def decode_protocol(cls, data):
        """Decoding with protocol"""

        decoded_data = decode_complete_pdu(data)

        msg_type = decoded_data['type']

        message = cls(
            msg_type=msg_type,
            iid_list=decoded_data['iid_list'],
            value_list=decoded_data['v_list']
        )

        message.tag = decoded_data['tag']
        message.timestamp = decoded_data['timestamp']
        message.msg_id = decoded_data['msg_id']
        message.t_list = decoded_data['t_list']
        message.e_list = decoded_data['e_list']

        return message
