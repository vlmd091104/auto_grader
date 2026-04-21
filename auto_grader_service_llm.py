import re
import json
import torch
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "Qwen/Qwen3-4B"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    torch_dtype="auto",
    trust_remote_code=True,
    attn_implementation="eager"
)
model.eval()

app = Flask(__name__)
def bow_fallback_grading(student_text):
    # We look for words that indicate reasoning or structure
    idea_keywords = [
        "because", "due to", "meanwhile", "therefore", "however", 
        "since", "consequently", "furthermore", "although", "specifically"
    ]
    text_lower = student_text.lower()
    idea_matches = len([word for word in idea_keywords if word in text_lower])
    if idea_matches == 0:
        i_pts = 0
    elif 1 <= idea_matches < 3:
        i_pts = 3
    else:
        i_pts = 5
    words = student_text.split()
    word_count = len(words)
    if word_count == 0:
        c_pts = 0
    elif 0 < word_count < 20:
        c_pts = 1
    elif 20 <= word_count < 50:
        c_pts = 3
    else:
        c_pts = 5
        
    feedback = f"Fallback Scoring: Found {idea_matches} logical connectors and {word_count} words."
    return i_pts, c_pts, feedback

def normalize_points(pts, allowed_tiers):
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


    prompt = f"""<|im_start|>system
You are an expert academic grader. Evaluate strictly based on:
CRITERION 1: IDEAS (5: Good, 3: Fair, 0: Poor)
CRITERION 2: CONTENT (5: Excellent, 3: Good, 1: Fair, 0: Poor)
Respond ONLY with the JSON object. Do not include any explanations or <think> tags.
Respond ONLY in JSON format.<|im_end|>
<|im_start|>user
Question: {question}
Student Answer: {student_text}
Return JSON: {{"ideas_pts": 0, "ideas_fb": "", "content_pts": 0, "content_fb": ""}}<|im_end|>
<|im_start|>assistant
"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=4096, temperature=0.1)
    
    content_str = tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    print(f"DEBUG LLM OUTPUT: {content_str}")

    try:
        match = re.search(r'(\{.*\})', content_str, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in LLM output")
            
        raw_json = json.loads(match.group(1))
        
        i_pts = normalize_points(raw_json.get("ideas_pts", 0), [0, 3, 5])
        c_pts = normalize_points(raw_json.get("content_pts", 0), [0, 1, 3, 5])
        
        i_lbl = "Good" if i_pts == 5 else ("Fair" if i_pts == 3 else "Poor")
        c_lbl = "Excellent" if c_pts == 5 else ("Good" if c_pts == 3 else ("Fair" if c_pts == 1 else "Poor"))

        return jsonify({
            "gradeData": {
                "score": {"pointsEarned": i_pts + c_pts, "pointsPossible": 10},
                "criteria": [
                    {"name": "Ideas", "points": i_pts, "selectedOption": i_lbl, "feedback": raw_json.get("ideas_fb", "N/A")},
                    {"name": "Content", "points": c_pts, "selectedOption": c_lbl, "feedback": raw_json.get("content_fb", "N/A")}
                ]
            },
            "gradeStatus": "graded"
        })
    except Exception as e:
        print(f"LLM Error, using Structural Fallback: {e}")
        # Get separate scores from our new logic
        i_pts, c_pts, fb = bow_fallback_grading(student_text)
        # Map points to labels for the UI
        i_lbl = "Good" if i_pts == 5 else ("Fair" if i_pts == 3 else "Poor")
        c_lbl = "Excellent" if c_pts == 5 else ("Good" if c_pts == 3 else ("Fair" if c_pts == 1 else "Poor"))
        return jsonify({
            "gradeData": {
                "score": {"pointsEarned": i_pts + c_pts, "pointsPossible": 10},
                "criteria": [
                    {"name": "Ideas", "points": i_pts, "selectedOption": f"Fallback ({i_lbl})", "feedback": fb},
                    {"name": "Content", "points": c_pts, "selectedOption": f"Fallback ({c_lbl})", "feedback": "Score based on response length."}
                ]
            },
            "gradeStatus": "fallback_graded"
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)