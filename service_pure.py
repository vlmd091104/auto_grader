import re
import json
import torch
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "Qwen/Qwen3-4B"

# --- MODEL LOADING ---
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

# --- UTILITY FUNCTIONS ---
def bow_fallback_grading(student_text):
    """
    Structural fallback logic based on connectives and word count.
    """
    idea_keywords = ["because", "due to", "meanwhile", "therefore", "however", "since", "consequently", "furthermore", "although", "specifically"]
    text_lower = student_text.lower()
    idea_matches = len([word for word in idea_keywords if word in text_lower])
    
    # Ideas Scoring (0, 3, 5)
    i_pts = 5 if idea_matches >= 3 else (3 if idea_matches >= 1 else 0)
    
    # Content Scoring (0, 1, 3, 5) based on word count
    word_count = len(student_text.split())
    if word_count == 0: c_pts = 0
    elif word_count < 20: c_pts = 1
    elif word_count < 50: c_pts = 3
    else: c_pts = 5
        
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

# --- ROUTES ---
@app.route("/auto-grade", methods=["POST"])
def auto_grade():
    data = request.get_json(force=True)
    student_text = data.get("text", "").strip()
    question = data.get("description", "Assignment")

    # Strict system prompt to encourage JSON and limit scaling
    prompt = f"""<|im_start|>system
You are an expert academic grader. Evaluate strictly based on:
CRITERION 1: IDEAS (Max 5 pts)
CRITERION 2: CONTENT (Max 5 pts)
Respond ONLY with a JSON object. Do not include thinking tags.
JSON FORMAT:
{{
  "ideas_pts": int (0, 3, or 5),
  "content_pts": int (0, 1, 3, or 5),
  "ideas_fb": "string",
  "content_fb": "string"
}}<|im_end|>
<|im_start|>user
Question: {question}
Student Answer: {student_text}<|im_end|>
<|im_start|>assistant
"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        # Higher max_tokens to accommodate reasoning models
        out = model.generate(**inputs, max_new_tokens=1024, temperature=0.1)
    
    content_str = tokenizer.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    print(f"DEBUG RAW OUTPUT: {content_str}")

    try:
        # 1. STRIP THINK TAGS (Crucial for Qwen/Reasoning models)
        content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
        
        # 2. EXTRACT JSON BLOCK
        match = re.search(r'(\{.*\})', content_str, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in LLM output")
            
        raw_json = json.loads(match.group(1))
        
        # 3. FLEXIBLE KEY EXTRACTION (Handles "Ideas" vs "ideas_pts")
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
        print(f"LLM Error, using Fallback: {e}")
        i_pts, c_pts, fb = bow_fallback_grading(student_text)
        
        return jsonify({
            "gradeData": {
                "score": {"pointsEarned": i_pts + c_pts, "pointsPossible": 10},
                "criteria": [
                    {"name": "Ideas", "points": i_pts, "selectedOption": "Fallback", "feedback": fb},
                    {"name": "Content", "points": c_pts, "selectedOption": "Fallback", "feedback": "Length-based fallback."}
                ]
            },
            "gradeStatus": "fallback_graded"
        })

if __name__ == "__main__":
    # Ensure port 5001 is used to match your configuration
    app.run(host="0.0.0.0", port=5001)