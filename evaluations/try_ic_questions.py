"""Replay the three suggested IC questions through the app's live entry point."""
import json
import time
from pathlib import Path
from prototype.institution_confirmation import ask

questions = [
    "What student services does Smith College offer, such as academic counseling, career placement, and on-campus childcare?",
    "Which Massachusetts colleges offer distance education at the undergraduate level?",
    "Compare the tuition payment plans offered by Smith College, Mount Holyoke College, and Wellesley College.",
]
output = Path('evaluations/ic_question_replay.json')
results = []
for question in questions:
    print('QUESTION:', question, flush=True)
    start = time.perf_counter()
    try:
        answer = ask(question, use_model=True)
        item = {'question': question, 'answer': answer}
        print(json.dumps(answer, ensure_ascii=False, default=str), flush=True)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        item = {'question': question, 'error': str(exc), 'error_type': type(exc).__name__}
    item['elapsed_seconds'] = time.perf_counter() - start
    results.append(item)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
