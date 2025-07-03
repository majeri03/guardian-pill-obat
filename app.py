import json
import ssl
import threading
import random  # <-- PERBAIKAN: Tambahkan import ini
from datetime import datetime
from collections import defaultdict

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template

# --- Konfigurasi MQTT (harus sama dengan publisher) ---
BROKER_ADDRESS = "broker.hivemq.com"
BROKER_PORT = 8883
MQTT_USER = "guardian_user"
MQTT_PASS = "GuardianPill123!"
MQTT_TOPIC = "guardianpill/#"  # Wildcard untuk subscribe ke semua pasien

# --- Penyimpanan Data In-Memory ---
# Dictionary untuk menyimpan data terbaru dan riwayat kepatuhan
# defaultdict digunakan agar tidak perlu cek key sudah ada atau belum
patient_data = defaultdict(lambda: {
    "patient_id": "",
    "patient_name": "",
    "schedules": {"Pagi": "menunggu", "Siang": "menunggu", "Malam": "menunggu"},
    "compliance_history": {"diambil": 0, "terlewat": 0}
})
data_lock = threading.Lock() # Untuk mencegah race condition saat update data

# --- Inisialisasi Aplikasi Flask ---
app = Flask(__name__)

# --- Logika Subscriber MQTT ---
def on_connect(client, userdata, flags, rc):
    """Callback saat koneksi ke broker berhasil."""
    if rc == 0:
        print("Subscriber berhasil terhubung ke Broker MQTT via TLS/SSL.")
        client.subscribe(MQTT_TOPIC)
        print(f"Berlangganan ke topik: {MQTT_TOPIC}")
    else:
        print(f"Gagal terhubung ke broker, kode: {rc}")

def on_message(client, userdata, msg):
    """Callback saat pesan dari MQTT diterima."""
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        # Validasi input sederhana di sisi subscriber
        required_keys = ["patient_id", "patient_name", "schedule", "status"]
        if not all(key in payload for key in required_keys):
            print(f"[VALIDATION_ERROR] Pesan tidak lengkap diterima: {payload}")
            return

        patient_id = payload["patient_id"]
        schedule = payload["schedule"]
        status = payload["status"]

        # Mengunci data untuk update agar aman dari akses thread lain
        with data_lock:
            # Update data utama pasien
            current_patient = patient_data[patient_id]
            current_patient["patient_id"] = patient_id
            current_patient["patient_name"] = payload["patient_name"]
            
            # Cek apakah status berubah untuk menghitung riwayat kepatuhan
            old_status = current_patient["schedules"].get(schedule)
            if old_status and old_status != status:
                # Kurangi hitungan lama jika statusnya bukan 'menunggu'
                if old_status in current_patient["compliance_history"]:
                    current_patient["compliance_history"][old_status] = max(0, current_patient["compliance_history"][old_status] - 1)
                # Tambah hitungan baru
                if status in current_patient["compliance_history"]:
                    current_patient["compliance_history"][status] += 1
            elif not old_status and status in current_patient["compliance_history"]:
                 current_patient["compliance_history"][status] += 1


            current_patient["schedules"][schedule] = status


        print(f"[{datetime.now().strftime('%H:%M:%S')}] RECEIVED: Status {patient_id} ({schedule}) -> {status}")

    except json.JSONDecodeError:
        print(f"Error: Gagal decode JSON dari topik {msg.topic}")
    except Exception as e:
        print(f"Error saat proses pesan: {e}")

def run_mqtt_subscriber():
    """Menjalankan listener MQTT di thread terpisah."""
    client = mqtt.Client(client_id=f"subscriber-{random.randint(1000, 9999)}")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    client.loop_forever()

# --- Rute Aplikasi Web (Flask) ---
@app.route('/')
def dashboard():
    """Menampilkan halaman utama dashboard."""
    return render_template('index.html')

@app.route('/data')
def get_data():
    """API endpoint untuk menyediakan data ke frontend."""
    with data_lock:
        # Mengubah defaultdict menjadi dict biasa untuk serialisasi JSON
        data_to_send = dict(patient_data)
    return jsonify(data_to_send)

if __name__ == '__main__':
    # Menjalankan subscriber MQTT di background thread
    mqtt_thread = threading.Thread(target=run_mqtt_subscriber, daemon=True)
    mqtt_thread.start()
    
    # Menjalankan aplikasi web Flask
    print("Menjalankan Dashboard Web di http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
