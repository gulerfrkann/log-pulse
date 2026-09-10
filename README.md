# LogPulse

LogPulse, gerçek zamanlı log izleme, yapay zeka destekli kök neden analizi (RCA), otonom iyileştirme (self-healing) aksiyonları ve anlık masaüstü bildirimleri gerçekleştiren otonom bir DevOps ve sistem yönetim ajanıdır. Go, RabbitMQ, Python, Docker SDK ve Google Gemini API kullanılarak geliştirilmiştir.

---

##  Mimari ve İş Akışı

1. **Log Üretici (Go)**: Mikroservis log simülasyonu yapar (normal operasyonlar ve anomali hataları) ve bunları mesaj kuyruğuna yayınlar.
2. **Mesaj Broker (RabbitMQ)**: Sistem loglarının güvenilir bir şekilde kuyruklanmasını ve adil bir şekilde dağıtılmasını sağlar.
3. **Yapay Zeka Tüketicisi ve Ajan (Python)**: Logları RabbitMQ'dan tüketir, sistem metriklerini (CPU/Bellek) değerlendirir ve anomali durumlarında Gemini API ile iletişime geçer.
4. **Otonom İyileştirme (Docker SDK)**: Gerçek zamanlı yapay zeka teşhisine dayanarak konteyner kurtarma aksiyonlarını (bozulmuş veya çökmüş servisleri yeniden başlatma gibi) otomatik olarak tetikler.
5. **Masaüstü Bildirimleri (Plyer)**: Otonom bir iyileştirme aksiyonu başarıyla gerçekleştirildiğinde yerel Windows bildirimleri aracılığıyla operatörleri anında bilgilendirir.

---

##  Teknoloji Yığını

* **Dil (Üretici):** Go
* **Dil (Tüketici / Yapay Zeka Ajanı):** Python
* **Mesaj Broker:** RabbitMQ
* **Konteyner Yönetimi:** Docker & Docker SDK for Python
* **Yapay Zeka:** Google Gemini API (`gemini-3.5-flash`)
* **Masaüstü Bildirimleri:** `plyer`
* **Ortam Yönetimi:** `python-dotenv`, `pika`

---

##  Başlangıç

### Gereksinimler

* Go (1.18+)
* Python (3.9+)
* Docker & Docker Compose
* Gemini API Anahtarı

### 1. Repoyu Klonlayın

```bash
git clone [https://github.com/gulerfrkann/log-pulse.git](https://github.com/gulerfrkann/log-pulse.git)
cd log-pulse