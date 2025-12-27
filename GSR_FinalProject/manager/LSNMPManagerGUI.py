import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
from manager.udp_client import UDPClient


class BeaconDashboard:
    """Classe para gerir e mostrar beacons recebidos"""

    def __init__(self):
        self.last_global_beacon = None
        self.last_global_time = None
        self.recent_sensor_activity = []
        self.max_sensor_activity = 8
        self.activity_time_window = 120  # 2 minutos
        self.beacon_count = 0
        self.last_update = time.time()

    def update_with_beacon(self, beacon_msg, addr):
        """Atualiza o dashboard com um novo beacon"""
        self.beacon_count += 1
        iid_list = beacon_msg['iid_list']
        v_list = beacon_msg['v_list']
        current_time = time.time()

        if iid_list == ["1.1", "1.2", "1.5", "1.8"]:
            # 🔔 BEACON GLOBAL
            self.last_global_beacon = {
                'agent_id': v_list[1],
                'total_sensors': v_list[2],
                'status': "🟢 NORMAL" if v_list[3] == 1 else "🔴 ERRO",
                'mib_id': v_list[0],
                'timestamp': beacon_msg['timestamp']
            }
            self.last_global_time = current_time

        elif len(iid_list) == 1 and iid_list[0].startswith("2.3."):
            # 📡 NOTIFICAÇÃO DE SENSOR
            sensor_iid = iid_list[0]
            sensor_value = v_list[0]
            sensor_num = sensor_iid.split('.')[2]

            # Procura se já existe atividade deste sensor
            found = False
            for i, activity in enumerate(self.recent_sensor_activity):
                if activity[0] == sensor_num:
                    # Atualiza atividade existente
                    self.recent_sensor_activity[i] = (sensor_num, sensor_value, current_time, beacon_msg['timestamp'])
                    found = True
                    break

            # Se não encontrou, adiciona nova atividade
            if not found:
                self.recent_sensor_activity.append((
                    sensor_num,
                    sensor_value,
                    current_time,
                    beacon_msg['timestamp']
                ))

            self._cleanup_old_activity()

        self.last_update = current_time

    def _cleanup_old_activity(self):
        """Remove atividade antiga"""
        current_time = time.time()
        cutoff_time = current_time - self.activity_time_window

        # Remove atividade antiga
        self.recent_sensor_activity = [
            activity for activity in self.recent_sensor_activity
            if activity[2] > cutoff_time
        ]

        # Ordena por timestamp mais recente primeiro
        self.recent_sensor_activity.sort(key=lambda x: x[2], reverse=True)

        # Mantém apenas as últimas max_sensor_activity atividades
        if len(self.recent_sensor_activity) > self.max_sensor_activity:
            self.recent_sensor_activity = self.recent_sensor_activity[:self.max_sensor_activity]

    def format_time_ago(self, timestamp):
        """Formata tempo decorrido"""
        elapsed = time.time() - timestamp
        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)}m"
        else:
            return f"{int(elapsed / 3600)}h"

    def get_formatted_dashboard(self):
        """Retorna dashboard formatado"""
        lines = []
        lines.append("═" * 70)
        lines.append("📊 BEACON DASHBOARD")
        lines.append("═" * 70)

        # Seção 1: Último Beacon Global
        if self.last_global_beacon:
            time_ago = self.format_time_ago(self.last_global_time)
            lines.append(f"🔔 LAST GLOBAL BEACON ({time_ago} ago)")
            lines.append(f"   🆔 {self.last_global_beacon['agent_id']}")
            lines.append(f"   📡 {self.last_global_beacon['total_sensors']} sensors")
            lines.append(f"   {self.last_global_beacon['status']}")
        else:
            lines.append(f"🔔 GLOBAL BEACON: None received")

        lines.append("─" * 70)

        # Seção 2: Atividade Recente
        lines.append(f"📈 RECENT ACTIVITY (last {self.activity_time_window // 60}min)")

        if self.recent_sensor_activity:
            sorted_activity = sorted(self.recent_sensor_activity,
                                     key=lambda x: x[2], reverse=True)

            for sensor_num, value, timestamp, _ in sorted_activity:
                time_ago = self.format_time_ago(timestamp)
                lines.append(f"   • Sensor {sensor_num}: {value}% ({time_ago} ago)")
        else:
            lines.append(f"   • No recent activity")

        lines.append("═" * 70)  # Changed from "─" to "═" to close the dashboard

        return "\n".join(lines)

class LSNMPManagerGUI:
    def __init__(self, udp_client):
        self.client = udp_client
        self.root = tk.Tk()
        self.root.title("L-SNMPvS Manager")
        self.root.geometry("1000x800")  # Aumentei um pouco para o dashboard

        # Queue para comunicação thread-safe
        self.message_queue = queue.Queue()

        # Dashboard de beacons
        self.dashboard = BeaconDashboard()
        self.show_dashboard = True

        self.setup_ui()

        # Iniciar atualização da UI da queue
        self.root.after(100, self.process_queue)
        # Iniciar atualização do dashboard
        self.root.after(1000, self.update_dashboard)

        # Iniciar listener de beacons em background
        self.client.start_beacon_listener()

        # Modificar o handler de beacons para atualizar o dashboard
        self.modify_beacon_handler()

    def modify_beacon_handler(self):
        """Modifica o handler de beacons para NÃO mostrar no output log"""
        original_handle_beacon = self.client._handle_beacon

        def new_handle_beacon(beacon_msg, addr):
            # ⬇️⬇️⬇️ APENAS ATUALIZA O DASHBOARD, NÃO LOGA NO OUTPUT ⬇️⬇️⬇️
            self.dashboard.update_with_beacon(beacon_msg, addr)

            # ⬇️⬇️⬇️ NÃO CHAMA O HANDLER ORIGINAL (que logava no output) ⬇️⬇️⬇️
            # Isso evita que apareça no output log
            # if original_handle_beacon:
            #     original_handle_beacon(beacon_msg, addr)  # 🚫 COMENTADO!

            # Apenas atualiza o status discretamente
            iid_list = beacon_msg['iid_list']
            if iid_list == ["1.1", "1.2", "1.5", "1.8"]:
                self.update_status("🟢 Ready | 🔔 Global beacon received")
            elif len(iid_list) == 1 and iid_list[0].startswith("2.3."):
                sensor_num = iid_list[0].split('.')[2]
                self.update_status(f"🟢 Ready | 📡 Sensor {sensor_num} updated")

        self.client._handle_beacon = new_handle_beacon

    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configurar expansão
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=2)  # Output mais largo
        main_frame.rowconfigure(0, weight=0)  # Título (altura fixa)
        main_frame.rowconfigure(1, weight=2)  # Linha 1: botões (menor)
        main_frame.rowconfigure(2, weight=3)  # Linha 2: dashboard (maior)

        # Título
        title_label = ttk.Label(main_frame,
                                text="📡 L-SNMPvS Manager",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)

        # ============ DEVICE SECTION ============
        device_frame = ttk.LabelFrame(main_frame, text="🏢 Device Control", padding="8")  # Padding reduzido
        device_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Botões do Device Group - texto ORIGINAL mas layout compacto
        ttk.Button(device_frame, text="1. Get All Device Info",
                   command=self.get_all_device_info).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Button(device_frame, text="1.1 Get L-MIB ID",
                   command=self.get_lmib_id).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Button(device_frame, text="1.2 Get Device ID",
                   command=self.get_device_id).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Button(device_frame, text="1.3 Get Device Type",
                   command=self.get_device_type).grid(row=3, column=0, sticky=tk.W, pady=2)

        # Beacon rate control - texto ORIGINAL
        beacon_frame = ttk.Frame(device_frame)
        beacon_frame.grid(row=4, column=0, sticky=tk.W, pady=5)  # Menos pady

        ttk.Label(beacon_frame, text="Beacon Rate:").grid(row=0, column=0)
        self.beacon_rate_var = tk.StringVar(value="30")
        beacon_entry = ttk.Entry(beacon_frame, textvariable=self.beacon_rate_var, width=10)
        beacon_entry.grid(row=0, column=1, padx=3)  # Menos padx
        ttk.Button(beacon_frame, text="Set",
                   command=self.set_beacon_rate).grid(row=0, column=2)

        # Botões adicionais do device - texto ORIGINAL
        ttk.Button(device_frame, text="1.5 Get Sensor Count",
                   command=self.get_sensor_count).grid(row=5, column=0, sticky=tk.W, pady=2)
        ttk.Button(device_frame, text="1.7 Get Uptime",
                   command=self.get_uptime).grid(row=6, column=0, sticky=tk.W, pady=2)
        ttk.Button(device_frame, text="1.8 Get Status",
                   command=self.get_status).grid(row=7, column=0, sticky=tk.W, pady=2)
        ttk.Button(device_frame, text="1.9 Reset Device",
                   command=self.reset_device).grid(row=8, column=0, sticky=tk.W, pady=2)

        # ============ SENSORS SECTION ============
        sensors_frame = ttk.LabelFrame(main_frame, text="📊 Sensors Control", padding="8")  # Padding reduzido
        sensors_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 5))

        # Botões dos sensores - texto ORIGINAL
        ttk.Button(sensors_frame, text="2. Read All Sensors",
                   command=self.read_all_sensors).grid(row=0, column=0, sticky=tk.W, pady=2)

        # Sensor selection - texto ORIGINAL
        ttk.Label(sensors_frame, text="Sensor Index:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.sensor_index_var = tk.StringVar(value="1")
        sensor_spin = ttk.Spinbox(sensors_frame, from_=1, to=8, textvariable=self.sensor_index_var, width=10)
        sensor_spin.grid(row=2, column=0, sticky=tk.W, pady=2)

        # Botões para sensor específico - texto ORIGINAL
        ttk.Button(sensors_frame, text="2.1 Get Sensor ID",
                   command=self.get_sensor_id).grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Button(sensors_frame, text="2.2 Get Sensor Type",
                   command=self.get_sensor_type).grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Button(sensors_frame, text="2.3 Get Sensor Value",
                   command=self.get_sensor_value).grid(row=5, column=0, sticky=tk.W, pady=2)
        ttk.Button(sensors_frame, text="2.4 Get Min Value",
                   command=self.get_sensor_min).grid(row=6, column=0, sticky=tk.W, pady=2)
        ttk.Button(sensors_frame, text="2.5 Get Max Value",
                   command=self.get_sensor_max).grid(row=7, column=0, sticky=tk.W, pady=2)
        ttk.Button(sensors_frame, text="2.6 Get Last Sample Time",
                   command=self.get_last_sample_time).grid(row=8, column=0, sticky=tk.W, pady=2)

        # Sampling rate control - texto ORIGINAL
        sample_frame = ttk.Frame(sensors_frame)
        sample_frame.grid(row=9, column=0, sticky=tk.W, pady=5)  # Menos pady

        ttk.Label(sample_frame, text="Sampling Rate (Hz):").grid(row=0, column=0)
        self.sampling_rate_var = tk.StringVar(value="10")
        sample_entry = ttk.Entry(sample_frame, textvariable=self.sampling_rate_var, width=10)
        sample_entry.grid(row=0, column=1, padx=3)  # Menos padx
        ttk.Button(sample_frame, text="Set",
                   command=self.set_sampling_rate).grid(row=0, column=2)

        # ============ OUTPUT SECTION (lado direito) ============
        output_frame = ttk.LabelFrame(main_frame, text="📝 Output Log", padding="10")
        output_frame.grid(row=1, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))

        # Text area para output (vertical)
        self.output_text = scrolledtext.ScrolledText(output_frame, width=50, height=35)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configurar expansão do output
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        # ============ DASHBOARD SECTION (maior verticalmente) ============
        dashboard_frame = ttk.LabelFrame(main_frame, text="📊 Beacon Dashboard", padding="10")
        dashboard_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

        # Área de texto para o dashboard (MAIOR verticalmente)
        self.dashboard_text = scrolledtext.ScrolledText(dashboard_frame, width=100, height=12,  # Aumentei height
                                                        font=("Courier", 9), state='disabled')
        self.dashboard_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configurar expansão do dashboard
        dashboard_frame.columnconfigure(0, weight=1)
        dashboard_frame.rowconfigure(0, weight=1)

        # ============ STATUS BAR ============
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        self.status_var = tk.StringVar(value="🟢 Ready | 📡 Waiting for beacons...")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)

        # Configurar expansão dos frames
        device_frame.columnconfigure(0, weight=1)
        sensors_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        dashboard_frame.columnconfigure(0, weight=1)


        # ============ NOVOS MÉTODOS DO DASHBOARD ============
    def update_dashboard(self):
        """Atualiza o display do dashboard"""
        if self.show_dashboard:
            dashboard_content = self.dashboard.get_formatted_dashboard()
            self.dashboard_text.config(state='normal')
            self.dashboard_text.delete(1.0, tk.END)
            self.dashboard_text.insert(1.0, dashboard_content)
            self.dashboard_text.config(state='disabled')

        # Agenda próxima atualização
        self.root.after(1000, self.update_dashboard)

    def refresh_dashboard(self):
        """Força refresh do dashboard"""
        self.update_dashboard()
        self.update_status("🟢 Ready | 🔄 Dashboard refreshed")

    # ============ MÉTODOS EXISTENTES (MANTÊM IGUAL) ============
    def log_message(self, message):
        """Adiciona mensagem à área de output"""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.update()

    def update_status(self, status):
        """Atualiza a barra de status"""
        self.status_var.set(status)

    def process_queue(self):
        """Processa mensagens da queue (thread-safe)"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.log_message(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def run_in_thread(self, func, *args):
        """Executa função em thread separada"""

        def thread_wrapper():
            try:
                self.update_status("🔄 Processing...")
                result = func(*args)
                if result:
                    self.message_queue.put(result)
                self.update_status("🟢 Ready")
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                self.message_queue.put(error_msg)
                self.update_status("🔴 Error")

        thread = threading.Thread(target=thread_wrapper, daemon=True)
        thread.start()

    # ============ DEVICE METHODS (MANTÊM IGUAL) ============
    def get_all_device_info(self):
        def action():
            response = self.client.send_request("get-request",
                                                ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9"])
            if response and response['v_list']:
                output = "🏢 DEVICE INFORMATION:\n"
                output += f"   L-MIB ID: {response['v_list'][0]}\n"
                output += f"   Device ID: {response['v_list'][1]}\n"
                output += f"   Device Type: {response['v_list'][2]}\n"
                output += f"   Beacon Rate: {response['v_list'][3]}s\n"
                output += f"   Sensor Count: {response['v_list'][4]}\n"
                output += f"   Date/Time: {response['v_list'][5]}\n"
                output += f"   Uptime: {response['v_list'][6]}\n"
                output += f"   Status: {'Normal' if response['v_list'][7] == 1 else 'Error'}\n"
                output += f"   Reset State: {'Normal' if response['v_list'][8] == 0 else 'Resetting'}\n"
                return output
            return "❌ No response from device"

        self.run_in_thread(action)

    def get_lmib_id(self):
        def action():
            response = self.client.send_request("get-request", ["1.1"])
            if response and response['v_list']:
                return f"🏷️  L-MIB ID: {response['v_list'][0]}"
            return "❌ No response"

        self.run_in_thread(action)

    def get_device_id(self):
        def action():
            response = self.client.send_request("get-request", ["1.2"])
            if response and response['v_list']:
                return f"🆔 Device ID: {response['v_list'][0]}"
            return "❌ No response"

        self.run_in_thread(action)

    def get_device_type(self):
        def action():
            response = self.client.send_request("get-request", ["1.3"])
            if response and response['v_list']:
                return f"🏭 Device Type: {response['v_list'][0]}"
            return "❌ No response"

        self.run_in_thread(action)

    def set_beacon_rate(self):
        def action():
            rate = self.beacon_rate_var.get()
            if rate.isdigit():
                response = self.client.send_request("set-request", ["1.4"], [int(rate)])
                return f"🔧 Beacon rate set to {rate}s"
            return "❌ Invalid beacon rate"

        self.run_in_thread(action)

    def get_sensor_count(self):
        def action():
            response = self.client.send_request("get-request", ["1.5"])
            if response and response['v_list']:
                return f"📊 Sensor Count: {response['v_list'][0]}"
            return "❌ No response"

        self.run_in_thread(action)

    def get_uptime(self):
        def action():
            response = self.client.send_request("get-request", ["1.7"])
            if response and response['v_list']:
                return f"⏰ Uptime: {response['v_list'][0]}"
            return "❌ No response"

        self.run_in_thread(action)

    def get_status(self):
        def action():
            response = self.client.send_request("get-request", ["1.8"])
            if response and response['v_list']:
                status = "🟢 Normal" if response['v_list'][0] == 1 else "🔴 Error"
                return f"🟢 Status: {status}"
            return "❌ No response"

        self.run_in_thread(action)

    def reset_device(self):
        def action():
            response = self.client.send_request("set-request", ["1.9"], [1])
            return "🔄 Device reset command sent"

        self.run_in_thread(action)

    # ============ SENSOR METHODS (MANTÊM IGUAL) ============
    def read_all_sensors(self):
        def action():
            sensor_iids = [f"2.3.{i}" for i in range(1, 9)]
            response = self.client.send_request("get-request", sensor_iids)
            if response and response['v_list']:
                output = "📊 ALL SENSORS:\n"
                for i, value in enumerate(response['v_list'], 1):
                    output += f"   Sensor {i}: {value}%\n"
                return output
            return "❌ No response from sensors"

        self.run_in_thread(action)

    def get_sensor_id(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            response = self.client.send_request("get-request", [f"2.1.{sensor_idx}"])
            if response and response['v_list']:
                return f"🏷️  Sensor {sensor_idx} ID: {response['v_list'][0]}"
            return f"❌ No response for sensor {sensor_idx}"

        self.run_in_thread(action)

    def get_sensor_type(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            response = self.client.send_request("get-request", [f"2.2.{sensor_idx}"])
            if response and response['v_list']:
                return f"🏭 Sensor {sensor_idx} Type: {response['v_list'][0]}"
            return f"❌ No response for sensor {sensor_idx}"

        self.run_in_thread(action)

    def get_sensor_value(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            response = self.client.send_request("get-request", [f"2.3.{sensor_idx}"])
            if response and response['v_list']:
                return f"📊 Sensor {sensor_idx} Value: {response['v_list'][0]}%"
            return f"❌ No response for sensor {sensor_idx}"

        self.run_in_thread(action)

    def get_sensor_min(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            response = self.client.send_request("get-request", [f"2.4.{sensor_idx}"])
            if response and response['v_list']:
                return f"📏 Sensor {sensor_idx} Min: {response['v_list'][0]}"
            return f"❌ No response for sensor {sensor_idx}"

        self.run_in_thread(action)

    def get_sensor_max(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            response = self.client.send_request("get-request", [f"2.5.{sensor_idx}"])
            if response and response['v_list']:
                return f"📏 Sensor {sensor_idx} Max: {response['v_list'][0]}"
            return f"❌ No response for sensor {sensor_idx}"

        self.run_in_thread(action)

    def get_last_sample_time(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            response = self.client.send_request("get-request", [f"2.6.{sensor_idx}"])
            if response and response['v_list']:
                return f"⏰ Sensor {sensor_idx} Last Sample: {response['v_list'][0]}"
            return f"❌ No response for sensor {sensor_idx}"

        self.run_in_thread(action)

    def set_sampling_rate(self):
        def action():
            sensor_idx = self.sensor_index_var.get()
            rate = self.sampling_rate_var.get()
            if rate.isdigit():
                response = self.client.send_request("set-request", [f"2.7.{sensor_idx}"], [int(rate)])
                return f"🔧 Sensor {sensor_idx} sampling rate set to {rate}Hz"
            return "❌ Invalid sampling rate"

        self.run_in_thread(action)

    def run(self):
        """Inicia a GUI"""
        self.root.mainloop()


# Modo de uso:
if __name__ == "__main__":
    # Cria o cliente UDP
    client = UDPClient(host='localhost', port=1161)

    # Cria e executa a GUI
    gui = LSNMPManagerGUI(client)
    gui.run()