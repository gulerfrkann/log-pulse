import os
import json
import pika
import docker
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from plyer import notification
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from detector import PredictiveAnomalyDetector
from db import log_incident_and_get_context

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.6-flash")
DASHBOARD_API_URL = "http://localhost:8000/api/logs"

# Proaktif Anomali ve Bellek Sızıntısı Detektörü (Global Tanım)
anomaly_detector = PredictiveAnomalyDetector(window_size=5, slope_threshold=1.2, mem_critical_threshold=75.0)

# Qdrant ve Embedding Modeli (RAG Vektör Hafızası)
try:
    qdrant_client = QdrantClient(host="localhost", port=6333)
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    COLLECTION_NAME = "logpulse_memory"
    
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
        )
    print("[QDRANT] RAG Hafıza sistemi aktif.")
except Exception as e:
    print(f"[UYARI] Qdrant bağlantısı kurulamadı: {e}")
    qdrant_client = None
    embedder = None

# Docker İstemcisi
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"[UYARI] Docker bağlantısı kurulamadı: {e}")
    docker_client = None

def send_windows_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='LogPulse AI Agent',
            timeout=5
        )
    except Exception as e:
        print(f"[HATA] Windows bildirimi gösterilemedi: {e}")

def send_to_dashboard(log_data, ai_analysis=None):
    payload = {
        "service": log_data.get("service", "unknown-service"),
        "level": log_data.get("level", "INFO"),
        "message": log_data.get("message", ""),
        "cpu_usage": log_data.get("cpu_usage", 0.0),
        "memory_usage": log_data.get("memory_usage", 0.0),
        "ai_analysis": ai_analysis
    }
    try:
        requests.post(DASHBOARD_API_URL, json=payload, timeout=2)
    except Exception:
        pass

def search_memory(error_message):
    if not qdrant_client or not embedder:
        return []
    try:
        vector = embedder.encode(error_message).tolist()
        
        # Yeni Qdrant API: query_points metodu kullanılır
        response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=2
        )
        memories = []
        for hit in response.points:
            if hit.score and hit.score > 0.70:
                payload = hit.payload or {}
                memories.append(f"- Geçmiş Hata: {payload.get('message')} | Çözüm: {payload.get('solution')}")
        return memories
    except Exception as e:
        print(f"[HATA] Hafıza sorgulanırken hata oluştu: {e}")
        return []
        
def save_memory(error_message, solution_text):
    if not qdrant_client or not embedder:
        return
    try:
        vector = embedder.encode(error_message).tolist()
        count_res = qdrant_client.count(collection_name=COLLECTION_NAME)
        point_id = count_res.count + 1
        
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"message": error_message, "solution": solution_text}
                )
            ]
        )
        print("[QDRANT] Çözüm deneyimi vektör hafızasına kaydedildi.")
    except Exception as e:
        print(f"[HATA] Hafızaya kayıt yapılamadı: {e}")

def analyze_log_with_ai(log_data):
    log_level = log_data.get("level", "INFO")
    message = log_data.get("message", "")
    service = log_data.get("service", "unknown-service")
    cpu = log_data.get("cpu_usage", 0.0)
    memory = log_data.get("memory_usage", 0.0)

    print(f"\n[CONSUMER] Log Alındı -> Servis: {service} | Seviye: {log_level} | CPU: %{cpu} | RAM: %{memory}")

    # 1. Proaktif Kestirimci Anomali Kontrolü (Sliding Window OLS Eğim Analizi)
    anomaly_result = anomaly_detector.evaluate_telemetry(service, memory)
    if anomaly_result["is_anomaly"]:
        print(f"\n🚨 [PROAKTİF TAHMİN] {service} üzerinde bellek sızıntısı (Memory Leak) tespit edildi!")
        print(f"📈 Artış Eğimi: +%{anomaly_result['slope']}/adım | Anlık RAM: %{anomaly_result['current_memory']}")
        print(f"⏳ Tahmini OOM Süresi: Yaklaşık {anomaly_result['steps_to_oom']} adım sonra!")

        proactive_prompt = f"""
Sen LogPulse otonom SRE ajanısın. Servis henüz ÇÖKMEMİŞTİR ancak kayan pencere (sliding window) regresyon analizi ile deterministik bir BELLEK SIZINTISI (Memory Leak) tespit edildi.

[PROAKTİF TELEMETRİ METRİKLERİ]
- Servis: {service}
- Anlık Bellek Tüketimi: %{anomaly_result['current_memory']}
- Bellek Artış Eğimi (Slope): +%{anomaly_result['slope']} birim/ölçüm
- Son 5 Ölçüm Geçmişi: {anomaly_result['history']}
- Tahmini OOM (Out-of-Memory) Çöküş Eşiği: Yaklaşık {anomaly_result['steps_to_oom']} adım sonra

Sistem OOM killer tarafından kilitlenmeden önce operatöre acil proaktif önlem planı üret:
1. Tahmini Kök Neden: (Bellek neden düzenli birikiyor?)
2. Proaktif İyileştirme (Preventive Action): (Graceful restart, connection pool drain veya GC tetikleme planı)
"""
        try:
            response = model.generate_content(proactive_prompt)
            proactive_analysis = f" [PROAKTİF UYARI - ÇÖKME ÖNLENDİ]\n{response.text}"
            print("\n---  GEMINI PROAKTİF KESTİRİMCİ RAPORU ---")
            print(proactive_analysis)
            print("-------------------------------------------\n")

            predictive_log = dict(log_data)
            predictive_log["level"] = "PREDICT_WARN"
            predictive_log["message"] = f"Proaktif Uyarı: Bellek sızıntısı eğilimi! Tahmini OOM: ~{anomaly_result['steps_to_oom']} adım."
            send_to_dashboard(predictive_log, ai_analysis=proactive_analysis)

            send_windows_notification(
                title=f" Proaktif Anomali: {service}",
                message=f"Bellek sızıntısı tespit edildi! Servis çökmeden müdahale öneriliyor."
            )
            return
        except Exception as e:
            print(f"[PROAKTİF ANALİZ HATA] {e}")

    # Normal akış: Hata yoksa ve anomali görülmediyse analiz atlanır
    if log_level == "INFO":
        print("[AI BYPASS] Normal işlem logu, telemetri stabil.")
        send_to_dashboard(log_data, ai_analysis=None)
        return

    # 2. PostgreSQL Çok Tablolu İlişkisel Bağlamı (JOIN) Çek
    db_context_text = "Veritabanı ilişkisel bağlamı alınamadı."
    try:
        incident_id, context = log_incident_and_get_context(
            service_name=service,
            level=log_level,
            message=message,
            cpu=cpu,
            memory=memory
        )
        db_context_text = f"""- Servis Katmanı (Tier): {context.get('tier')}
- Donanım Limitleri: Maksimum Bellek {context.get('max_memory_mb')}MB | Kritik CPU Eşiği %{context.get('max_cpu_percent')}
- Son 1 Saatteki Toplam Hata Sayısı: {context.get('total_incidents_last_hour')}
- En Son Operatör Müdahalesi: {context.get('last_remediation_action') or 'Yok'} (Onaylayan: {context.get('last_operator') or 'N/A'}, Durum: {context.get('last_remediation_status') or 'N/A'})"""
    except Exception as e:
        print(f"[DB UYARI] PostgreSQL kayıt/bağlam hatası: {e}")

    # 3. Qdrant Vektör Hafızasını Tara (RAG)
    past_memories = search_memory(message)
    memory_context = "\n".join(past_memories) if past_memories else "Benzer bir geçmiş vaka bulunamadı (İlk kayıt)."

    # 4. İlişkisel Graf + Vektör Hafızası ile Hibrit Prompt Oluştur
    prompt = f"""
Sen LogPulse otonom AIOps ajanısın. Hem uzun vadeli vektör hafızasına (Qdrant RAG) hem de kurumsal ilişkisel sistem veritabanına (PostgreSQL) erişimin var.

[SİSTEM İLİŞKİSEL GRAF & TELEMETRİ BAĞLAMI]
{db_context_text}

[QDRANT RAG HAFIZA KAYITLARI]
{memory_context}

[GÜNCEL HATA TELEMETRİSİ]
- Servis: {service}
- Hata Seviyesi: {log_level}
- Mesaj: {message}
- Anlık CPU Tüketimi: %{cpu}
- Anlık Bellek Tüketimi: %{memory}

Yukarıdaki donanım eşiklerini, son 1 saatteki hata sıklığını ve geçmiş müdahaleleri analiz ederek şu formatta yanıt üret:
1. Kök Neden (Root Cause): (Hatanın donanım limiti, bellek sızıntısı veya kod bazlı teknik nedeni)
2. Önerilen Aksiyon (Suggested Action): (Docker API veya sistem seviyesinde operatör onayına sunulacak kurtarma adımı)
"""

    print("[AI ANALİZ] İlişkisel sistem grafı ve RAG bağlamı Gemini API'ye iletiliyor...")
    try:
        response = model.generate_content(prompt)
        ai_analysis_text = response.text
        print("\n--- 🤖 GEMINI İLİŞKİSEL & RAG ANALİZİ ---")
        print(ai_analysis_text)
        print("----------------------------------------\n")
        
        send_to_dashboard(log_data, ai_analysis=ai_analysis_text)

        send_windows_notification(
            title=f" LogPulse Olayı: {service}",
            message="Hata frekansı değerlendirildi. İnsan onayı bekleniyor!"
        )

        save_memory(message, ai_analysis_text)
            
    except Exception as e:
        print(f"Gemini API hatası: {e}")
        send_to_dashboard(log_data, ai_analysis=f"Analiz hatası: {e}")

def callback(ch, method, properties, body):
    try:
        log_data = json.loads(body.decode('utf-8'))
        analyze_log_with_ai(log_data)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Mesaj işlenirken hata oluştu: {e}")

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='log_queue', durable=True)

    print('[*] LogPulse Kestirimci (Predictive) + Hibrit AI Consumer aktif. Kuyruk dinleniyor...')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='log_queue', on_message_callback=callback)
    channel.start_consuming()

if __name__ == '__main__':
    main()