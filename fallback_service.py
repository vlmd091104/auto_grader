from flask import Flask, request, jsonify

app = Flask(__name__)

def bow_fallback_grading(student_text):
    idea_keywords = ["because", "due to", "meanwhile", "therefore", "however", "since", "consequently", "furthermore", "although", "specifically"]
    text_lower = student_text.lower()
    idea_matches = len([word for word in idea_keywords if word in text_lower])
    i_pts = 5 if idea_matches >= 3 else (3 if idea_matches >= 1 else 0)   
    
    word_count = len(student_text.split())
    c_pts = 5 if word_count >= 50 else (3 if word_count >= 20 else (1 if word_count > 0 else 0))   
    
    i_lbl = "Good" if i_pts >= 5 else ("Fair" if i_pts >= 3 else "Poor")
    c_lbl = "Excellent" if c_pts >= 5 else ("Good" if c_pts >= 3 else ("Fair" if c_pts >= 1 else "Poor"))
    
    return i_pts, c_pts, i_lbl, c_lbl, f"Fallback: {idea_matches} connectors, {word_count} words."

@app.route("/auto-grade", methods=["POST"])
def auto_grade():
    data = request.get_json(force=True)
    student_text = data.get("text", "").strip()
    
    i_pts, c_pts, i_lbl, c_lbl, fb = bow_fallback_grading(student_text)
    
    return jsonify({
        "gradeData": {
            "score": {"pointsEarned": i_pts + c_pts, "pointsPossible": 10},
            "criteria": [
                {"name": "Ideas", "points": i_pts, "selectedOption": f"Fallback ({i_lbl})", "feedback": fb},
                {"name": "Content", "points": c_pts, "selectedOption": f"Fallback ({c_lbl})", "feedback": "Score based on response structure."}
            ]
        },
        "gradeStatus": "service_fallback"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)