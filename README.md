# L-SNMPvS Monitoring System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)

> **A lightweight, secure network monitoring system based on the L-SNMPvS protocol**, developed for the *Gestão e Segurança de Redes* course at the **University of Minho**.

---

## 📖 Overview

The **L-SNMPvS Monitoring System** is a complete implementation of the **Light Secure SNMP (L-SNMPvS)** protocol — a modern evolution of SNMP designed for **resource-constrained environments** such as IoT devices, embedded sensors, and home automation systems.

Traditional SNMP was built for powerful network equipment, but the rise of IoT has exposed its limitations: high computational overhead, complex MIB implementations, and weak security in early versions. **L-SNMPvS** addresses these challenges by keeping compatibility with traditional SNMP agents while introducing a complementary architecture optimized for constrained devices.

This project implements the full protocol stack in **Python**, including:

- ✅ A **custom binary encoding/decoding system** for L-SNMPvS PDUs
- ✅ A **UDP-based agent** (server) managing a virtual L-MIBvS
- ✅ A **graphical manager console** (Tkinter) for real-time monitoring
- ✅ **Virtual sensors** with configurable sampling rates
- ✅ **Symmetric encryption** (AES-ECB) for message confidentiality
- ✅ **Unsolicited beacons** for agent discovery
- ✅ **Asynchronous notifications** for sensor updates

---

## ✨ Features

### 🧩 Protocol Layer
- Full binary implementation of L-SNMPvS PDUs (`Tag`, `Type`, `Timestamp`, `MSG-ID`, `IID-list`, `V-list`, `T-list`, `E-list`)
- Custom encoding for IIDs, timestamps, values, and lists
- Automatic type detection for values (integers, strings, bytes, timestamps)

### 🖥️ Agent (UDP Server)
- Listens on **port 1161** for L-SNMPvS requests
- Manages the **L-MIBvS** (Device Group + Sensors Table)
- Handles `get-request`, `set-request`, `response`, and `notification` messages
- Broadcasts **beacons on port 1163** for network discovery
- Applies **AES-ECB encryption** to all main communications
- Runs asynchronous threads for beacons and sensor notifications

### 📊 Manager Console (GUI)
- Built with **Tkinter**
- Real-time sensor value visualization
- Send `get` and `set` requests to the agent
- Beacon dashboard with detection history
- Configurable agent address and ports

### 🌡️ Virtual Sensors
- Configurable `minValue`, `maxValue`, and `samplingRate`
- Unique IDs per sensor
- Simulated sensor types: Temperature, Humidity, Light, etc.

### 🔐 Security
- **Confidentiality**: AES-ECB symmetric encryption
- **Weak mutual authentication**: shared tuple of symmetric keys (K_A, K_M)
- **Unsigned beacons**: transmitted without security (as per spec)

---

## 🚀 How to Run

### Prerequisites

```bash
pip install pycryptodome
```

> Python 3.10 or higher is recommended.

### 1. Start the Agent (Server)

In one terminal, run:

```bash
python -m Agent.udp_server
```

The agent will:
- Bind to UDP port **1161** for L-SNMPvS requests
- Start broadcasting beacons on port **1163**
- Initialize the virtual sensors and the L-MIBvS
- Begin sending periodic sensor notifications

### 2. Start the Manager (GUI)

In another terminal, run:

```bash
python -m manager.LSNMPManagerGUI
```

The manager will:
- Open the graphical console
- Automatically listen for beacons on port **1163**
- Allow you to send `get` and `set` requests to the agent

> 💡 **Tip:** Make sure both processes can communicate on the same network (localhost works by default).

---

## 🏗️ Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Manager (GUI)     │         │   Agent (UDP)       │
│  LSNMPManagerGUI    │◄───────►│   udp_server        │
│                     │  :1161  │                     │
└─────────────────────┘         └──────────┬──────────┘
                                           │
                                           │ manages
                                           ▼
                                ┌─────────────────────┐
                                │     L-MIBvS         │
                                │  ┌───────────────┐  │
                                │  │ Device Group  │  │
                                │  ├───────────────┤  │
                                │  │ Sensors Table │  │
                                │  └───────────────┘  │
                                └──────────┬──────────┘
                                           │
                                           │ updates
                                           ▼
                                ┌─────────────────────┐
                                │  Virtual Sensors    │
                                │  (temperature,      │
                                │   humidity, light)  │
                                └─────────────────────┘
```

**Communication channels:**
- **Port 1161** → Main L-SNMPvS PDUs (encrypted)
- **Port 1163** → Unsigned beacons (discovery)

---

## 📁 Project Structure

```
lsnmpvs-monitoring-system/
│
├── Agent/
│   └── udp_server.py          # L-SNMPvS agent (server)
│
├── manager/
│   └── LSNMPManagerGUI.py     # Tkinter monitoring console
│
├── protocol/
│   └── ...                    # Encoding/decoding, PDUs, security
│
├── sensors/
│   └── ...                    # Virtual sensor implementations
│
└── README.md
```

---


## 🎯 Use Cases

- 📡 **IoT monitoring** in constrained networks
- 🔬 **Academic research** on network management protocols
- 🧪 **Protocol prototyping** for SNMP alternatives
- 🎓 **Teaching** network programming and secure communications

---

## ⚠️ Known Limitations

| Area | Limitation | Suggested Improvement |
|------|-----------|----------------------|
| 🔐 Security | Hard-coded symmetric key | Use key derivation + secure storage |
| 🔐 Security | No message integrity check | Add HMAC / hash validation |
| 🔐 Security | No key rotation | Implement periodic key renewal |
| 🌡️ Sensors | Basic random value generation | Add realistic patterns (trends, noise) |
| 🛠️ Errors | Basic error handling | Expand exception coverage |

These limitations are acknowledged in the project's critical analysis and represent clear opportunities for future work.

---

## 📚 References

1. [Net-SNMP Tutorial](http://net-snmp.sourceforge.net/wiki/index.php/Tutorials/)
2. [SimpleWeb](http://www.simpleweb.org/)
3. [SNMP Links](http://www.snmplinks.org/)
4. Rose, M. *The Simple Book*, 2nd Ed., Prentice Hall, 1996.
5. Stallings, W. *SNMP, SNMPv2, SNMPv3, and RMON 1 and 2*, Addison-Wesley, 2000.
6. Mauro, D., Schmidt, K. *Essential SNMP*, O'Reilly, 2001.
7. *Especificação do Trabalho Prático "Sensing with L-SNMPvS"*, Universidade do Minho, 2025.

---

## 👤 Author

**Ruben Magalhães** — PG56008
Master's in Computer Engineering — *Gestão e Segurança de Redes*
University of Minho · 2024/2025

---


<p align="center">
  <sub>⭐ If you find this project useful, consider giving it a star! ⭐</sub>
</p>
