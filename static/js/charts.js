document.addEventListener('DOMContentLoaded', function () {
    // Objek untuk menyimpan semua instance Chart.js agar bisa diupdate
    const chartInstances = {};
    const POLLING_INTERVAL = 3000; // Ambil data setiap 3 detik

    // Konfigurasi default untuk semua grafik
    Chart.defaults.color = '#a9a9b3';
    Chart.defaults.font.family = 'Inter, sans-serif';

    /**
     * Fungsi utama untuk mengambil data dari backend dan memperbarui seluruh UI.
     */
    async function fetchDataAndUpdate() {
        try {
            const response = await fetch('/data');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            updateConnectionStatus(true);
            updateGlobalSummary(data);
            updateGlobalComplianceChart(data);
            updatePatientGrid(data);

        } catch (error) {
            console.error("Gagal mengambil data dari server:", error);
            updateConnectionStatus(false, "Error");
        }
    }

    /**
     * Memperbarui indikator status koneksi.
     */
    function updateConnectionStatus(isConnected, message = "Terhubung") {
        const statusDot = document.querySelector('.status-indicator .dot');
        const statusText = document.getElementById('connection-status');
        
        statusText.textContent = message;
        if (isConnected) {
            statusDot.className = 'dot connected';
        } else {
            statusDot.className = 'dot error';
        }
    }

    /**
     * Memperbarui kartu ringkasan global di bagian atas.
     */
    function updateGlobalSummary(data) {
        const patientIds = Object.keys(data);
        document.getElementById('total-patients').textContent = patientIds.length;

        let totalTaken = 0;
        let totalMissed = 0;

        patientIds.forEach(id => {
            const history = data[id].compliance_history;
            totalTaken += history.diambil;
            totalMissed += history.terlewat;
        });
        
        document.getElementById('total-missed').textContent = totalMissed;
        
        const totalEvents = totalTaken + totalMissed;
        const globalCompliance = totalEvents > 0 ? ((totalTaken / totalEvents) * 100).toFixed(1) : 0;
        document.getElementById('global-compliance').textContent = `${globalCompliance} %`;
    }

    /**
     * Membuat atau memperbarui grafik batang global untuk perbandingan kepatuhan.
     */
    function updateGlobalComplianceChart(data) {
        const ctx = document.getElementById('globalComplianceChart').getContext('2d');
        const patientNames = Object.values(data).map(p => p.patient_name);
        const complianceData = Object.values(data).map(p => {
            const history = p.compliance_history;
            const total = history.diambil + history.terlewat;
            return total > 0 ? (history.diambil / total) * 100 : 0;
        });

        if (chartInstances.global) {
            // Update data jika grafik sudah ada
            chartInstances.global.data.labels = patientNames;
            chartInstances.global.data.datasets[0].data = complianceData;
            chartInstances.global.update();
        } else {
            // Buat grafik baru jika belum ada
            chartInstances.global = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: patientNames,
                    datasets: [{
                        label: 'Tingkat Kepatuhan (%)',
                        data: complianceData,
                        backgroundColor: 'rgba(74, 144, 226, 0.6)',
                        borderColor: 'rgba(74, 144, 226, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) { return value + "%" }
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
    }

    /**
     * Membuat atau memperbarui semua kartu pasien di grid.
     */
    function updatePatientGrid(data) {
        const grid = document.getElementById('patient-grid');
        const patientIds = Object.keys(data);

        // Hapus pasien yang tidak ada lagi di data (jika ada)
        // ... (opsional untuk kasus ini)

        patientIds.forEach(id => {
            const patient = data[id];
            let card = document.getElementById(`card-${id}`);
            if (!card) {
                card = createPatientCard(id, patient.patient_name);
                grid.appendChild(card);
            }
            updatePatientCardContent(card, patient);
        });
    }

    /**
     * Membuat elemen HTML untuk satu kartu pasien.
     */
    function createPatientCard(id, name) {
        const card = document.createElement('div');
        card.className = 'patient-card';
        card.id = `card-${id}`;
        card.innerHTML = `
            <div class="patient-header">
                <h4>${name}</h4>
                <span class="compliance-score">-%</span>
            </div>
            <div class="schedule-status-container">
                <div class="schedule-status">
                    <div class="label">Pagi</div>
                    <div class="status" data-schedule="Pagi">menunggu</div>
                </div>
                <div class="schedule-status">
                    <div class="label">Siang</div>
                    <div class="status" data-schedule="Siang">menunggu</div>
                </div>
                <div class="schedule-status">
                    <div class="label">Malam</div>
                    <div class="status" data-schedule="Malam">menunggu</div>
                </div>
            </div>
            <div class="patient-chart-container">
                <canvas id="chart-${id}"></canvas>
            </div>
        `;
        return card;
    }

    /**
     * Memperbarui konten di dalam satu kartu pasien.
     */
    function updatePatientCardContent(card, patient) {
        // Update status Pagi, Siang, Malam
        card.querySelectorAll('.status').forEach(el => {
            const schedule = el.dataset.schedule;
            const status = patient.schedules[schedule] || 'menunggu';
            el.textContent = status;
            el.className = `status ${status}`;
        });

        // Update skor kepatuhan
        const history = patient.compliance_history;
        const total = history.diambil + history.terlewat;
        const compliance = total > 0 ? (history.diambil / total) * 100 : 0;
        const complianceEl = card.querySelector('.compliance-score');
        complianceEl.textContent = `${compliance.toFixed(0)}%`;
        
        if(compliance >= 80) complianceEl.className = 'compliance-score good';
        else if (compliance >= 50) complianceEl.className = 'compliance-score medium';
        else complianceEl.className = 'compliance-score bad';


        // Update grafik donat per pasien
        const chartCtx = card.querySelector('canvas').getContext('2d');
        const chartId = `chart-${patient.patient_id}`;
        
        if (chartInstances[chartId]) {
            chartInstances[chartId].data.datasets[0].data = [history.diambil, history.terlewat];
            chartInstances[chartId].update();
        } else {
            chartInstances[chartId] = new Chart(chartCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Diambil', 'Terlewat'],
                    datasets: [{
                        data: [history.diambil, history.terlewat],
                        backgroundColor: [
                            'rgba(52, 211, 153, 0.7)', // Hijau
                            'rgba(230, 0, 122, 0.7)'   // Magenta
                        ],
                        borderColor: [
                            'rgba(52, 211, 153, 1)',
                            'rgba(230, 0, 122, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 10,
                                boxWidth: 12
                            }
                        }
                    }
                }
            });
        }
    }

    // Mulai polling data
    fetchDataAndUpdate(); // Panggil sekali saat load
    setInterval(fetchDataAndUpdate, POLLING_INTERVAL);
});
