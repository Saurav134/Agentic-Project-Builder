#!/usr/bin/env python3
"""
Agentic Project Builder - Web API & UI
Provides a web interface for project generation.
"""

import os
import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


import shutil


load_dotenv(override=True)

# Import agent components
from builder.graph import agent
from builder.tools import init_project_root, get_project_root, list_files, zip_project

# Initialize FastAPI
app = FastAPI(
    title="Agentic Project Builder",
    description="AI-powered multi-agent system for automated code generation",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== API Endpoints ==============


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
    }


@app.post("/api/generate")
async def generate_project(request: dict):
    """
    Generate a project (non-streaming).

    Request body:
        {"prompt": "Your project description"}
    """
    prompt = request.get("prompt", "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Initialize project directory
    init_project_root()

    try:
        result = agent.invoke({"user_prompt": prompt}, {"recursion_limit": 100})

        return {
            "success": result.get("status") == "DONE",
            "status": result.get("status"),
            "project_path": result.get("project_path", str(get_project_root())),
            "summary": result.get("final_summary", ""),
            "errors": result.get("errors", []),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
async def get_project_files():
    """Get list of generated files."""
    files = list_files.invoke({"directory": "."})

    if "ERROR" in files:
        return {"files": [], "error": files}

    file_list = [f.strip() for f in files.split("\n") if f.strip()]
    return {"files": file_list}


# ============== WebSocket for Streaming ==============


@app.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """
    WebSocket endpoint for streaming project generation.

    Send: {"prompt": "Your project description"}
    Receive: Stream of generation events
    """
    await websocket.accept()

    try:
        # Receive the prompt
        data = await websocket.receive_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            await websocket.send_json(
                {"event": "error", "message": "Prompt is required"}
            )
            await websocket.close()
            return

        # Initialize
        init_project_root()

        await websocket.send_json(
            {
                "event": "started",
                "message": f"Starting project generation for: {prompt[:100]}...",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Stream events from the agent
        async for event in agent.astream_events(
            {"user_prompt": prompt}, {"recursion_limit": 100}, version="v2"
        ):
            event_type = event.get("event", "")
            event_name = event.get("name", "")

            # Filter and format relevant events
            if event_type in ["on_chain_start", "on_chain_end"]:
                await websocket.send_json(
                    {
                        "event": event_type,
                        "name": event_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            elif event_type == "on_tool_end":
                tool_output = str(event.get("data", {}).get("output", ""))[:200]
                await websocket.send_json(
                    {
                        "event": "tool_output",
                        "name": event_name,
                        "output": tool_output,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Send completion
        await websocket.send_json(
            {
                "event": "complete",
                "message": "Project generation complete!",
                "project_path": str(get_project_root()),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@app.get("/api/download")
async def download_project():
    project_root = Path(get_project_root())

    if not project_root.exists():
        raise HTTPException(status_code=404, detail="No project found")

    zip_path = zip_project(project_root)

    return FileResponse(
        zip_path, filename="generated_project.zip", media_type="application/zip"
    )


# ============== Web UI ==============


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the web UI."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic Project Builder</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 40px 0;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            color: #888;
            font-size: 1.1em;
        }
        
        .input-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .input-group {
            display: flex;
            gap: 15px;
        }
        
        input[type="text"] {
            flex: 1;
            padding: 15px 20px;
            font-size: 1em;
            border: 2px solid rgba(0, 217, 255, 0.3);
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            outline: none;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus {
            border-color: #00d9ff;
        }
        
        input[type="text"]::placeholder {
            color: #666;
        }
        
        button {
            padding: 15px 30px;
            font-size: 1em;
            font-weight: bold;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #1a1a2e;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 217, 255, 0.3);
        }
        
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .examples {
            margin-top: 15px;
            color: #666;
            font-size: 0.9em;
        }
        
        .examples span {
            color: #00d9ff;
            cursor: pointer;
            margin: 0 5px;
        }
        
        .examples span:hover {
            text-decoration: underline;
        }
        
        .output-section {
            background: #0a0a0f;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            min-height: 400px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .output-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .output-title {
            font-weight: bold;
            color: #00d9ff;
        }
        
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
        }
        
        .status.idle { background: rgba(255, 255, 255, 0.1); }
        .status.running { background: rgba(0, 217, 255, 0.2); color: #00d9ff; }
        .status.complete { background: rgba(0, 255, 136, 0.2); color: #00ff88; }
        .status.error { background: rgba(255, 68, 68, 0.2); color: #ff4444; }
        
        .log-entry {
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 8px;
            font-family: 'Consolas', monospace;
            font-size: 0.9em;
            border-left: 3px solid #333;
        }
        
        .log-entry.start { border-left-color: #00d9ff; background: rgba(0, 217, 255, 0.05); }
        .log-entry.end { border-left-color: #00ff88; background: rgba(0, 255, 136, 0.05); }
        .log-entry.tool { border-left-color: #ffaa00; background: rgba(255, 170, 0, 0.05); }
        .log-entry.error { border-left-color: #ff4444; background: rgba(255, 68, 68, 0.05); }
        .log-entry.complete { border-left-color: #00ff88; background: rgba(0, 255, 136, 0.1); }
        
        .log-time {
            color: #666;
            font-size: 0.8em;
            margin-right: 10px;
        }
        
        .log-name {
            color: #00d9ff;
            font-weight: bold;
        }
        
        .agents-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }
        
        .agent-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .agent-card .icon {
            font-size: 1.5em;
            margin-bottom: 5px;
        }
        
        .agent-card .name {
            font-weight: bold;
            color: #00d9ff;
        }
        
        footer {
            text-align: center;
            padding: 30px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1> Agentic Project Builder</h1>
            <p class="subtitle">Multi-Agent AI System for Automated Code Generation</p>
        </header>
        
        <div class="agents-info">
            <div class="agent-card"><div class="name">Planner</div></div>
            <div class="agent-card"><div class="name">Architect</div></div>
            <div class="agent-card"><div class="name">Coder</div></div>
            <div class="agent-card"><div class="name">Reviewer</div></div>
            <div class="agent-card"><div class="name">Fixer</div></div>
            <div class="agent-card"><div class="name">Tester</div></div>
            <div class="agent-card"><div class="name">Finalizer</div></div>
        </div>
        
        <div class="input-section">
            <div class="input-group">
                <input type="text" id="prompt" placeholder="Describe your project... e.g., Build a todo app with HTML, CSS, and JavaScript">
                <button class="btn-primary" id="generateBtn" onclick="startGeneration()">
                    Generate
                </button>

                <button class="btn-primary" id="downloadBtn" onclick="downloadProject()" disabled>
                    Download Project
                </button>

            </div>
            <div class="examples">
                Try: 
                <span onclick="setPrompt('Build a colorful todo app with HTML, CSS, and JavaScript')">Todo App</span> |
                <span onclick="setPrompt('Create a Python CLI calculator with basic math operations')">Calculator</span> |
                <span onclick="setPrompt('Build a simple portfolio website with HTML, CSS and JS')">Portfolio</span>
            </div>
        </div>
        
        <div class="output-section" id="output">
            <div class="output-header">
                <span class="output-title"> Generation Log</span>
                <span class="status idle" id="status">Idle</span>
            </div>
            <div id="logs">
                <div class="log-entry">Ready to generate. Enter your project idea above and click Generate!</div>
            </div>
        </div>
        
        <footer>
            Built by Saurav Deshpande
        </footer>
    </div>
    
    <script>
        let ws = null;
        
        function setPrompt(text) {
            document.getElementById('prompt').value = text;
        }
        
        function formatTime() {
            return new Date().toLocaleTimeString();
        }
        
        function addLog(message, type = '') {
            const logs = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.innerHTML = '<span class="log-time">' + formatTime() + '</span> ' + message;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
        }
        
        function setStatus(status, text) {
            const statusEl = document.getElementById('status');
            statusEl.className = 'status ' + status;
            statusEl.textContent = text;
        }
        
        function startGeneration() {
            const prompt = document.getElementById('prompt').value.trim();
            if (!prompt) {
                alert('Please enter a project description');
                return;
            }
            
            // Clear previous logs
            document.getElementById('logs').innerHTML = '';
            
            // Disable button
            const btn = document.getElementById('generateBtn');
            btn.disabled = true;
            btn.textContent = 'Generating...';
            
            setStatus('running', 'Running');
            addLog('Starting project generation...', 'start');
            
            // Connect WebSocket
            const wsUrl = 'ws://' + window.location.host + '/ws/generate';
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                ws.send(JSON.stringify({ prompt: prompt }));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                switch(data.event) {
                    case 'started':
                        addLog(data.message, 'start');
                        break;
                    case 'on_chain_start':
                        addLog('Starting: <span class="log-name">' + data.name + '</span>', 'start');
                        break;
                    case 'on_chain_end':
                        addLog('Completed: <span class="log-name">' + data.name + '</span>', 'end');
                        break;
                    case 'tool_output':
                        addLog('Tool [' + data.name + ']: ' + data.output, 'tool');
                        break;
                    case 'complete':
                        addLog(data.message, 'complete');
                        addLog('Project saved to: ' + data.project_path, 'complete');
                        setStatus('complete', 'Complete');
                        updateDownloadButton();
                        break;
                    case 'error':
                        addLog('Error: ' + data.message, 'error');
                        setStatus('error', 'Error');
                        break;
                }
            };
            
            ws.onerror = (error) => {
                addLog('WebSocket error', 'error');
                setStatus('error', 'Error');
            };
            
            ws.onclose = () => {
                btn.disabled = false;
                btn.textContent = 'Generate';
            };
        }

        function downloadProject() {
            window.open("/api/download", "_blank");
        }
    
        async function updateDownloadButton() {
            try {
                const res = await fetch("/api/files");
                const data = await res.json();
                const btn = document.getElementById("downloadBtn");

            if (data.files && data.files.length > 0) {
                btn.disabled = false;
            } else {
                btn.disabled = true;
            }
            } catch {
                document.getElementById("downloadBtn").disabled = true;
            }
        }
    </script>
</body>
</html>
    """


# ============== Run Server ==============

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    print(
        f"""
     ==============================================================
    |       Agentic Project Builder - Web UI                       |
    |                                                              |
    |     Open http://localhost:{port} in your browser             |
     ==============================================================
    """
    )

    uvicorn.run(app, host="0.0.0.0", port=port)
