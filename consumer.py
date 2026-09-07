import os
import json
import pika
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yüklüyoruz
load_dotenv()

# API anahtarını güvenli bir şekilde ortam değişkeninden alıyoruz
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.5-flash")

# (Geri kalan consumer fonksiyonların aynı kalabilir...)

def analyze_log_with_ai(log_data):
    """
    RabbitMQ'dan gelen log verisini inceler, hata varsa Gemini API ile kök neden analizi yapar.
    """
    log_level = log_data.get("level", "INFO")
    message = log_data.get("message", "")
    service = log_data.get("service", "unknown-service")
    cpu = log_data.get("cpu_usage", 0.0)
    memory = log_data.get("memory_usage", 0.0)

    print(f"\n[CONSUMER] Log Alındı -> Servis: {service} | Seviye: {log_level} | Mesaj: {message}")

    # Eğer log normal bir INFO mesajıysa yapay zekayı yormaya gerek yok
    if log_level == "INFO":
        print("[AI BYPASS] Log normal durumda, müdahaleye gerek yok.")
        return

    # Eğer log hata içeriyorsa veya kaynak tüketimi yüksekse Gemini'yi çağırıyoruz
    prompt = f"""
    You are an autonomous DevOps AI agent named LogPulse. 
    Analyze the following system log and telemetry data to find the root cause and suggest a recovery action (e.g., restart container, clear cache, scale up).
    
    Log Data:
    - Service: {service}
    - Level: {log_level}
    - Message: {message}
    - CPU Usage: {cpu}%
    - Memory Usage: {memory}%

    Provide your response in a clear, concise structure:
    1. Root Cause: (Why did this happen?)
    2. Suggested Action: (What command or action should be executed via Docker API?)
    """

    print("[AI ANALİZ] Anomali yakalandı, Gemini API'ye gönderiliyor...")
    try:
        response = model.generate_content(prompt)
        print("\n--- 🤖 GEMINI OTONOM ANALİZİ ---")
        print(response.text)
        print("----------------------------------\n")
    except Exception as e:
        print(f"Gemini API hatası: {e}")

def callback(ch, method, properties, body):
    """
    RabbitMQ kuyruğundan yeni bir mesaj düştüğünde çalışan tetikleyici fonksiyon.
    """
    try:
        log_data = json.loads(body.decode('utf-8'))
        analyze_log_with_ai(log_data)
        # Mesajın kuyruktan başarıyla işlendiğini onaylıyoruz (Acknowledge)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Mesaj işlenirken hata oluştu: {e}")

def main():
    # RabbitMQ bağlantısı
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # Go ajanının yazdığı kuyruğa bağlanıyoruz
    channel.queue_declare(queue='log_queue', durable=True)

    print('[*] LogPulse AI Consumer başlatıldı. Kuyruk dinleniyor. Çıkış için CTRL+C')

    # Adil dağıtım (Fair dispatch): Worker boşta kalmadan önüne yığınla iş yığmaz
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='log_queue', on_message_callback=callback)

    channel.start_consuming()

if __name__ == '__main__':
    main()