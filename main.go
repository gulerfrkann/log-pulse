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

	fmt.Println("🚀 LogPulse Agent başlatıldı. Normal ve Hata logları kuyruğa akıyor...")

	counter := 0
	for {
		counter++
		var logData LogPayload

		// Her 4 döngüde bir sisteme hata (ERROR) simülasyonu sokalım
		if counter%4 == 0 {
			logData = LogPayload{
				Timestamp:   time.Now().Format(time.RFC3339),
				Hostname:    "server-node-01",
				Level:       "ERROR",
				Service:     "auth-api",
				Message:     "Database connection pool exhausted! Out of memory error occurred while processing heavy concurrent requests.",
				CPUUsage:    94.8,
				MemoryUsage: 91.2,
			}
		} else {
			logData = LogPayload{
				Timestamp:   time.Now().Format(time.RFC3339),
				Hostname:    "server-node-01",
				Level:       "INFO",
				Service:     "auth-api",
				Message:     "Health check OK, system operating normally.",
				CPUUsage:    14.2,
				MemoryUsage: 48.6,
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
			fmt.Printf("[PRODUCER] (%s) Kuyruğa Gönderildi: Sev=%s\n", logData.Service, logData.Level)
		}

		time.Sleep(3 * time.Second)
	}
}