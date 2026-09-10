from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json

app = FastAPI(title="LogPulse Dashboard")

# Son gelen logları ve analizleri saklamak için bellek içi liste
latest_logs = []

@app.post("/api/logs")
async def receive_log(data: dict):
    global latest_logs
    latest_logs.insert(0, data)
    if len(latest_logs) > 50:
        latest_logs.pop()
    return {"status": "success"}

@app.get("/api/logs")
async def get_logs():
    return latest_logs

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LogPulse - Autonomous DevOps Dashboard</title>
        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            async function fetchLogs() {
                try {
                    let response = await fetch('/api/logs');
                    let logs = await response.json();
                    let container = document.getElementById('log-container');
                    container.innerHTML = '';

                    if (logs.length === 0) {
                        container.innerHTML = '<div class="text-gray-500 text-center py-10 bg-gray-900 rounded-xl border border-gray-800">Henüz log alınmadı. Sistem bekleniyor...</div>';
                        return;
                    }

                    logs.forEach(log => {
                        let isError = log.level === 'ERROR';
                        let borderColor = isError ? 'border-red-500 bg-red-950/20' : 'border-green-500 bg-gray-900';
                        let badgeColor = isError ? 'bg-red-600 text-white animate-pulse' : 'bg-green-600 text-white';

                        let card = `
                            <div class="border-l-4 ${borderColor} p-4 rounded-r-xl shadow-lg mb-4 transition-all duration-300">
                                <div class="flex justify-between items-center mb-2">
                                    <span class="px-2.5 py-0.5 rounded text-xs font-bold ${badgeColor}">${log.level}</span>
                                    <span class="text-xs text-gray-400">Servis: <strong class="text-white">${log.service}</strong> | CPU: %${log.cpu_usage} | Bellek: %${log.memory_usage}</span>
                                </div>
                                <p class="text-sm text-gray-200 mb-2 font-mono">${log.message}</p>
                                ${log.ai_analysis ? `
                                    <div class="mt-3 bg-black/60 p-3 rounded-lg border border-gray-800 text-xs text-gray-300 font-mono">
                                        <div class="text-indigo-400 font-bold mb-1 flex items-center gap-1">
                                            <span>🤖</span> Gemini Otonom Analiz & Kök Neden:
                                        </div>
                                        <pre class="whitespace-pre-wrap text-gray-300">${log.ai_analysis}</pre>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                        container.innerHTML += card;
                    });
                } catch (err) {
                    console.error("Loglar çekilirken hata oluştu:", err);
                }
            }

            // Her 2 saniyede bir paneli otomatik güncelle
            setInterval(fetchLogs, 2000);
            window.onload = fetchLogs;
        </script>
    </head>
    <body class="bg-gray-950 text-gray-100 font-sans min-h-screen p-6">
        <div class="max-w-4xl mx-auto">
            <header class="flex justify-between items-center border-b border-gray-800 pb-4 mb-6">
                <div>
                    <h1 class="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">LogPulse Dashboard</h1>
                    <p class="text-xs text-gray-400">Autonomous DevOps & AI Agent Live Monitoring</p>
                </div>
                <div class="flex items-center space-x-2 bg-gray-900 px-3 py-1.5 rounded-full border border-gray-800">
                    <span class="relative flex h-3 w-3">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    <span class="text-xs text-green-400 font-semibold">Canlı Bağlantı</span>
                </div>
            </header>

            <main>
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-sm font-bold uppercase tracking-wider text-gray-400">Canlı Sistem Akışı & AI Raporları</h2>
                    <span class="text-xs text-gray-500">Her 2 saniyede bir yenilenir</span>
                </div>
                <div id="log-container" class="space-y-3">
                    <!-- Loglar buraya dinamik dolacak -->
                </div>
            </main>
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)