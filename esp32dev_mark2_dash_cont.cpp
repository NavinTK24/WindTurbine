#include <WiFi.h>
#include <WebServer.h>

// --- NETWORK CREDENTIALS ---
const char* ssid = "YOUR_HOME_OR_LAB_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

WebServer server(80);

// --- SYSTEM CONTROL VARIABLES ---
bool isRunning = false;
int targetRPM = 0;

// --- HTML/JAVASCRIPT TELEMETRY DASHBOARD ---
const char HTML_DASHBOARD[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Turbine Mission Control</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0f19; color: #e2e8f0; text-align: center; padding: 20px; }
        .container { max-width: 500px; margin: auto; background: #111827; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #1f2937; }
        h2 { color: #3b82f6; margin-bottom: 25px; font-weight: 600; letter-spacing: 1px; }
        .status-box { padding: 15px; border-radius: 8px; font-size: 1.2rem; font-weight: bold; margin-bottom: 25px; transition: 0.3s; }
        .ON { background: #065f46; color: #34d399; border: 1px solid #047857; }
        .OFF { background: #991b1b; color: #f87171; border: 1px solid #b91c1c; }
        .btn { width: 100%; padding: 15px; font-size: 1.2rem; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; transition: 0.2s; margin-bottom: 25px; }
        .btn-start { background: #2563eb; color: white; }
        .btn-start:hover { background: #1d4ed8; }
        .btn-stop { background: #dc2626; color: white; }
        .btn-stop:hover { background: #b91c1c; }
        .slider-container { margin: 30px 0; }
        input[type=range] { width: 100%; height: 8px; border-radius: 5px; background: #374151; outline: none; -webkit-appearance: none; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 24px; height: 24px; border-radius: 50%; background: #3b82f6; cursor: pointer; }
        .rpm-display { font-size: 2.5rem; font-weight: bold; color: #f59e0b; margin: 10px 0; }
        label { font-size: 0.9rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
    <script>
        function sendCommand(url) {
            var xhr = new XMLHttpRequest();
            xhr.open("GET", url, true);
            xhr.send();
        }
        function toggleSystem() {
            var state = document.getElementById("status").innerHTML;
            if (state === "SYSTEM: STOPPED") {
                sendCommand("/start");
                document.getElementById("status").innerHTML = "SYSTEM: RUNNING";
                document.getElementById("status").className = "status-box ON";
                document.getElementById("toggleBtn").innerHTML = "STOP TURBINE";
                document.getElementById("toggleBtn").className = "btn btn-stop";
            } else {
                sendCommand("/stop");
                document.getElementById("status").innerHTML = "SYSTEM: STOPPED";
                document.getElementById("status").className = "status-box OFF";
                document.getElementById("toggleBtn").innerHTML = "START TURBINE";
                document.getElementById("toggleBtn").className = "btn btn-start";
            }
        }
        function updateRPM(val) {
            document.getElementById("rpmVal").innerHTML = val;
            sendCommand("/set_rpm?value=" + val);
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>TURBINE TELEMETRY</h2>
        <div id="status" class="status-box OFF">SYSTEM: STOPPED</div>
        <button id="toggleBtn" class="btn btn-start" onclick="toggleSystem()">START TURBINE</button>
        
        <div class="slider-container">
            <label>Target Command Velocity</label>
            <div class="rpm-display"><span id="rpmVal">0</span> <span style="font-size:1.2rem; color:#9ca3af;">RPM</span></div>
            <input type="range" min="0" max="1500" value="0" step="10" oninput="updateRPM(this.value)">
        </div>
    </div>
</body>
</html>
)rawliteral";

// --- ROUTE HANDLERS ---
void handleRoot() {
    server.send(200, "text/html", HTML_DASHBOARD);
}

void handleStart() {
    isRunning = true;
    server.send(200, "text/plain", "Started");
}

void handleStop() {
    isRunning = false;
    targetRPM = 0;
    server.send(200, "text/plain", "Stopped");
}

void handleSetRPM() {
    if (server.hasArg("value")) {
        targetRPM = server.arg("value").toInt();
        server.send(200, "text/plain", "RPM Updated");
    } else {
        server.send(400, "text/plain", "Bad Request");
    }
}

// NEW: Endpoint for Blender to pull data out wirelessly
void handleStatusAPI() {
    String jsonOutput = "{\"running\":" + String(isRunning ? 1 : 0) + 
                        ",\"rpm\":" + String(targetRPM) + "}";
    server.send(200, "application/json", jsonOutput);
}

// --- INITIALIZATION ---
void setup() {
    Serial.begin(115200);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    Serial.print("Connecting to Network");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("\nConnected!");
    Serial.print("URL: http://");
    Serial.println(WiFi.localIP());

    // Bind URL Endpoints
    server.on("/", handleRoot);
    server.on("/start", handleStart);
    server.on("/stop", handleStop);
    server.on("/set_rpm", handleSetRPM);
    server.on("/status", handleStatusAPI); // Register JSON API path

    server.begin();
}

void loop() {
    server.handleClient();
}
