# LogPulse

LogPulse, gerçek zamanlı log izleme, yapay zeka destekli kök neden analizi, otonom iyileştirme aksiyonları, vektör tabanlı hafıza yönetimi ve insan onay mekanizması gerçekleştiren otonom bir DevOps ve sistem yönetim ajanıdır. Go, RabbitMQ, Python, Qdrant, Docker SDK ve Google Gemini API kullanılarak geliştirilmiştir.

---

## Mimari ve İş Akışı

1. **Log Üretici (Go)**: Mikroservis log simülasyonu yapar ve bunları mesaj kuyruğuna yayınlar.
2. **Mesaj Broker (RabbitMQ)**: Sistem loglarının güvenilir bir şekilde kuyruklanmasını ve dağıtılmasını sağlar.
3. **Yapay Zeka Tüketicisi ve Ajan (Python)**: Logları tüketir, Qdrant vektör veritabanı üzerinden geçmiş benzer vakaları sorgular (RAG) ve Gemini API ile bağlam odaklı analiz üretir.
4. **İnsan Onay Mekanizması (Human-in-the-Loop)**: Kritik iyileştirme aksiyonları doğrudan tetiklenmek yerine web tabanlı arayüz üzerinden operatör onayına sunulur.
5. **Otonom İyileştirme (Docker SDK)**: Onaylanan veya tetiklenen kararlar doğrultusunda konteyner kurtarma operasyonlarını gerçekleştirir ve sonuçları hafızaya kaydeder.

---

## Teknoloji Yığını

* **Dil (Üretici):** Go
* **Dil (Tüketici / Ajan):** Python
* **Web Arayüzü / Sunucu:** FastAPI, Tailwind CSS
* **Vektör Veritabanı (RAG):** Qdrant
* **Mesaj Broker:** RabbitMQ
* **Konteyner Yönetimi:** Docker & Docker SDK for Python
* **Yapay Zeka:** Google Gemini API
* **Ortam Yönetimi:** `python-dotenv`, `pika`, `sentence-transformers`

---

## Başlangıç

### Gereksinimler

* Go (1.18+)
* Python (3.9+)
* Docker & Docker Compose
* Qdrant
* Gemini API Anahtarı

### 1. Repoyu Klonlayın

```bash
git clone [https://github.com/gulerfrkann/log-pulse.git](https://github.com/gulerfrkann/log-pulse.git)
cd log-pulse