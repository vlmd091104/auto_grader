import re
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
def bow_fallback_grading(student_text):
    idea_keywords = ["because", "due to", "meanwhile", "therefore", "however", "since", "consequently", "furthermore", "although", "specifically"]
    text_lower = student_text.lower()
    idea_matches = len([word for word in idea_keywords if word in text_lower])
    i_pts = 5 if idea_matches >= 3 else (3 if idea_matches >= 1 else 0)   
    word_count = len(student_text.split())
    c_pts = 5 if word_count >= 50 else (3 if word_count >= 20 else (1 if word_count > 0 else 0))   
    feedback = f"Fallback Scoring: Found {idea_matches} logical connectors and {word_count} words."
    return i_pts, c_pts, feedback
def normalize_points(pts, allowed_tiers):
    """
    Ensures points match valid tiers (e.g., mapping 25 to 5).
    """
    try:
        val = int(pts)
        return min(allowed_tiers, key=lambda x: abs(x - val))
    except:
        return 0
@app.route("/auto-grade", methods=["POST"])
def auto_grade():
    data = request.get_json(force=True)
    student_text = data.get("text", "").strip()
    question = data.get("description", "Assignment")
    payload = {
        "model": "qwen/qwen3-4b",
        "messages": [
            {
                "role": "system", 
                "content": "You are a grader. Return ONLY JSON.  \nJSON FORMAT:\n{\n  \"ideas_pts\": int (0, 3, or 5),\n  \"content_pts\": int (0, 1, 3, or 5),\n  \"ideas_fb\": string feedback for ideas,\n  \"content_fb\": string feedback for content\n}"
            },
            {
                "role": "user", 
                "content": f"Question: {question}\nStudent Answer: {student_text}"
            }
        ],
        "temperature": 0.1,
        "stream": False
    }
    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        content_str = result['choices'][0]['message']['content']
        print(f"DEBUG RAW CONTENT: {content_str}")
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
        match = re.search(r'(\{.*\})', content_str, re.DOTALL)
        if not match:
            raise ValueError("No JSON found after stripping think tags")      
        clean_json_str = match.group(1)
        print(f"DEBUG CLEANED JSON: {clean_json_str}")
        raw_json = json.loads(clean_json_str)
        i_pts = normalize_points(raw_json.get("ideas_pts", raw_json.get("Ideas", 0)), [0, 3, 5])
        c_pts = normalize_points(raw_json.get("content_pts", raw_json.get("Content", 0)), [0, 1, 3, 5])
        i_fb = raw_json.get("ideas_fb", raw_json.get("ideas_feedback", "N/A"))
        c_fb = raw_json.get("content_fb", raw_json.get("content_feedback", "N/A"))     
        i_lbl = "Good" if i_pts >= 5 else ("Fair" if i_pts >= 3 else "Poor")
        c_lbl = "Excellent" if c_pts >= 5 else ("Good" if c_pts >= 3 else ("Fair" if c_pts >= 1 else "Poor"))
        return jsonify({
            "gradeData": {
                "score": {"pointsEarned": i_pts + c_pts, "pointsPossible": 10},
                "criteria": [
                    {"name": "Ideas", "points": i_pts, "selectedOption": i_lbl, "feedback": i_fb},
                    {"name": "Content", "points": c_pts, "selectedOption": c_lbl, "feedback": c_fb}
                ]
            },
            "gradeStatus": "graded"
        })
    except Exception as e:
        print(f"LM Studio Error, using Fallback: {e}")
        i_pts, c_pts, fb = bow_fallback_grading(student_text)
        return jsonify({
            "gradeData": {
                "score": {"pointsEarned": i_pts + c_pts, "pointsPossible": 10},
                "criteria": [
                    {"name": "Ideas", "points": i_pts, "selectedOption": f"Fallback", "feedback": fb},
                    {"name": "Content", "points": c_pts, "selectedOption": f"Fallback", "feedback": "Length-based fallback."}
                ]
            },
            "gradeStatus": "fallback_graded"
        })
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)