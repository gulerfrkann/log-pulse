package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
)

type LogPayload struct {
	Timestamp   string  `json:"timestamp"`
	Hostname    string  `json:"hostname"`
	Level       string  `json:"level"`
	Service     string  `json:"service"`
	Message     string  `json:"message"`
	CPUUsage    float64 `json:"cpu_usage"`
	MemoryUsage float64 `json:"memory_usage"`
}

func failOnError(err error, msg string) {
	if err != nil {
		log.Fatalf("%s: %s", msg, err)
	}
}

func main() {
	conn, err := amqp.Dial("amqp://guest:guest@localhost:5672/")
	failOnError(err, "RabbitMQ sunucusuna bağlanılamadı")
	defer conn.Close()

	ch, err := conn.Channel()
	failOnError(err, "Kanal (Channel) açılamadı")
	defer ch.Close()

	q, err := ch.QueueDeclare(
		"log_queue",
		true,
		false,
		false,
		false,
		nil,
	)
	failOnError(err, "Kuyruk oluşturulamadı")

	fmt.Println("🚀 LogPulse Agent başlatıldı. Proaktif Telemetri & Bellek Akışı devrede...")

	counter := 0
	simulatedMemory := 71.0 // Bellek sızıntısı başlangıç noktası

	for {
		counter++
		var logData LogPayload

		// Kademeli bellek sızıntısı simülasyonu: Her adımda RAM %2.8 artar
		simulatedMemory += 2.8

		// Bellek %93'ü aştığında sızıntı sonucu gerçek bir OOM çöküşü simüle et ve sıfırla
		if simulatedMemory >= 93.0 {
			logData = LogPayload{
				Timestamp:   time.Now().Format(time.RFC3339),
				Hostname:    "server-node-01",
				Level:       "ERROR",
				Service:     "auth-api",
				Message:     "Out of Memory (OOMKilled)! Pod memory limit exceeded.",
				CPUUsage:    95.2,
				MemoryUsage: simulatedMemory,
			}
			simulatedMemory = 71.0 // Çöküş sonrası belleği sıfırla
		} else {
			// Henüz ERROR yok, sistem INFO seviyesinde ama RAM tırmanıyor (Sızıntı Aşaması)
			logData = LogPayload{
				Timestamp:   time.Now().Format(time.RFC3339),
				Hostname:    "server-node-01",
				Level:       "INFO",
				Service:     "auth-api",
				Message:     fmt.Sprintf("Worker active. Routine health check OK. Memory at %.1f%%", simulatedMemory),
				CPUUsage:    24.5,
				MemoryUsage: simulatedMemory,
			}
		}

		jsonData, err := json.Marshal(logData)
		if err != nil {
			fmt.Printf("JSON dönüşüm hatası: %v\n", err)
			continue
		}

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		err = ch.PublishWithContext(ctx,
			"",
			q.Name,
			false,
			false,
			amqp.Publishing{
				ContentType: "application/json",
				Body:        jsonData,
			})
		cancel()

		if err != nil {
			fmt.Printf("Mesaj kuyruğa gönderilemedi: %v\n", err)
		} else {
			fmt.Printf("[PRODUCER] (%s) Telemetri İletildi: Sev=%s | RAM=%%%.1f\n", logData.Service, logData.Level, logData.MemoryUsage)
		}

		time.Sleep(3 * time.Second)
	}
}