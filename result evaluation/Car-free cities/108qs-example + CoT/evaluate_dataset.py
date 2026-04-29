import pandas as pd
import requests
import json
import re

INPUT_FILE = "dataset of prompt name Car-free cities.xlsx" 
OUTPUT_FILE = "evaluation_results_asap.csv"
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"

# Anchor Examples for Car-free cities dataset
EXAMPLES = """
Score 1: "Smog barely filled the air in VAUBAN, Germany... People in France enforced a partial driving ban for a while just to clear the air... BOGOTA, Colombia is where the car-free day was held..."
Reason: The essay is primarily a collection of facts copied or paraphrased from the source text. It lacks a clear original argument or an introductory/concluding framework. Minimal synthesis of ideas.

Score 2: "cars all around the world are a big part of many peoples daily use... in europe, cars are responsible for 12 percent of greenhouse gas emisions... in paris, due to the amounts of polution..."
Reason: Provides a basic opinion with some supporting facts, but the language is simple and contains several mechanical/spelling errors. The structure is repetitive and lacks depth in analysis.

Score 3: "Cars are used everyday in work and social life... But recently we have been cutting back on the usage of cars and we could extend the life of our planet... Transportation is the second largest source of America's emmisions..."
Reason: Demonstrates a developing understanding. It moves beyond just listing facts to attempting a thematic connection (planet longevity), though the organization remains loose and transitions are basic.

Score 4: "Biking for a Change... Cities have come to the realization of how much pollution is being released into our air by motor vehicles... Vauban, Germany, the streets are completely 'car-free'..."
Reason: A clear, multi-paragraph explanatory essay. It has a functional introduction and uses specific evidence from multiple locations (Germany, Paris, Bogota) to explain the advantages. The tone is informative but the vocabulary remains standard.

Score 5: "How important is a persons car to them? Do they really need to have their own car?... Some where in Germany, there's a social experiment going on... The people in this community have taken a huge leap of faith..."
Reason: High-level engagement. Uses rhetorical questions to engage the reader and frames the evidence as a "social experiment." Stronger voice and more deliberate paragraph structure than a Score 4.

Score 6: "Limiting car usage is not the end of the world, it is the beginning of a healthy one. Most cars burn gas which cause smog and pollution... our own ancestors lived for centuries without cars, and we can learn from their simplicity..."
Reason: Mastery of the prompt. Exceptional synthesis that combines environmental data with philosophical reflections on human history. The tone is authoritative, the transitions are seamless, and the vocabulary is sophisticated (e.g., 'precarious era', 'nuanced synthesis').
"""

try:
    df = pd.read_excel(INPUT_FILE)
except Exception as e:
    print(f"Error reading Excel file: {e}")
    exit()

ai_scores = []
rationales = []

print(f"Starting evaluation of {len(df)} samples...")

for index, row in df.iterrows():
    student_text = row.get('full_text', '')
    assignment = row.get('assignment', 'Facial Action Coding System')
    
    payload = {
        "model": "qwen/qwen3-4b", 
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are an expert essay grader. You must grade on a scale of 1-6.\n"
                    "CRITICAL INSTRUCTION: Do not play it safe. If an essay is excellent, give it a 6. "
                    "If it is incoherent, give it a 1. Use the full range of the rubric.\n\n"
                    f"ANCHOR EXAMPLES:\n{EXAMPLES}\n"
                    "Grading Step-by-Step:\n"
                    "1. Analyze the grammar, evidence, and structure.\n"
                    "2. Compare it to the anchor examples.\n"
                    "3. Assign the final score.\n"
                )
            },
            {
                "role": "user",
                "content": f"Topic: {assignment}\n\nEssay: {student_text}\n\n"
                "Respond in JSON with this structure:\n"
                "{\n"
                "  'vocabulary_level': 'basic/sophisticated',\n"
                "  'evidence_synthesis': 'direct quotes/nuanced integration',\n"
                "  'reason': '<detailed analysis comparing to anchors>',\n"
                "  'score': <int>\n"
                "}"
            }
        ],
        "temperature": 0.0,
        "top_p": 0.9
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=300)
        content = response.json()['choices'][0]['message']['content']
        match = re.search(r'(\{.*\})', content, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            score = max(1, min(6, int(data.get("score", 0))))
            ai_scores.append(score)
            rationales.append(data.get("reason", ""))
        else:
            ai_scores.append(None)
            rationales.append("Format Error")
    except Exception as e:
        ai_scores.append(None)
        rationales.append(str(e))
    
    print(f"[{index+1}/{len(df)}] Human: {row.get('score', '?')} | AI: {ai_scores[-1]}")

df['ai_score'] = ai_scores
df['rationale'] = rationales
df.to_csv(OUTPUT_FILE, index=False)
print(f"Results saved to {OUTPUT_FILE}")