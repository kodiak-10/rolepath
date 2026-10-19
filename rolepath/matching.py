"""Only recommend catalog entries with explicit skill coverage; preserve provenance."""
from .catalog import load_questions


def course_matches(requirement, retriever, prefer_bili=True):
    hits = retriever.search(requirement.get('detail', requirement['evidence']) + ' ' + requirement['skill'], limit=100, skill=requirement['skill'])
    # Relevance first. Platform only breaks exact ties; no creator bonus.
    hits.sort(key=lambda h: (-h.score, prefer_bili and h.resource.get('platform') != 'B站'))
    return hits


def question_matches(skill):
    return [q for q in load_questions() if skill in q['skills']]


def coverage(requirements, retriever, prefer_bili=True):
    return [dict(requirement=r, courses=course_matches(r, retriever, prefer_bili), questions=question_matches(r['skill'])) for r in requirements]
