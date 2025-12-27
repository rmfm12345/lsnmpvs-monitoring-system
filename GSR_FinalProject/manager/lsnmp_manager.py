import select
import socket
import sys

from manager.udp_client import UDPClient


class LSNMPManager:
    def __init__(self):
        self.udp_client = UDPClient()
        self.udp_client.start_beacon_listener()
        self.message_counter = 1
        self.running = True

    def simple_ui(self):
        while self.running:
            print("\n" + "=" * 60)
            print("               L-SNMPvS UDP MANAGER")
            print("=" * 60)
            print("=== DEVICE GROUP (1.x) ===")
            print("1.  Informações completas do dispositivo (1.1-1.9)")
            print("1.1  ID do L-MIB (1.1)")
            print("1.2  ID do dispositivo (1.2)")
            print("1.3  Tipo de dispositivo (1.3)")
            print("1.4  Configurar beacon rate (1.4)")
            print("1.5  Número de sensores (1.5)")
            print("1.6  Configurar data e hora (1.6)")
            print("1.7  Uptime do dispositivo (1.7)")
            print("1.8  Status operacional (1.8)")
            print("1.9  Reiniciar dispositivo (1.9)")

            print("\n=== SENSORS TABLE (2.x) ===")
            print("2.  Informações completas de todos os sensores")
            print("2.1  ID do sensor (2.1)")
            print("2.2  Tipo de sensor (2.2)")
            print("2.3  Valor atual do sensor (2.3)")
            print("2.4  Valor mínimo do sensor (2.4)")
            print("2.5  Valor máximo do sensor (2.5)")
            print("2.6  Último sampling time (2.6)")
            print("2.7  Configurar sampling rate (2.7)")

            print("\n=== OPERAÇÕES AVANÇADAS ===")
            print("3.  Ativar/desativar beacons")
            print("4.  Ativar/desativar notificações de sensor")
            print("5.  Monitorar notificações em tempo real")
            print("6.  Sair")
            print("=" * 60)

            try:
                user_input = input("Selecione uma opção: ").strip()

                # Device Group (1.x)
                if user_input == "1":
                    self.get_device_info_complete()
                elif user_input == "1.1":
                    self.get_lmib_id()
                elif user_input == "1.2":
                    self.get_device_id()
                elif user_input == "1.3":
                    self.get_device_type()
                elif user_input == "1.4":
                    self.configure_beacon_rate()
                elif user_input == "1.5":
                    self.get_number_of_sensors()
                elif user_input == "1.6":
                    self.get_date_time()
                elif user_input == "1.7":
                    self.get_uptime()
                elif user_input == "1.8":
                    self.get_operational_status()
                elif user_input == "1.9":
                    self.reset_device()

                # Sensors Table (2.x)
                elif user_input == "2":
                    self.read_all_sensors()
                elif user_input == "2.1":
                    self.get_sensor_id()
                elif user_input == "2.2":
                    self.get_sensor_type()
                elif user_input == "2.3":
                    self.get_sensor_value()
                elif user_input == "2.4":
                    self.get_sensor_min_value()
                elif user_input == "2.5":
                    self.get_sensor_max_value()
                elif user_input == "2.6":
                    self.get_last_sampling_time()
                elif user_input == "2.7":
                    self.configure_beacon_rate()

                # Operações Avançadas
                elif user_input == "3":
                    self.toggle_beacons()
                elif user_input == "4":
                    self.toggle_sensor_notifications()
                elif user_input == "5":
                    self.monitor_notifications()
                elif user_input == "6":
                    self.running = False
                    print("A sair do manager...")
                else:
                    print("Comando inválido.")

            except KeyboardInterrupt:
                print("\nOperação cancelada pelo utilizador")
                break
            except Exception as e:
                print(f"Erro: {e}")

    def get_last_sampling_time(self):
        """Feature 2.6 - Ler último sampling time de um sensor"""
        try:
            sensor_index = input("Índice do sensor (1-8): ").strip()

            # Validar input
            if not sensor_index.isdigit():
                print("❌ Índice deve ser um número!")
                return

            iid = f"2.6.{sensor_index}"  # IID para sensors.lastSamplingTime

            print(f"\n📡 A pedir último sampling time do sensor {iid} via UDP...")

            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=[iid]
            )

            print(f"\n⏰ ÚLTIMO SAMPLING TIME DO SENSOR {iid}:")
            if response['v_list']:
                sampling_time = response['v_list'][0]

                # Formatar a apresentação
                parts = sampling_time.split(':')
                if len(parts) == 5:  # Formato Type 1: days:hours:mins:secs:ms
                    days, hours, minutes, seconds, ms = parts

                    print(f"   ⏱️  Tempo desde a última amostra:")
                    if int(days) > 0:
                        print(f"      📅 {days}d {hours}h {minutes}m {seconds}s {ms}ms")
                    elif int(hours) > 0:
                        print(f"      ⏳ {hours}h {minutes}m {seconds}s {ms}ms")
                    elif int(minutes) > 0:
                        print(f"      ⏱️  {minutes}m {seconds}s {ms}ms")
                    else:
                        print(f"      🕐 {seconds}s {ms}ms")
                else:
                    print(f"   🔸 {sampling_time}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_sensor_max_value(self):
        """Feature 2.5 - Ler valor maximo de um sensor especifico"""
        try:
            sensor_index = input("Indice do sensor: ").strip()

            #Validar input
            if not sensor_index.isdigit():
                print("X Indice deve ser um numero")
                return

            iid = f"2.5.{sensor_index}"

            print(f"\n A pedir valor maximo do sensor {iid} via UDP...")

            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=[iid]
            )

            print(f"\n📏 VALOR MÁXIMO DO SENSOR {iid}:")
            if response['v_list']:
                max_value = response['v_list'][0]
                print(f"   🔸 {max_value}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_sensor_min_value(self):
        """Feature 2.4 - Ler valor minimo de um sensr especifico"""
        try:
            sensor_index = input("Indice do sensor: ").strip()

            #Validar input
            if not sensor_index.isdigit():
                print("X Indice deve ser numero")
                return

            iid = f"2.4.{sensor_index}"
            print(f"\n A pedir valor minimo do sensor {iid} via UDP...")

            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=[iid]
            )

            print(f"\n📏 VALOR MÍNIMO DO SENSOR {iid}:")
            if response['v_list']:
                min_value = response['v_list'][0]
                print(f"   🔸 {min_value}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_sensor_value(self):
        """Feature 2.3 - Ler valor atual de um sensor especifico"""
        try:
            sensor_index = input("indice do sensor: ").strip()

            #validar input
            if not sensor_index.isdigit():
                print("X Indice dever ser um número!")
                return

            iid = f"2.3.{sensor_index}"

            print(f"\n A pedir valor do sensor {iid} via UDP...")
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=[iid]
            )

            print(f"\n📊 VALOR DO SENSOR {iid}:")
            if response['v_list']:
                sensor_value = response['v_list'][0]

                # Obter min/max para contexto
                min_max_response = self.udp_client.send_request(
                    msg_type="get-request",
                    iid_list=[f"2.4.{sensor_index}", f"2.5.{sensor_index}"]  # min e max
                )

                min_val = min_max_response['v_list'][0] if len(min_max_response['v_list']) > 0 else "?"
                max_val = min_max_response['v_list'][1] if len(min_max_response['v_list']) > 1 else "?"

                print(f"   🔸 {sensor_value}%")
                print(f"   📏 Range: {min_val} - {max_val}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_sensor_type(self):
        """Feature 2.2 - Ler tipo de um sensor especifico"""
        try:
            sensor_index = input("Indice do sensor: ").strip()

            #Validar input
            if not sensor_index.isdigit():
                print("X Indice deve ser um número")
                return

            iid = f"2.2.{sensor_index}"
            print(f"\n A pedir tipo do sensor {iid} via UDP...")

            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=[iid]
            )

            print(f"\n🏷️  TIPO DO SENSOR {iid}:")
            if response['v_list']:
                sensor_type = response['v_list'][0]
                print(f"   🔸 {sensor_type}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_sensor_id(self):
        """Feature 2.1 - Ler ID de um sensor especifico"""
        try:
            sensor_index = input("Indice do sensor: ").strip()

            #Validor input
            if not sensor_index.isdigit() or not (1 <= int(sensor_index) <= 8):
                print("X Indice invalido!")
                return

            iid = f"2.1.{sensor_index}"
            print(f"\n A pedir ID do sensor {iid} via UDP...")

            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=[iid]
            )

            print(f"\n  ID DO SENSOR {iid}:")
            if response['v_list']:
                sensor_id = response['v_list'][0]
                print(f"🔸 {sensor_id}")
            else:
                print("❌ Nenhum valor retornado")

        except ValueError:
            print("❌ Erro: Índice deve ser um número")
        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def reset_device(self):
        """Feature 1.9 - Reiniciar dispositivo (1.9) - SET request"""
        print("\n🔄 REINICIAR DISPOSITIVO (1.9)")

        try:
            # Primeiro verificar o status atual
            print("📡 A verificar status atual...")
            status_response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.8"]  # Status operacional
            )

            current_status = status_response['v_list'][0] if status_response['v_list'] else "desconhecido"
            print(f"   Status atual: {current_status}")

            # Confirmação do utilizador
            confirm = input("\n⚠️  TEM A CERTEZA QUE QUER REINICIAR O DISPOSITIVO? (s/N): ").strip().lower()

            if confirm != 's':
                print("❌ Reinício cancelado")
                return

            # Enviar SET request para reiniciar
            print("📡 A enviar comando de reinício...")
            reset_response = self.udp_client.send_request(
                msg_type="set-request",
                iid_list=["1.9"],
                v_list=[1]  # 1 = reiniciar
            )

            print("✅ Comando de reinício enviado com sucesso!")
            print("🕐 O dispositivo deverá reiniciar em breve...")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_operational_status(self):
        """Feature 1.8 - Ler status operacional (1.8) - APENAS GET"""
        print("\n📡 A pedir status operacional (1.8) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.8"]  # ⬅️ APENAS o IID 1.8
            )

            print(f"\n🟢 STATUS OPERACIONAL (1.8):")
            if response['v_list']:
                status_code = response['v_list'][0]

                # Mapear códigos para descrições
                status_map = {
                    0: "🟡 STANDBY",
                    1: "🟢 NORMAL",
                    2: "🔴 ERRO"
                }

                status_text = status_map.get(status_code, f"🔴 ESTADO DESCONHECIDO ({status_code})")
                print(f"   {status_text}")

                # Informação adicional
                if status_code == 0:
                    print("   ℹ️  Dispositivo em modo de espera")
                elif status_code == 1:
                    print("   ℹ️  Dispositivo operacional normal")
                elif status_code >= 2:
                    print("   ⚠️  Dispositivo com problemas operacionais")

            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_uptime(self):
        """Feature 1.7 - Ler uptime do dispositivo (1.7) - APENAS GET"""
        print("\n📡 A pedir uptime do dispositivo (1.7) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.7"]  # ⬅️ APENAS GET, sem SET
            )

            print(f"\n⏰ UPTIME DO DISPOSITIVO (1.7):")
            if response['v_list']:
                uptime = response['v_list'][0]
                print(f"   🔸 {uptime}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_date_time(self):
        """Feature 1.6 - Ler data e hora do dispositivo (1.6) - APENAS GET"""
        print("\n📡 A pedir data e hora do dispositivo (1.6) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.6"]  # ⬅️ APENAS GET
            )

            print(f"\n📅 DATA E HORA DO DISPOSITIVO (1.6):")
            if response['v_list']:
                datetime_str = response['v_list'][0]
                print(f"   🔸 {datetime_str}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_number_of_sensors(self):
        """Feature 1.5 - Ler número de sensores (1.5)"""
        print("\n   A pedir numero de sensores (1.5) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.5"]
            )

            print(f"\n NUMERO DE SENSORES (1.5):")
            if response['v_list']:
                num_sensors = response['v_list'][0]
                print(f"   🔸 {num_sensors} sensores")

                #Extra: Mostrar lista de sensores disponiveis
                if num_sensors > 0:
                    print(f"    Sensores disponíveis: {num_sensors}")
            else:
                print(f"    X Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_device_type(self):
        """Feature 1.3 - Ler apenas o tipo de dispositivo"""
        print("\n📡 A pedir tipo de dispositivo (1.3) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.3"]  # ⬅️ APENAS o IID 1.3
            )

            print(f"\n🏭 TIPO DE DISPOSITIVO (1.3):")
            if response['v_list']:
                device_type = response['v_list'][0]
                print(f"   🔸 {device_type}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_device_id(self):
        """Feature 1.2 - Ler apenas o ID do dispositivo (1.2)"""
        print("\n📡 A pedir ID do dispositivo (1.2) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.2"]  # ⬅️ APENAS o IID 1.2
            )

            print(f"\n🆔 ID DO DISPOSITIVO (1.2):")
            if response['v_list']:
                device_id = response['v_list'][0]
                print(f"   🔸 {device_id}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_lmib_id(self):
        """Feature 1.1 - Ler apenas o ID do L-MIB (1.1)"""
        print("\n   A pedir ID do L-MIB (1.1) via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.1"]
            )

            print(f"\n🏷️  ID DO L-MIB (1.1):")
            if response['v_list']:
                print(f"   🔸 {response['v_list'][0]}")
            else:
                print("   ❌ Nenhum valor retornado")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def get_device_info_complete(self):
        """Let todos os objetos do Device Group (1.1-1.9)"""
        print("\n A pedir informações completeas do dispositivo via UDP")

        try:
            #Pedir todos os objectos do device group (1.1 a 1.9)
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9"]
            )

            print("=" * 60)
            print(" INFORMAÇÕES COMPLETAS DO DISPOSITIVO")
            print("=" * 60)

            #Mapear IIDs para nomes descritivos
            device_info_map = {
                "1.1": "ID do L-MIB",
                "1.2": "ID do Dispositivo",
                "1.3": "Tipo de Dispositivo",
                "1.4": "Beacon Rate (segundos)",
                "1.5": "Número de Sensores",
                "1.6": "Data e Hora",
                "1.7": "Uptime",
                "1.8": "Status Operacional",
                "1.9": "Estado do Reset"
            }

            # Mostrar cada valor com descrição
            for iid, value in zip(response['iid_list'], response['v_list']):
                description = device_info_map.get(iid, iid)

                # Formatação especial para alguns valores
                if iid == "1.8":  # Status operacional
                    status_map = {0: "🟡 STANDBY", 1: "🟢 NORMAL", 2: "🔴 ERRO"}
                    status_text = status_map.get(value, f"🔴 ERRO ({value})")
                    print(f"   {description}: {status_text}")
                elif iid == "1.4":  # Beacon rate
                    if value == 0:
                        print(f"   {description}: 🔴 DESATIVADO")
                    else:
                        print(f"   {description}: 🟢 {value}s")
                elif iid == "1.9":  # Reset
                    if value == 0:
                        print(f"   {description}: 🟢 NORMAL")
                    else:
                        print(f"   {description}: 🔄 REINICIANDO")
                else:
                    print(f"   {description}: {value}")

            print("=" * 60)

        except socket.timeout:
            print("X Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"X Erro ao obter informações dos dispositivo: {e}")

    def read_all_sensors(self):
        """Via UDP para o Agent real"""
        print("\n📡 A pedir sensores via UDP...")

        try:
            response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["2.3.1", "2.3.2","2.3.3", "2.3.4","2.3.5", "2.3.6","2.3.7", "2.3.8",]
            )

            print("=" * 50)
            print("📦 PDU COMPLETE - RESPONSE:")
            print("=" * 50)
            print(f"🏷️  Tag: {response['tag']}")
            print(f"📨 Type: {response['type']}")
            print(f"⏰ Timestamp: {response['timestamp']}")
            print(f"🆔 MSG-ID: {response['msg_id']}")
            print(f"🔗 IID List: {response['iid_list']}")
            print(f"💾 Value List: {response['v_list']}")
            print(f"⏱️  T List: {response['t_list']}")
            print(f"❌ E List: {response['e_list']}")
            if response.get('remaining_data'):
                print(f"📎 Remaining Data: {response['remaining_data']}")
            print("=" * 50)

            print("\n📊 RESULTADOS DOS SENSORES:")
            for i, (iid, value) in enumerate(zip(response['iid_list'], response['v_list'])):
                print(f"   🔸 {iid}: {value}%")

        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

    def configure_beacon(self):
        """Configurar beacon rate via UDP"""
        try:
            rate = int(input("Novo beacon rate (segundos): "))
            response = self.udp_client.send_request(
                msg_type="set-request",
                iid_list=["1.4"],
                v_list=[rate]
            )
            print(f" Beacon rate configurado: {response['v_list'][0]}s")
        except Exception as e:
            print(f"X Erro: {e}")

    def configure_beacon_rate(self):
        """Feature 1.4 - Configurar beacon rate (1.4)"""
        try:
            #Primeiro ler o valor autal
            print("\n A ler beacon rate atual...")
            current_response = self.udp_client.send_request(
                msg_type="get-request",
                iid_list=["1.4"]
            )

            current_rate = current_response['v_list'][0] if current_response['v_list'] else "desconhecido"
            print(f"    Beaocn rate atual: {current_rate}s")

            # Pedir novo valor
            new_rate = int(input("\nNovo beacon rate (segundos, 0 para desativar):"))
            if new_rate < 0:
                print("X Erro: Valor deve ser >= 0")
                return

            #Enviar SER request
            print(f"    A configurar beacon rate para {new_rate}s...")
            set_response = self.udp_client.send_request(
                msg_type="set-request",
                iid_list=["1.4"],
                v_list=[new_rate]
            )

            print(f"  Beacon rate configurado para {new_rate}s")

        except ValueError:
            print("❌ Erro: Insira um número válido")
        except socket.timeout:
            print("❌ Timeout - Agent não respondeu!")
        except Exception as e:
            print(f"❌ Erro UDP: {e}")

if __name__ == "__main__":
    manager = LSNMPManager()
    manager.simple_ui()