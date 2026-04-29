import pandas as pd
import requests
import json
import re

INPUT_FILE = "dataset of prompt name Exploring Venus.xlsx" 
OUTPUT_FILE = "evaluation_results_asap.csv"
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"

EXAMPLES = """
Score 1: "In the story of 'The Challenge of Exploring Venus' Venus is one of the brightest point of light in the night sky... Venus has blanets of thick atmosphere of 97 percent carbon dioxide... Astronomers thinks that Venus was probably covered with largely oceans..."
Reason: The response is almost entirely a list of facts copied directly from the text. It lacks an original claim or any attempt to evaluate the author's argument. There is no clear introduction or conclusion.

Score 2: "The author thinks that exploring venus is a worthy pursuit because it is our twin planet. Even though it is hot and has acid clouds, we should go there... the author supports this by saying it is close to earth and we can learn a lot."
Reason: Provides a very basic claim but offers little development. The essay relies on simple summary and has limited organizational structure. Mechanical errors are present but the general idea is clear.

Score 3: "In the article, the author suggests that studying Venus is a worthy pursuit despite the dangers it presents. I think the author supports this idea well by giving many details... For example, he mentions that Venus is the closest Earth-like planet and might have had life."
Reason: Demonstrates a developing understanding. It includes a basic evaluation ("supports this idea well") and organizes the evidence into paragraphs, but the analysis remains surface-level and repetitive.

Score 4: "The author of 'The Challenge of Exploring Venus' provides a strong argument that Venus is worth the risk. He balances the dangers, like the 800-degree temperatures and crushing pressure, with the scientific rewards... By mentioning that Venus was once Earth-like, he makes a compelling case for further study."
Reason: A clear explanatory essay. It establishes a functional claim and uses specific evidence to explain *how* the author supports the idea. The structure is logical with an intro, body, and conclusion, though it lacks deep rhetorical analysis.

Score 5: "Is exploring a planet that can melt lead and crush titanium really worth it? According to the author, the answer is a resounding yes. The author effectively supports this pursuit by framing Venus not as a death trap, but as a 'toasty' opportunity thirty miles above the surface..."
Reason: Strong evaluative voice. The student uses more sophisticated vocabulary and rhetorical analysis (e.g., noting how the author 'frames' the evidence). The transitions are smooth and the argument is well-developed.

Score 6: "While the hostile conditions of Venus—erupting volcanoes, corrosive acid, and immense pressure—would deter most, the author of this article constructs a masterful argument for its exploration. By shifting the focus from the inhospitable surface to the Earth-like conditions of the upper atmosphere, the author successfully minimizes the perceived dangers..."
Reason: Exceptional mastery. The essay provides a nuanced evaluation of the author’s persuasive strategy. It synthesizes the technical data from the text with a sophisticated analysis of the author's logic and tone.
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