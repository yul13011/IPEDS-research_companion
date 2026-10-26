"""Bind longitudinal windows before treating endpoint years as single observations."""
import re

WORDS={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'fifteen':15,'twenty':20}
NUMBER=r'(\d{1,2}|'+ '|'.join(WORDS)+r')'
SEP=r'[\s\-–‑]+'

def is_trend_followup(question):
    q=question.lower()
    if re.search(r'\b\d{6}\b',q) or not re.search(r'\btrend\b|\blongitudinal\b|\bover time\b',q):return False
    allowed=set(('please show display plot give me make it this that same as a an the trend longitudinal over time past last previous most recent for of years year fall terms term academic fiscal reporting periods period ending end with in at starting start beginning from through to between and now').split())|set(WORDS)
    return set(re.findall(r'[a-z]+',q))<=allowed

def trend_years(question,default_end=2024,previous_years=None):
    """Return an inclusive requested window, or None for non-window requests.

    A single date in a trend denotes its endpoint, not the whole date selection.
    An explicit list/range is left to the existing period/cohort binding logic.
    Population durations (six-year graduation) are not observation windows.
    """
    q=question.lower().strip();trend=bool(re.search(r'\btrend\b|\blongitudinal\b|\bover time\b',q))
    # "four-year institutions"/"two-year colleges" describe institution type, not a
    # reporting window: a number+year followed by a sector noun is not a duration.
    not_sector=r'(?![\s\-–‑]+(?:institution|college|school|universit|program|degree|student|graduat|undergrad|cohort|sector|level|old))'
    match=re.search(r'\b(?:past|last|previous|most recent|over(?: the)?|for(?: the)?)\s+'+NUMBER+SEP+r'(?:(?:fall|academic|fiscal|reporting)\s+)?(?:years?|terms?|periods?)\b'+not_sector,q)
    if not match:match=re.search(r'\b'+NUMBER+SEP+r'year'+SEP+r'(?:longitudinal'+SEP+r')?trend\b',q)
    if not trend and not match:return None
    count=(int(match[1]) if match[1].isdigit() else WORDS[match[1]]) if match else None
    explicit=list(dict.fromkeys(int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',q)))
    if len(explicit)>1:
        if count is not None and len(explicit)==2 and re.search(r'\bthrough\b|\bto\b|\bbetween\b|\d{4}\s*[-–]\s*\d{4}',q) and explicit[1]-explicit[0]+1!=count:
            raise ValueError('The stated trend length and start/end years disagree. Please specify the intended interval.')
        return None
    if count is None and not explicit and previous_years and len(previous_years)>1:return sorted(previous_years)
    if count is None:count=10
    if not 1<=count<=10:raise ValueError('Choose a trend of 1–10 years; no years have been omitted.')
    if explicit:
        if re.search(r'\b(?:starting|beginning|from)(?: in| with)?\s+(?:fall\s+)?'+str(explicit[0]),q) and match:
            return list(range(explicit[0],explicit[0]+count))
        end=explicit[0]
    else:end=default_end
    return list(range(end-count+1,end+1))
