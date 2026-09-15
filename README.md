# LogPulse - Autonomous AIOps & Predictive Telemetry Orchestrator

LogPulse; mikroservis ekosistemlerinde telemetri akışını izleyen, zaman serisi üzerinde kayan pencere (sliding-window) OLS regresyonu koşturarak bellek sızıntılarını servis çökmeden (OOM) önce tespit eden, PostgreSQL ilişkisel sistem grafı ve Qdrant vektör hafızasını (RAG) harmanlayarak çok boyutlu kök neden analizi (RCA) üreten ve otonom iyileştirmeleri insan onay süzgecinden (Human-in-the-Loop) geçiren kurumsal düzeyde bir AIOps platformudur.

---

##  Mimari ve Veri Akışı

```text
[ Go Producer / Telemetry Simulator ]
        │ (Kademeli Bellek Sızıntısı & CPU/RAM Telemetrisi)
        ▼
[ RabbitMQ Broker ]
        │ (Asenkron & Güvenilir Mesaj İletimi)
        ▼
[ Python AI Agent / SRE Controller ]
   ├── Predictive Detector ──────► Sliding-Window OLS Regression (Eğim / Slope Hesabı)
   ├── Qdrant Vector DB ─────────► Epizodik Hafıza (RAG - Cosine Similarity)
   ├── PostgreSQL Telemetry ─────► İlişkisel Sistem Grafı (Donanım Limitleri, Hata Sıklığı, Denetim İzi)
   └── Google Gemini API ────────► Gemini 3.6 Flash Çok Boyutlu Kök Neden Analizi (RCA)
        │
        ▼
[ FastAPI Control Plane & Dashboard ]
   ├── Predictive Warning Card ──► Sarı Yanıp Sönen Erken Uyarı & Time-to-OOM Projeksiyonu
   ├── Chart.js Dynamic Visualizer ──► Anlık Çift Eksenli CPU / Bellek Takibi
   └── Operator HITL Console ────────► Operatör Onayı -> Docker SDK Tetikleme -> Audit Kaydı
   
### Temel Yetenekler

* **Dağıtık Telemetri Simülatörü (Go):** Mikroservis yüklerini simüle ederek CPU ve bellek metriklerini RabbitMQ kuyruğuna aktarır; bellek sızıntısı paternlerini kademeli olarak üretir.
* **Kestirimci Bakım (Sliding-Window OLS Regression):** Çöküşü beklemek yerine son 5 ölçümün doğrusal eğimini ($\beta$) hesaplar; eşik aşıldığında tahmini çöküş süresini (Time-to-OOM) belirleyerek erken uyarı fırlatır.
* **İlişkisel Telemetri Katmanı (PostgreSQL):** Servis donanım limitlerini (`services`), zaman serisi hatalarını (`incident_logs`) ve operatör müdahalelerini (`remediation_audits`) tek bir ilişkisel modelde birleştirir.
* **Vektör Hafızası (Qdrant RAG):** Başarılı operasyonel çözümleri `all-MiniLM-L6-v2` embedding modeli ile anlamsal hafızaya kaydeder ve gelecekteki benzer vakalarda ajana bağlam olarak sunar.
* **İnsan Onay Mekanizması (Human-in-the-Loop):** Kritik altyapı aksiyonları doğrudan icra edilmez; operatörün web paneli üzerinden onaylaması beklenir ve her eylem denetim tablosuna işlenir.
* **Gerçek Zamanlı Gözlemlenebilirlik:** Çift eksenli Chart.js grafiği ile donanım tüketimi izlenir; `PREDICT_WARN` anında sarı erken uyarı paneli devreye girer.

---

##  Teknoloji Yığını

* **Sistem & Backend:** Go, Python, SQL
* **İlişkisel Veritabanı:** PostgreSQL 15
* **Vektör Veritabanı:** Qdrant (Distance: Cosine, Vector Size: 384)
* **Mesaj Broker:** RabbitMQ
* **Web Arayüzü & API:** FastAPI, Tailwind CSS, Chart.js
* **Altyapı & Orkestrasyon:** Docker & Docker SDK for Python
* **Yapay Zeka & Embedding:** Google Gemini API (`gemini-3.6-flash`), `sentence-transformers`

---

##  Veritabanı Şeması (PostgreSQL DDL)

```sql
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    max_memory_mb INT NOT NULL DEFAULT 512,
    max_cpu_percent FLOAT NOT NULL DEFAULT 80.0,
    healthcheck_url VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'critical'
);

CREATE TABLE IF NOT EXISTS incident_logs (
    id SERIAL PRIMARY KEY,
    service_id INT REFERENCES services(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    cpu_usage FLOAT NOT NULL,
    memory_usage FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS remediation_audits (
    id SERIAL PRIMARY KEY,
    incident_id INT REFERENCES incident_logs(id) ON DELETE SET NULL,
    service_id INT REFERENCES services(id) ON DELETE CASCADE,
    action_taken VARCHAR(100) NOT NULL,
    approved_by VARCHAR(50) DEFAULT 'operator_admin',
    execution_status VARCHAR(20) DEFAULT 'SUCCESS',
    resolution_time_sec FLOAT DEFAULT 1.2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);