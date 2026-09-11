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

# .env dosyasındaki değişkenleri yüklüyoruz
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.5-flash")

# Dashboard API URL adresi
DASHBOARD_API_URL = "http://localhost:8000/api/logs"

# Qdrant ve Embedding Modelini Başlatıyoruz (RAG Hafızası)
try:
    qdrant_client = QdrantClient(host="localhost", port=6333)
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    COLLECTION_NAME = "logpulse_memory"
    
    # Koleksiyon yoksa oluşturalım (Boyut: 384)
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
        )
    print("[QDRANT] RAG Hafıza sistemi başarıyla aktifleşti.")
except Exception as e:
    print(f"[UYARI] Qdrant bağlantısı kurulamadı: {e}")
    qdrant_client = None
    embedder = None

# Docker istemcisini başlatıyoruz
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"[UYARI] Docker bağlantısı kurulamadı: {e}")
    docker_client = None

def send_windows_notification(title, message):
    """
    Plyer kütüphanesi ile Windows masaüstü bildirimi gönderir.
    """
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
    """
    Log verisini ve AI analizini FastAPI dashboard sunucusuna iletir.
    """
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
        # Dashboard açık olmayabilir, ana akışı bozmamak için hatayı yutuyoruz
        pass

def search_memory(error_message):
    """
    Qdrant üzerinde benzer geçmiş hataları ve çözümleri anlamsal olarak arar.
    """
    if not qdrant_client or not embedder:
        return []
    try:
        vector = embedder.encode(error_message).tolist()
        hits = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=2
        )
        memories = []
        for hit in hits:
            if hit.score > 0.70: # Benzerlik eşik değeri
                memories.append(f"- Geçmiş Hata: {hit.payload.get('message')} | Çözüm: {hit.payload.get('solution')}")
        return memories
    except Exception as e:
        print(f"[HATA] Hafıza sorgulanırken hata oluştu: {e}")
        return []

def save_memory(error_message, solution_text):
    """
    Çözülen hatayı ve Gemini'nin çözümünü Qdrant vektör veritabanına kaydeder.
    """
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
        print("[QDRANT] Yeni hata ve çözüm hafızaya (vektör veritabanına) başarıyla kaydedildi.")
    except Exception as e:
        print(f"[HATA] Hafızaya kayıt yapılamadı: {e}")

def restart_container(container_name):
    """
    Belirtilen Docker konteynerini otomatik olarak yeniden başlatır ve masaüstü bildirimi atar.
    """
    if not docker_client:
        print("[HATA] Docker istemcisi aktif değil, otomatik yeniden başlatma yapılamadı.")
        send_windows_notification("❌ LogPulse Uyarı", f"'{container_name}' için Docker aktif değil!")
        return False
    
    try:
        container = docker_client.containers.get(container_name)
        print(f"[OTONOM İŞLEM] '{container_name}' konteyneri yeniden başlatılıyor...")
        container.restart()
        print(f"[BAŞARILI] '{container_name}' başarıyla yeniden başlatıldı!")
        
        # Windows Masaüstü Bildirimi Gönder
        send_windows_notification(
            title="🤖 LogPulse Otonom Onarım",
            message=f"'{container_name}' servisi çöktü. RAG hafızası ile desteklenerek otomatik onarıldı!"
        )
        return True
        
    except docker.errors.NotFound:
        print(f"[HATA] '{container_name}' adında çalışan bir konteyner bulunamadı.")
        send_windows_notification("❌ LogPulse Uyarı", f"'{container_name}' konteyneri bulunamadı!")
        return False
    except Exception as e:
        print(f"[HATA] Konteyner yeniden başlatılırken hata oluştu: {e}")
        send_windows_notification("❌ LogPulse Hata", f"'{container_name}' yeniden başlatılamadı!")
        return False

def analyze_log_with_ai(log_data):
    log_level = log_data.get("level", "INFO")
    message = log_data.get("message", "")
    service = log_data.get("service", "unknown-service")
    cpu = log_data.get("cpu_usage", 0.0)
    memory = log_data.get("memory_usage", 0.0)

    print(f"\n[CONSUMER] Log Alındı -> Servis: {service} | Seviye: {log_level} | Mesaj: {message}")

    ai_analysis_text = None

    if log_level == "INFO":
        print("[AI BYPASS] Log normal durumda, müdahaleye gerek yok.")
        send_to_dashboard(log_data, ai_analysis=None)
        return

    # Qdrant RAG Hafızasından benzer geçmiş hataları sorgula
    past_memories = search_memory(message)
    memory_context = "\n".join(past_memories) if past_memories else "Daha önce benzer bir kayıt bulunamadı (İlk vaka)."

    prompt = f"""
    You are an autonomous DevOps AI agent named LogPulse equipped with a long-term vector memory (RAG). 
    Analyze the current system log by considering your past experiences and solutions.

    Historical Similar Incidents & Solutions:
    {memory_context}

    Current Log Data:
    - Service: {service}
    - Level: {log_level}
    - Message: {message}
    - CPU Usage: {cpu}%
    - Memory Usage: {memory}%

    Provide your response in a clear, concise structure:
    1. Root Cause: (Why did this happen?)
    2. Suggested Action: (What command or action should be executed via Docker API?)
    """

    print("[AI ANALİZ] Anomali yakalandı, RAG bağlamı ile Gemini API'ye gönderiliyor...")
    try:
        response = model.generate_content(prompt)
        ai_analysis_text = response.text
        print("\n--- 🤖 GEMINI OTONOM & HAFIZALI ANALİZİ ---")
        print(ai_analysis_text)
        print("------------------------------------------\n")
        
        # Dashboard'a analiz ile birlikte gönder
        send_to_dashboard(log_data, ai_analysis=ai_analysis_text)
        
        if log_level == "ERROR":
            print("[OTONOM AKSİYON] Hata tespit edildi, otomatik kurtarma prosedürü tetikleniyor...")
            success = restart_container(service)
            if success:
                # Başarılı onarım sonrası bu deneyimi Qdrant hafızasına kaydet
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

    print('[*] LogPulse RAG-Powered AI Consumer başlatıldı. Kuyruk dinleniyor...')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='log_queue', on_message_callback=callback)
    channel.start_consuming()

if __name__ == '__main__':
    main()