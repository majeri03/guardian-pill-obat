import paho.mqtt.client as mqtt
import time
import json
import random
import ssl
from datetime import datetime

# --- Konfigurasi MQTT ---
# Gunakan broker publik HiveMQ yang mendukung TLS/SSL di port 8883
BROKER_ADDRESS = "broker.hivemq.com"
BROKER_PORT = 8883

# --- Keamanan (Sesuai Tugas) ---
# Ganti dengan username & password Anda sendiri jika diperlukan,
# atau gunakan ini untuk pengujian.
MQTT_USER = "guardian_user"
MQTT_PASS = "GuardianPill123!"

# --- Data Dummy Pasien ---
PATIENTS = [
    {"id": "patient001", "name": "Nenek Aminah"},
    {"id": "patient002", "name": "Kakek Budi"},
    {"id": "patient003", "name": "Ibu Siti"},
    {"id": "patient004", "name": "Bapak Joko"}
]

SCHEDULES = ["Pagi", "Siang", "Malam"]
STATUS_CHOICES = ["diambil", "terlewat", "menunggu"]

def on_connect(client, userdata, flags, rc):
    """Callback yang dipanggil saat koneksi ke broker berhasil."""
    if rc == 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Publisher terhubung ke Broker MQTT via TLS/SSL.")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Gagal terhubung, kode: {rc}. Cek username/password atau koneksi.")
        if rc == 5:
            print("Error: Not authorised. Pastikan username dan password benar.")

def create_dummy_event():
    """Membuat satu event data dummy seolah-olah dari kotak obat."""
    patient = random.choice(PATIENTS)
    schedule = random.choice(SCHEDULES)
    
    # Validasi Input Sederhana: Memastikan status valid
    status = random.choices(STATUS_CHOICES, weights=[0.6, 0.2, 0.2], k=1)[0]
    if status not in STATUS_CHOICES:
        print(f"[VALIDATION_ERROR] Status tidak valid: {status}. Menggunakan 'menunggu'.")
        status = "menunggu"

    payload = {
        "patient_id": patient["id"],
        "patient_name": patient["name"],
        "schedule": schedule,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    return payload

def run_publisher():
    """Fungsi utama untuk menjalankan publisher."""
    client = mqtt.Client(client_id=f"publisher-{random.randint(1000, 9999)}")
    
    # --- Implementasi Keamanan ---
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    
    client.on_connect = on_connect

    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    except Exception as e:
        print(f"Error koneksi ke broker: {e}")
        return

    client.loop_start()
    print("Publisher simulasi IoT dimulai. Mengirim data setiap beberapa detik...")
    print("-" * 30)

    try:
        while True:
            event_data = create_dummy_event()
            topic = f"guardianpill/{event_data['patient_id']}/events"
            
            # Publish data sebagai JSON string
            client.publish(topic, json.dumps(event_data), qos=1)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] PUBLISH ke '{topic}': {event_data['status']} untuk {event_data['patient_name']} ({event_data['schedule']})")
            
            time.sleep(random.uniform(2, 5)) # Kirim data dalam interval acak
            
    except KeyboardInterrupt:
        print("\nPublisher dihentikan oleh pengguna.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Koneksi MQTT publisher diputus.")

if __name__ == "__main__":
    run_publisher()
