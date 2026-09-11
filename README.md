# LogPulse

LogPulse; gerçek zamanlı log izleme, yapay zeka destekli kök neden analizi (RCA), vektör tabanlı epizodik hafıza (RAG), ilişkisel sistem telemetrisi ve insan onay mekanizması (Human-in-the-Loop) barındıran kurumsal düzeyde bir AIOps platformudur. 

Go, RabbitMQ, Python, PostgreSQL, Qdrant, Docker SDK ve Google Gemini API kullanılarak dağıtık mimaride geliştirilmiştir.

---

## Mimari ve İş Akışı

1. **Log Üretici & Metrik Simülatörü (Go)**: Mikroservis loglarını ve donanım telemetrisini (CPU, bellek) simüle ederek RabbitMQ kuyruğuna aktarır.
2. **Mesaj Kuyruğu (RabbitMQ)**: Dağıtık servis loglarının kayıpsız ve asenkron iletimini sağlar.
3. **İlişkisel Telemetri Katmanı (PostgreSQL)**: Servis konfigürasyonlarını, donanım limitlerini, zaman serisi hata sıklıklarını (`incident_logs`) ve operatör denetim izlerini (`remediation_audits`) saklar.
4. **Hibrit Akıllı Ajan (Python & Gemini & Qdrant)**:
   - **Vektör Hafızası (RAG):** Qdrant üzerinde anlamsal arama yaparak geçmiş benzer çözümleri çeker.
   - **İlişkisel Sistem Grafı:** PostgreSQL üzerinden servis limitlerini ve son 1 saatteki hata frekansını sorgular (`JOIN`).
   - Çok boyutlu bağlam ile Gemini üzerinden kök neden tespiti yapar.
5. **İnsan Onay Mekanizması (Human-in-the-Loop)**: Kritik aksiyonlar doğrudan uygulanmaz; FastAPI ve Tailwind CSS tabanlı dashboard üzerinden operatör onayına sunulur.
6. **Denetim İzi & Otonom İyileştirme (Docker SDK)**: Operatör onayı sonrası konteyner operasyonları icra edilir ve sonuçlar PostgreSQL denetim tablosuna işlenir.

---

## Teknoloji Yığını

* **Diller:** Go, Python, SQL
* **İlişkisel Veritabanı:** PostgreSQL (Zaman serisi telemetri & Denetim izi)
* **Vektör Veritabanı:** Qdrant (RAG Hafıza Yönetimi)
* **Mesaj Broker:** RabbitMQ
* **Web Arayüzü & API:** FastAPI, Tailwind CSS, Chart.js
* **Konteyner Orkestrasyonu:** Docker & Docker SDK for Python
* **Yapay Zeka:** Google Gemini API (`gemini-2.5-flash`), `sentence-transformers`

---

## Kurulum ve Başlangıç

### Gereksinimler

* Docker & Docker Compose
* Go (1.18+)
* Python (3.9+)

### 1. Altyapı Konteynerlerini Başlatın

```bash
# Qdrant ve RabbitMQ konteynerlerinin yanında PostgreSQL'i başlatın
docker run -d --name logpulse-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=logpulse -p 5432:5432 postgres:15