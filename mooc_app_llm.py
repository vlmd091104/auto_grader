import sqlite3
import requests
import json
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# --- CONFIGURATION ---
AI_SERVICE_URL = "http://127.0.0.1:5001/auto-grade"
FALLBACK_SERVICE_URL = "http://127.0.0.1:5003/auto-grade"
QUESTION = "What is computer architecture and why is it important in the design of computer systems?"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('grading_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  question TEXT, 
                  answer TEXT, 
                  score INTEGER, 
                  status TEXT, 
                  is_flagged BOOLEAN,
                  raw_ai_data TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- TEMPLATES ---

STUDENT_TEMPLATE = """
<style>
    body { font-family: 'Open Sans', sans-serif; background: #f4f7f6; padding: 20px; }
    .openassessment { max-width: 800px; margin: auto; border: 1px solid #ddd; padding: 20px; background: white; border-radius: 8px; }
    .prompt-input { width: 100%; padding: 12px; border: 2px solid #0075b0; border-radius: 4px; margin-bottom: 20px; font-weight: bold; }
    .status-bar { background: #008100; color: white; padding: 5px 10px; font-weight: bold; margin-bottom: 10px; display: inline-block; }
    .result-box { background: #e7f3fe; padding: 15px; border-left: 6px solid #2196F3; margin-top: 20px; }
    .nav { margin-bottom: 20px; text-align: right; }
    textarea { width: 100%; padding: 10px; border: 1px solid #ccc; font-family: inherit; }
</style>

<div class="nav"><a href="/teacher">Switch to Teacher View</a></div>

<div class="openassessment">
    <h2>Your Submission Page</h2>
    
    {% if sub %}
        <div class="status-bar">✔ {{ 'GRADED (Human)' if sub[4] == 'human_verified' else 'GRADED (AI)' }}</div>
        <div style="background: #f9f9f9; padding: 15px; border: 1px solid #eee; margin-bottom: 20px;">
            <strong>Question:</strong> {{ sub[1] }}
        </div>
        
        <div class="result-box">
            <h3>Score: {{ sub[3] }} / 10</h3>
            <p><b>Status:</b> {{ sub[4] | upper | replace('_', ' ') }}</p>
            <hr>
            {% set ai_data = sub[6] | from_json %}
            {% if ai_data and ai_data.gradeData %}
                {% for item in ai_data.gradeData.criteria %}
                    <p><b>{{ item.name }}:</b> {{ item.points }} pts ({{ item.selectedOption }})</p>
                    <small style="color: #666;">{{ item.feedback }}</small>
                {% endfor %}
            {% else %}
                <p>Feedback details are currently unavailable.</p>
            {% endif %}
        </div>
        <br>
        <form action="/request-regrade/{{ sub[0] }}" method="POST" style="display:inline;">
            <button type="submit" style="background:#d32f2f; color:white; padding:5px 15px; border:none; cursor:pointer; border-radius:4px; font-weight:bold;">
                Request Re-grade
            </button>
        </form>
        <a href="/" style="margin-left: 10px;">Submit a new answer</a>
    {% else %}
        <form action="/submit" method="post">
            <label><strong>Question:</strong></label><br>
            <input type="text" name="question" class="prompt-input" value="{{ description }}" required><br>
            
            <label><strong>Your Response:</strong></label><br>
            <textarea name="response" rows="8" placeholder="Type your answer here..." required></textarea><br><br>
            
            <button type="submit" style="background:#0075b0; color:white; padding:10px 20px; border:none; cursor:pointer;">Submit your answer</button>
        </form>
    {% endif %}
</div>
"""

TEACHER_TEMPLATE = """
<style>
    body { font-family: sans-serif; margin: 40px; background: #f0f2f5; }
    table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #0075b0; color: white; }
    .flagged { background-color: #fff3cd; }
    .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .ai { background: #e1f5fe; color: #01579b; }
    .human { background: #e8f5e9; color: #1b5e20; }
</style>
<h2>Teacher Dashboard: Answer Queue</h2>
<p><a href="/">← Back to Student View</a></p>
<table>
    <tr>
        <th>ID</th>
        <th>Student Answer</th>
        <th>Score</th>
        <th>Status</th>
        <th>Actions</th>
    </tr>
    {% for row in submissions %}
    <tr class="{{ 'flagged' if row[5] else '' }}">
        <td>{{ row[0] }}</td>
        <td><small>{{ row[2][:80] }}...</small></td>
        <td><strong style="color: #d32f2f;">{{ row[3] }}/10</strong></td>
        <td><span class="status-badge {{ 'human' if row[4] == 'human_verified' else 'ai' }}">{{ row[4]|upper|replace('_', ' ') }}</span></td>
        <td>
            <a href="/view-answer/{{ row[0] }}" style="margin-right:10px;">View Answer</a>
            <form action="/override" method="post" style="display:inline;">
                <input type="hidden" name="sub_id" value="{{ row[0] }}">
                <input type="number" name="new_score" style="width:50px" min="0" max="10" required>
                <button type="submit">Override</button>
            </form>
            <a href="/flag/{{ row[0] }}" style="margin-left:10px; text-decoration:none;" title="Flag for review">🚩</a>
        </td>
    </tr>
    {% endfor %}
</table>
"""

@app.template_filter('from_json')
def from_json_filter(value):
    try: return json.loads(value)
    except: return None

# --- ROUTES ---

@app.route('/')
def home():
    return render_template_string(STUDENT_TEMPLATE, description=QUESTION, sub=None)

@app.route('/submit', methods=['POST'])
def submit():
    student_text = request.form.get('response')
    # Use the question from the user input instead of the global constant
    user_question = request.form.get('question')
    
    points = 0
    raw_response = "{}"
    try:
        # Pass user_question to the AI service
        resp = requests.post(AI_SERVICE_URL, json={"text": student_text, "description": user_question}, timeout=300)
        if resp.status_code == 200:
            result = resp.json()
            points = result.get("gradeData", {}).get("score", {}).get("pointsEarned", 0)
            raw_response = json.dumps(result)
        else:
            print(f"Primary Service failed. Calling Fallback Service...")
            resp = requests.post(FALLBACK_SERVICE_URL, json={"text": student_text, "description": user_question}, timeout=300)
            result = resp.json()
            points = result.get("gradeData", {}).get("score", {}).get("pointsEarned", 0)
            raw_response = json.dumps(result)
    except Exception as e:
        print(f"Both services failed ({e}).")

    conn = sqlite3.connect('grading_system.db')
    cursor = conn.cursor()
    # Save the user_question into the database for this specific submission
    cursor.execute('''INSERT INTO submissions (question, answer, score, status, is_flagged, raw_ai_data) 
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (user_question, student_text, points, 'ai_graded', False, raw_response))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(url_for('view_result', sub_id=new_id))

@app.route('/result/<int:sub_id>')
def view_result(sub_id):
    conn = sqlite3.connect('grading_system.db')
    sub = conn.execute('SELECT * FROM submissions WHERE id = ?', (sub_id,)).fetchone()
    conn.close()
    return render_template_string(STUDENT_TEMPLATE, sub=sub)

@app.route('/teacher')
def teacher_dashboard():
    conn = sqlite3.connect('grading_system.db')
    subs = conn.execute('SELECT * FROM submissions ORDER BY id DESC').fetchall()
    conn.close()
    return render_template_string(TEACHER_TEMPLATE, submissions=subs)

@app.route('/override', methods=['POST'])
def override_score():
    sub_id = request.form.get('sub_id')
    new_score = request.form.get('new_score')
    conn = sqlite3.connect('grading_system.db')
    conn.execute('UPDATE submissions SET score = ?, status = ? WHERE id = ?', 
                 (new_score, 'human_verified', sub_id))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/flag/<int:sub_id>')
def flag_submission(sub_id):
    conn = sqlite3.connect('grading_system.db')
    conn.execute('UPDATE submissions SET is_flagged = NOT is_flagged WHERE id = ?', (sub_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/request-regrade/<int:sub_id>', methods=['POST'])
def request_regrade(sub_id):
    conn = sqlite3.connect('grading_system.db')
    conn.execute('UPDATE submissions SET is_flagged = 1 WHERE id = ?', (sub_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_result', sub_id=sub_id))

@app.route('/view-answer/<int:sub_id>')
def view_full_answer(sub_id):
    conn = sqlite3.connect('grading_system.db')
    sub = conn.execute('SELECT question, answer FROM submissions WHERE id = ?', (sub_id,)).fetchone()
    conn.close()
    return f"<h3>Question:</h3>p>{sub[0]}</p><hr><h3>Full Answer:</h3><p>{sub[1]}</p><br><a href='/teacher'>Back</a>"

if __name__ == '__main__':
    app.run(port=5002, debug=True)