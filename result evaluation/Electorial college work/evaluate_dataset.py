import pandas as pd
import requests
import json
import re

INPUT_FILE = "dataset of prompt name Electorial college work.xlsx" 
OUTPUT_FILE = "evaluation_results_asap.csv"
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"

EXAMPLES = """
Score 1: "Dear, To whom ever it may concern I here am writing this this letter to tell you guys about the Electoral College or changing to election by popular vote... The Electoral college process consists of the selection of the electors..."
Reason: The response is almost entirely a summary of facts copied from the provided texts. It lacks a clear claim (pro or con) and does not attempt to argue a position. The structure is rudimentary and lacks synthesis.

Score 2: "Dear State Senator, I think that we should not abolish the electoral college! The Electoral College has been used for many years... people are just getting upset because the nominees they voted for didn't get elected."
Reason: Provides a basic claim but relies heavily on personal opinion and simple summary. While it includes a quote, it lacks development and the transitions between ideas are weak. Mechanical errors are present but don't stop the main point.

Score 3: "Dear, State Senator, I have come to a conclusion that keeping the Eletoral College would be a much better process... It is more organized with five benifits of certainity of outcome, trans-regonal appeal, winner-take-all method..."
Reason: Demonstrates a developing understanding. The student makes a clear choice and lists specific benefits from the text. However, the essay is mostly a list of points from the source rather than a cohesive argument.

Score 4: "Dear Senator, The purpose of this letter is to fight for the cause of removing the Electoral College and voting simply by popular vote. With evidence from multiple sources like Bradford Plumer and Richard Posner, I will elaborate on this subject..."
Reason: A solid formal letter. It establishes a clear claim and uses evidence from several sources to support the argument. The structure is logical with an introduction, body, and conclusion, though it lacks deep engagement with counterarguments.

Score 5: "Dear Mr. Florida State Senator, My name is [Name]... I am writing to you addressing a matter that I have witnessed being discussed: the Electoral College. I am in favor of abolishing the Electoral College because it is unfair, problematic, and does not represent the will of our citizens..."
Reason: Strong argumentative voice and formal tone. The student effectively organizes the evidence into thematic paragraphs (fairness, representation) and shows a higher level of vocabulary and sentence variety than a Score 4.

Score 6: "Dear Senator, Concerning the topic of the merits and demerits of the Electoral College... Though the lack of control over the president's election is disconcerting, the Electoral College remains a stabilizing force in our republic..."
Reason: Mastery of the prompt. The essay constructs a sophisticated, nuanced argument that directly addresses counterclaims. It synthesizes complex ideas from the sources into a persuasive whole, using professional vocabulary and seamless transitions.
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
    assignment = row.get('assignment', '')
    
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
        "temperature": 0.0
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