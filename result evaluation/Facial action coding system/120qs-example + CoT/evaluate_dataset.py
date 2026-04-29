import pandas as pd
import requests
import json
import re

INPUT_FILE = "dataset of prompt name Facial action.xlsx" 
OUTPUT_FILE = "evaluation_results_asap.csv"
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"

EXAMPLES = """
Score 1: "The technology Facial Action Ocding of the System is something was knoe when the people are happy or sad. And Mona Lisa she at least according to some new computer software that can recognize emotions... The introduction of ah boddy an ah conclusion to your essay that it is more of our personallity..."
Reason: Extremely limited control of language. Frequent spelling and grammatical errors that impede meaning. Lacks a clear argument and mostly rephrases prompt text without synthesizing it.

Score 2: "I think this claim would be very usefull in a students environment. The resone I feel as why this facial action coding system would do well in schools is because... lower the risks of suicides or school shooting by trying to help the child..."
Reason: Basic opinion with limited development. Relies on personal anecdotes rather than evidence from the text. Simple sentence structures with frequent errors.

Score 3: "In some cases i believe that the Facial Action Coding System is valuable like when people go to counseling in school... Dr. Paul Eckmon made the FACS to scan for the six basic emotion..."
Reason: Demonstrates a developing understanding. Includes specific details from the text but lacks a cohesive organizational structure and deeper analysis.

Score 4: "Facial Action Coding System can be both useful and invasive. On the one hand, if a student is bored or confused this can help the computer to recognize this... However, some people may find it to be an invasion of privacy."
Reason: Clear organization and balanced viewpoint. Demonstrates solid comprehension of the text with logical transitions and fewer mechanical errors.

Score 5: "Helpful But Not Needed... How far is too far? Sometime we as a human try to improve our ways of living for society... but in doing so, are we giving away our rights to privacy?"
Reason: Strong voice and thematic development. Uses rhetorical devices and a more sophisticated vocabulary to argue a specific position with nuance.

Score 6: "Childhood is often painted as a happy, idyllic time... Triumph, frustration, bitterness, and indifference are all commonplace feelings at school... The FACS system offers a window into this hidden world..."
Reason: Exceptional control of language and professional tone. Masterful synthesis of the source material into a persuasive and well-structured argument.
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
                        "Respond ONLY in JSON format: {'reason': '<detailed analysis>', 'score': <int>}"
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