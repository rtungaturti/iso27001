"""
ISO/IEC 27001 Audit Compliance Tool
Flask + Groq Free Tier LLM

Setup:
1. pip install flask groq python-dotenv
2. Create .env file with: GROQ_API_KEY=your_key_here
3. Get free API key from: https://console.groq.com
4. Run: python app.py
"""

from flask import Flask, render_template_string, request, jsonify
from groq import Groq
import os
from datetime import datetime

# Load .env only in local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available in production, that's fine

app = Flask(__name__)

# Get API key from environment
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("⚠️  WARNING: GROQ_API_KEY not found in environment variables!")
    print("⚠️  Please set it in Render dashboard or .env file for local dev")
    client = None
else:
    print(f"✅ GROQ_API_KEY found: {GROQ_API_KEY[:8]}...")
    client = Groq(api_key=GROQ_API_KEY)

# ISO 27001:2022 Annex A Controls (subset)
ISO_CONTROLS = {
    "A.5.1": {"name": "Policies for information security", "category": "Organizational"},
    "A.5.2": {"name": "Information security roles and responsibilities", "category": "Organizational"},
    "A.6.1": {"name": "Screening", "category": "People"},
    "A.6.2": {"name": "Terms and conditions of employment", "category": "People"},
    "A.7.1": {"name": "Physical security perimeters", "category": "Physical"},
    "A.7.2": {"name": "Physical entry", "category": "Physical"},
    "A.8.1": {"name": "User endpoint devices", "category": "Technological"},
    "A.8.2": {"name": "Privileged access rights", "category": "Technological"},
    "A.8.3": {"name": "Information access restriction", "category": "Technological"},
}

# In-memory storage (use SQLite/PostgreSQL in production)
audit_data = {
    "assessments": [],
    "chat_history": []
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ISO 27001 Audit Compliance Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .tabs {
            display: flex;
            background: #f8fafc;
            border-bottom: 2px solid #e2e8f0;
        }
        .tab {
            flex: 1;
            padding: 16px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 15px;
            font-weight: 500;
            color: #64748b;
            transition: all 0.3s;
        }
        .tab:hover { background: #e2e8f0; }
        .tab.active {
            color: #3b82f6;
            background: white;
            border-bottom: 3px solid #3b82f6;
        }
        .content {
            padding: 30px;
            min-height: 500px;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        /* Controls List */
        .control-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.3s;
        }
        .control-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        .control-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .control-id {
            font-weight: 700;
            color: #1e3a8a;
            font-size: 14px;
        }
        .control-name { color: #334155; font-size: 15px; }
        .category-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            background: #dbeafe;
            color: #1e40af;
        }
        .assess-btn {
            margin-top: 12px;
            padding: 8px 16px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.3s;
        }
        .assess-btn:hover { background: #2563eb; }
        
        /* Chat Interface */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 600px;
            background: #f8fafc;
            border-radius: 8px;
            overflow: hidden;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin-bottom: 16px;
            display: flex;
            gap: 12px;
        }
        .message.user { justify-content: flex-end; }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
        }
        .message.user .message-content {
            background: #3b82f6;
            color: white;
        }
        .message.assistant .message-content {
            background: white;
            color: #334155;
            border: 1px solid #e2e8f0;
        }
        .chat-input-container {
            padding: 16px;
            background: white;
            border-top: 1px solid #e2e8f0;
            display: flex;
            gap: 12px;
        }
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
        }
        .send-btn {
            padding: 12px 24px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
        }
        .send-btn:hover { background: #2563eb; }
        .send-btn:disabled {
            background: #94a3b8;
            cursor: not-allowed;
        }
        
        /* Gap Analysis */
        .gap-form {
            background: #f8fafc;
            padding: 24px;
            border-radius: 8px;
            margin-bottom: 24px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #334155;
        }
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            resize: vertical;
        }
        .analyze-btn {
            padding: 12px 32px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 15px;
        }
        .analyze-btn:hover { background: #2563eb; }
        .results {
            background: white;
            padding: 24px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
        .spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 ISO/IEC 27001 Audit Compliance Tool</h1>
            <p>Powered by Flask + Groq Free Tier LLM</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('controls')">Controls Assessment</button>
            <button class="tab" onclick="switchTab('chat')">AI Assistant</button>
            <button class="tab" onclick="switchTab('gap')">Gap Analysis</button>
        </div>
        
        <div class="content">
            <!-- Controls Tab -->
            <div id="controls" class="tab-content active">
                <h2 style="margin-bottom: 20px; color: #1e3a8a;">Annex A Controls</h2>
                <div id="controls-list"></div>
            </div>
            
            <!-- Chat Tab -->
            <div id="chat" class="tab-content">
                <div class="chat-container">
                    <div class="chat-messages" id="chat-messages">
                        <div class="message assistant">
                            <div class="message-content">
                                Hello! I'm your ISO 27001 compliance assistant. Ask me anything about information security controls, audit requirements, or implementation guidance.
                            </div>
                        </div>
                    </div>
                    <div class="chat-input-container">
                        <input type="text" id="chat-input" class="chat-input" 
                               placeholder="Ask about ISO 27001 controls..." 
                               onkeypress="if(event.key==='Enter') sendMessage()">
                        <button class="send-btn" onclick="sendMessage()">Send</button>
                    </div>
                </div>
            </div>
            
            <!-- Gap Analysis Tab -->
            <div id="gap" class="tab-content">
                <h2 style="margin-bottom: 20px; color: #1e3a8a;">Gap Analysis</h2>
                <div class="gap-form">
                    <div class="form-group">
                        <label>Control ID:</label>
                        <input type="text" id="gap-control" placeholder="e.g., A.8.1" 
                               style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px;">
                    </div>
                    <div class="form-group">
                        <label>Current Implementation Description:</label>
                        <textarea id="gap-description" rows="6" 
                                  placeholder="Describe your current security controls and practices..."></textarea>
                    </div>
                    <button class="analyze-btn" onclick="analyzeGap()">Analyze Gap</button>
                </div>
                <div id="gap-results"></div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }

        function loadControls() {
            fetch('/api/controls')
                .then(r => r.json())
                .then(data => {
                    const list = document.getElementById('controls-list');
                    list.innerHTML = data.controls.map(c => `
                        <div class="control-card">
                            <div class="control-header">
                                <span class="control-id">${c.id}</span>
                                <span class="category-badge">${c.category}</span>
                            </div>
                            <div class="control-name">${c.name}</div>
                            <button class="assess-btn" onclick="assessControl('${c.id}')">
                                Assess with AI
                            </button>
                        </div>
                    `).join('');
                });
        }

        async function assessControl(controlId) {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = 'Analyzing...';
            btn.disabled = true;
            
            try {
                const response = await fetch('/api/assess', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({control_id: controlId})
                });
                
                if (!response.ok) {
                    throw new Error('Failed to assess control');
                }
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                } else if (data.assessment) {
                    // Create a modal/overlay to show the assessment
                    showAssessmentModal(controlId, data.assessment);
                } else {
                    alert('No assessment data received');
                }
            } catch (error) {
                alert('Error: ' + error.message);
                console.error('Assessment error:', error);
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
        
        function showAssessmentModal(controlId, assessment) {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            `;
            
            modal.innerHTML = `
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 700px; max-height: 80vh; overflow-y: auto; position: relative;">
                    <h3 style="color: #1e3a8a; margin-bottom: 16px;">Assessment: ${controlId}</h3>
                    <div style="white-space: pre-wrap; line-height: 1.6; color: #334155;">${assessment}</div>
                    <button onclick="this.closest('[style*=fixed]').remove()" 
                            style="margin-top: 20px; padding: 10px 24px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                        Close
                    </button>
                </div>
            `;
            
            modal.onclick = (e) => {
                if (e.target === modal) modal.remove();
            };
            
            document.body.appendChild(modal);
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;

            const messagesDiv = document.getElementById('chat-messages');
            messagesDiv.innerHTML += `
                <div class="message user">
                    <div class="message-content">${message}</div>
                </div>
            `;
            input.value = '';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            messagesDiv.innerHTML += `
                <div class="message assistant">
                    <div class="message-content">
                        <div class="spinner"></div>
                        Thinking...
                    </div>
                </div>
            `;

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message})
            });
            const data = await response.json();

            const lastMessage = messagesDiv.lastElementChild;
            lastMessage.querySelector('.message-content').textContent = data.response;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function analyzeGap() {
            const controlId = document.getElementById('gap-control').value;
            const description = document.getElementById('gap-description').value;
            
            if (!controlId || !description) {
                alert('Please fill in all fields');
                return;
            }

            const resultsDiv = document.getElementById('gap-results');
            resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Analyzing...</div>';

            const response = await fetch('/api/gap-analysis', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({control_id: controlId, description})
            });
            const data = await response.json();

            resultsDiv.innerHTML = `
                <div class="results">
                    <h3 style="color: #1e3a8a; margin-bottom: 16px;">Gap Analysis Results</h3>
                    <div style="white-space: pre-wrap; line-height: 1.6;">${data.analysis}</div>
                </div>
            `;
        }

        loadControls();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/controls')
def get_controls():
    controls = [{"id": k, **v} for k, v in ISO_CONTROLS.items()]
    return jsonify({"controls": controls})

@app.route('/api/assess', methods=['POST'])
def assess_control():
    try:
        data = request.json
        print(f"📥 Received data: {data}")
        
        control_id = data.get('control_id')
        print(f"🔑 Control ID: {control_id}")
        
        if control_id not in ISO_CONTROLS:
            print(f"❌ Invalid control ID: {control_id}")
            return jsonify({"error": f"Invalid control ID: {control_id}"}), 400
        
        control = ISO_CONTROLS[control_id]
        print(f"✅ Control found: {control}")
        
        prompt = f"""You are an ISO/IEC 27001:2022 audit expert. Provide a detailed assessment guide for:

Control: {control_id} - {control['name']}
Category: {control['category']}

Please provide:
1. What this control requires (2-3 sentences)
2. Key implementation steps (3-5 bullet points)
3. Common audit evidence needed
4. Typical gaps found during audits

Keep the response concise and practical."""

        print("=" * 80)
        print("📤 PROMPT BEING SENT TO GROQ:")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        
        # Check if Groq client is initialized
        if client is None or not os.environ.get("GROQ_API_KEY"):
            error_msg = "Groq API key not configured. Please set GROQ_API_KEY in .env file"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 500
        
        print("🤖 Calling Groq API...")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024
        )
        
        assessment = chat_completion.choices[0].message.content
        print(f"✅ Received assessment ({len(assessment)} characters)")
        print("=" * 80)
        print("📥 RESPONSE FROM GROQ:")
        print("=" * 80)
        print(assessment)
        print("=" * 80)
        
        audit_data["assessments"].append({
            "control_id": control_id,
            "timestamp": datetime.now().isoformat(),
            "assessment": assessment
        })
        
        return jsonify({"assessment": assessment})
    
    except Exception as e:
        error_msg = f"Error in assess_control: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    
    system_prompt = """You are an expert ISO/IEC 27001:2022 compliance consultant. 
You help organizations understand and implement information security controls.
Provide clear, practical advice focused on audit readiness and compliance.
Be concise but thorough."""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024
        )
        
        response = chat_completion.choices[0].message.content
        
        audit_data["chat_history"].append({
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "assistant": response
        })
        
        return jsonify({"response": response})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/gap-analysis', methods=['POST'])
def gap_analysis():
    data = request.json
    control_id = data.get('control_id')
    description = data.get('description')
    
    if control_id not in ISO_CONTROLS:
        return jsonify({"error": "Invalid control ID"}), 400
    
    control = ISO_CONTROLS[control_id]
    
    prompt = f"""You are an ISO 27001 auditor performing a gap analysis.

Control: {control_id} - {control['name']}
Current Implementation:
{description}

Provide a detailed gap analysis including:
1. Compliance Status (Compliant/Partial/Non-Compliant)
2. Strengths in current implementation
3. Identified gaps and weaknesses
4. Specific recommendations for improvement
5. Priority level (High/Medium/Low)

Be specific and actionable."""

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
            temperature=0.5,
            max_tokens=1500
        )
        
        analysis = chat_completion.choices[0].message.content
        
        return jsonify({"analysis": analysis})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting ISO 27001 Audit Compliance Tool")
    print("📝 Make sure to set GROQ_API_KEY in your .env file")
    print("🌐 Get your free API key at: https://console.groq.com")
    app.run(debug=True, port=5000)
