import os
import docker
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from db import log_audit_action

app = FastAPI(title="LogPulse Control Plane")

# Docker Client Başlatma
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"[UYARI] Docker bağlantısı kurulamadı: {e}")
    docker_client = None

# Bellek içi log ve telemetri deposu
in_memory_logs = []

class LogPayload(BaseModel):
    service: str
    level: str
    message: str
    cpu_usage: float
    memory_usage: float
    ai_analysis: Optional[str] = None

@app.post("/api/logs")
async def receive_log(payload: LogPayload):
    log_dict = payload.dict()
    in_memory_logs.append(log_dict)
    # Bellekte son 50 logu tutalım
    if len(in_memory_logs) > 50:
        in_memory_logs.pop(0)
    return {"status": "ok"}

@app.get("/api/logs", response_model=List[LogPayload])
async def get_logs():
    return in_memory_logs

@app.post("/api/approve")
async def approve_action(payload: dict):
    service_name = payload.get("service")
    if not docker_client:
        raise HTTPException(status_code=500, detail="Docker istemcisi aktif değil.")
    
    try:
        container = docker_client.containers.get(service_name)
        container.restart()
        
        # PostgreSQL Denetim (Audit) Tablosuna Başarılı Müdahaleyi Kaydet
        try:
            log_audit_action(
                incident_id=None,
                service_name=service_name,
                action="DOCKER_CONTAINER_RESTART",
                operator="operator_admin"
            )
        except Exception as db_err:
            print(f"[AUDIT HATA] Denetim izi yazılamadı: {db_err}")

        print(f"[İNSAN ONAYI] '{service_name}' kullanıcı tarafından onaylandı ve yeniden başlatıldı.")
        return {"status": "success", "message": f"'{service_name}' başarıyla yeniden başlatıldı ve denetim tablosuna işlendi."}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"'{service_name}' konteyneri bulunamadı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="tr" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LogPulse AIOps Control Plane</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            slate: { 850: '#151f32', 950: '#0a0f1d' }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen font-sans p-6">
        <div class="max-w-7xl mx-auto space-y-6">
            
            <!-- Üst Başlık & Sistem Durumu -->
            <header class="flex justify-between items-center bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
                <div class="flex items-center space-x-3">
                    <div class="w-3 h-3 bg-emerald-500 rounded-full animate-ping"></div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">LogPulse <span class="text-indigo-400 text-lg font-mono">AIOps Telemetry Plane</span></h1>
                </div>
                <div class="text-sm text-slate-400 flex items-center gap-4">
                    <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-indigo-500"></span>PostgreSQL 15</span>
                    <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-violet-500"></span>Qdrant RAG</span>
                    <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-500"></span>Sliding-Window OLS</span>
                </div>
            </header>

            <!-- KESTİRİMCİ ERKEN UYARI KARTI (PREDICT_WARN - Sarı Pulse Efekti) -->
            <div id="predictive-alert-card" class="hidden bg-amber-950/40 border-2 border-amber-500/80 rounded-2xl p-6 shadow-2xl relative overflow-hidden animate-pulse">
                <div class="flex items-start justify-between">
                    <div class="flex items-start space-x-4">
                        <div class="p-3 bg-amber-500/20 text-amber-400 rounded-xl border border-amber-500/30">
                            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                            </svg>
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="bg-amber-500 text-slate-950 text-xs font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">Kestirimci Erken Uyarı</span>
                                <span id="predictive-service" class="font-mono font-semibold text-amber-300"></span>
                            </div>
                            <h2 class="text-xl font-bold text-white mt-1">Bellek Sızıntısı & OOM Tehlikesi Tespit Edildi</h2>
                            <p id="predictive-message" class="text-amber-200/90 text-sm mt-1 font-mono"></p>
                        </div>
                    </div>
                </div>
                <div class="mt-4 pt-4 border-t border-amber-500/20">
                    <p class="text-xs uppercase font-bold text-amber-400 tracking-wider mb-1">Gemini Proaktif Eylem Önerisi</p>
                    <div id="predictive-ai-text" class="text-sm text-slate-200 bg-slate-900/80 p-4 rounded-xl border border-amber-500/30 whitespace-pre-line font-sans"></div>
                </div>
            </div>

            <!-- Standart Kritik Hata & Operatör Onay Paneli (Kırmızı) -->
            <div id="operator-alert-card" class="hidden bg-rose-950/40 border border-rose-500/40 rounded-2xl p-6 shadow-xl relative">
                <div class="flex items-start justify-between">
                    <div>
                        <span class="bg-rose-500 text-white text-xs font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">Kritik Olay (HITL)</span>
                        <h2 class="text-xl font-bold text-white mt-2">Konteyner Çöküşü - Operatör Onayı Bekleniyor</h2>
                        <p id="alert-service-msg" class="text-rose-200 text-sm mt-1 font-mono"></p>
                    </div>
                    <button id="approve-btn" onclick="approveRemediation()" class="bg-rose-600 hover:bg-rose-500 text-white font-semibold px-5 py-2.5 rounded-xl shadow-lg transition duration-200 flex items-center gap-2">
                        <span>Onayla ve Uygula (Restart)</span>
                    </button>
                </div>
                <div class="mt-4 pt-4 border-t border-rose-500/20">
                    <p class="text-xs uppercase font-bold text-rose-400 tracking-wider mb-1">Gemini Kök Neden & Aksiyon Raporu</p>
                    <div id="alert-ai-text" class="text-sm text-slate-200 bg-slate-900/80 p-4 rounded-xl border border-slate-800 whitespace-pre-line"></div>
                </div>
            </div>

            <!-- Canlı Telemetri Grafiği -->
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-white">Canlı Telemetri & Donanım Tüketimi</h3>
                    <span class="text-xs font-mono text-slate-400">Sliding-Window $N=5$ Takibi</span>
                </div>
                <div class="h-64">
                    <canvas id="telemetryChart"></canvas>
                </div>
            </div>

            <!-- Log Tablosu -->
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg">
                <h3 class="text-lg font-bold text-white mb-4">Gelen Telemetri Akışı</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="bg-slate-800/60 text-xs uppercase text-slate-400 border-b border-slate-800">
                            <tr>
                                <th class="py-3 px-4">Seviye</th>
                                <th class="py-3 px-4">Servis</th>
                                <th class="py-3 px-4">CPU (%)</th>
                                <th class="py-3 px-4">Bellek (%)</th>
                                <th class="py-3 px-4">Mesaj</th>
                            </tr>
                        </thead>
                        <tbody id="log-table-body" class="divide-y divide-slate-800 font-mono text-xs">
                            <!-- JS ile dinamik doldurulacak -->
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

        <script>
            // Chart.js Kurulumu
            const ctx = document.getElementById('telemetryChart').getContext('2d');
            const telemetryChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU Usage (%)',
                            borderColor: '#818cf8',
                            backgroundColor: 'rgba(129, 140, 248, 0.1)',
                            borderWidth: 2,
                            data: [],
                            tension: 0.3,
                            fill: true
                        },
                        {
                            label: 'Memory Usage (%)',
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            borderWidth: 2,
                            data: [],
                            tension: 0.3,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            grid: { color: '#1e293b' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { color: '#1e293b' },
                            ticks: { color: '#94a3b8', maxTicksLimit: 12 }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#cbd5e1' } }
                    }
                }
            });

            let currentCriticalService = null;

            async function fetchTelemetry() {
                try {
                    const response = await fetch('/api/logs');
                    const logs = await response.json();
                    if (!logs || logs.length === 0) return;

                    // Tabloyu güncelle
                    const tableBody = document.getElementById('log-table-body');
                    tableBody.innerHTML = '';
                    
                    const chartLabels = [];
                    const cpuData = [];
                    const memoryData = [];

                    let hasPredictWarn = false;
                    let lastPredictLog = null;

                    let hasError = false;
                    let lastErrorLog = null;

                    logs.forEach((log, index) => {
                        chartLabels.push(`T-${logs.length - index}`);
                        cpuData.push(log.cpu_usage);
                        memoryData.push(log.memory_usage);

                        let badgeColor = 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
                        if (log.level === 'ERROR') {
                            badgeColor = 'bg-rose-500/20 text-rose-400 border border-rose-500/30';
                            hasError = true;
                            lastErrorLog = log;
                        } else if (log.level === 'PREDICT_WARN') {
                            badgeColor = 'bg-amber-500/20 text-amber-400 border border-amber-500/30 font-bold';
                            hasPredictWarn = true;
                            lastPredictLog = log;
                        }

                        const row = `
                            <tr class="hover:bg-slate-800/40 transition">
                                <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[10px] ${badgeColor}">${log.level}</span></td>
                                <td class="py-2.5 px-4 text-slate-200">${log.service}</td>
                                <td class="py-2.5 px-4">${log.cpu_usage.toFixed(1)}%</td>
                                <td class="py-2.5 px-4">${log.memory_usage.toFixed(1)}%</td>
                                <td class="py-2.5 px-4 text-slate-400 truncate max-w-md">${log.message}</td>
                            </tr>
                        `;
                        tableBody.insertAdjacentHTML('afterbegin', row);
                    });

                    // Grafiği güncelle
                    telemetryChart.data.labels = chartLabels.slice(-20);
                    telemetryChart.data.datasets[0].data = cpuData.slice(-20);
                    telemetryChart.data.datasets[1].data = memoryData.slice(-20);
                    telemetryChart.update();

                    // 1. Kestirimci Erken Uyarı Kartı Kontrolü (PREDICT_WARN)
                    const predictCard = document.getElementById('predictive-alert-card');
                    if (hasPredictWarn && lastPredictLog && lastPredictLog.ai_analysis) {
                        document.getElementById('predictive-service').innerText = lastPredictLog.service;
                        document.getElementById('predictive-message').innerText = lastPredictLog.message;
                        document.getElementById('predictive-ai-text').innerText = lastPredictLog.ai_analysis;
                        predictCard.classList.remove('hidden');
                    } else {
                        predictCard.classList.add('hidden');
                    }

                    // 2. Operatör Onay Kartı Kontrolü (ERROR)
                    const alertCard = document.getElementById('operator-alert-card');
                    if (hasError && lastErrorLog && lastErrorLog.ai_analysis) {
                        currentCriticalService = lastErrorLog.service;
                        document.getElementById('alert-service-msg').innerText = `${lastErrorLog.service} - ${lastErrorLog.message}`;
                        document.getElementById('alert-ai-text').innerText = lastErrorLog.ai_analysis;
                        alertCard.classList.remove('hidden');
                    } else {
                        alertCard.classList.add('hidden');
                    }

                } catch (e) {
                    console.error('Telemetri verisi alınamadı:', e);
                }
            }

            async function approveRemediation() {
                if (!currentCriticalService) return;
                const btn = document.getElementById('approve-btn');
                btn.disabled = true;
                btn.innerText = 'İşlem Uygulanıyor...';

                try {
                    const res = await fetch('/api/approve', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ service: currentCriticalService })
                    });
                    const data = await res.json();
                    alert(data.message || 'Konteyner başarıyla yeniden başlatıldı.');
                    document.getElementById('operator-alert-card').classList.add('hidden');
                } catch (err) {
                    alert('Hata oluştu: ' + err);
                } finally {
                    btn.disabled = false;
                    btn.innerText = 'Onayla ve Uygula (Restart)';
                }
            }

            // Her 2 saniyede bir telemetriyi güncelle
            setInterval(fetchTelemetry, 2000);
            fetchTelemetry();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)