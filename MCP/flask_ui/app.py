import os
from flask import Flask, request, render_template_string
import requests

app = Flask(__name__)

tpl = """
<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MCP RAG PoC</title></head>
<body style="font-family:system-ui,Segoe UI,Helvetica,Arial,sans-serif;margin:20px;">
<h2>MCP RAG PoC</h2>
<section style="margin-bottom:24px;">
<h3>Step 1: Ingest Swagger</h3>
<form method="post" action="/ingest">
<input type="text" name="urls" placeholder="Swagger URLs comma separated" style="width:480px;" required>
<br><br>
<textarea name="instructions" placeholder="Assistant instructions" style="width:480px;height:120px;"></textarea>
<br><br>
<button type="submit">Ingest</button>
</form>
<div>{{ ingest_status }}</div>
</section>
<section>
<h3>Available Tools</h3>
<div>
{% if tools and tools|length > 0 %}
<table border="1" cellpadding="6" cellspacing="0">
<tr><th>Name</th><th>Method</th><th>Path</th><th>Base</th></tr>
{% for t in tools %}
<tr>
<td>{{ t.name }}</td>
<td>{{ t.method }}</td>
<td>{{ t.path }}</td>
<td>{{ t.base }}</td>
</tr>
{% endfor %}
</table>
{% else %}
<em>No tools yet. Ingest a spec above.</em>
{% endif %}
</div>
</section>
<section>
<h3>Step 2: Chat</h3>
<form method="post" action="/chat">
<input type="text" name="message" placeholder="Ask something..." style="width:480px;" required>
<br><br>
<button type="submit">Send</button>
</form>
<div><pre>{{ chat_answer }}</pre></div>
</section>
</body>
</html>
"""

api_base = os.getenv("API_BASE", "http://localhost:8000")
port = int(os.getenv("FLASK_PORT", "5050"))
session_id = "sess"

@app.route("/", methods=["GET"])
def index():
    tools = []
    try:
        r = requests.get(f"{api_base}/tools", params={"session_id": session_id}, timeout=30)
        if r.status_code == 200:
            tools = r.json()
    except Exception:
        tools = []
    return render_template_string(tpl, tools=tools)

@app.route("/ingest", methods=["POST"])
def ingest():
    urls = request.form.get("urls","")
    instructions = request.form.get("instructions","")
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    ingest_status = ""
    tools = []
    try:
        r = requests.post(f"{api_base}/ingest", json={"swagger_urls": url_list, "instructions": instructions}, timeout=120)
        ingest_status = r.text
        tr = requests.get(f"{api_base}/tools", params={"session_id": session_id}, timeout=30)
        if tr.status_code == 200:
            tools = tr.json()
    except Exception as e:
        ingest_status = f"Error: {e}"
    return render_template_string(tpl, ingest_status=ingest_status, tools=tools)

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.form.get("message","")
    chat_answer = ""
    tools = []
    try:
        r = requests.post(f"{api_base}/chat", json={"session_id":session_id,"message":msg}, timeout=120)
        chat_answer = r.text
        tr = requests.get(f"{api_base}/tools", params={"session_id": session_id}, timeout=30)
        if tr.status_code == 200:
            tools = tr.json()
    except Exception as e:
        chat_answer = f"Error: {e}"
    return render_template_string(tpl, chat_answer=chat_answer, tools=tools)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
