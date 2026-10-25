"""Only recommend catalog entries with explicit skill coverage; preserve provenance."""
from .catalog import load_questions


def reviewed_domestic(resource):
    return resource.get('domestic_platform') is True and bool(resource.get('checked_at') and resource.get('quality_basis'))

def course_matches(requirement, retriever, prefer_domestic=True):
    hits = retriever.search(requirement.get('detail', requirement['evidence']) + ' ' + requirement['skill'], limit=100, skill=requirement['skill'])
    # Exact skill coverage is mandatory. Prefer reviewed domestic sources within
    # that scope, then rank their specific content by relevance. No creator bonus.
    hits = [h for h in hits if requirement['skill'] in h.resource['skills']]
    hits.sort(key=lambda h: (prefer_domestic and not reviewed_domestic(h.resource), -h.score))
    return hits


def question_matches(skill):
    return [q for q in load_questions() if skill in q['skills']]


def coverage(requirements, retriever, prefer_domestic=True):
    return [dict(requirement=r, courses=course_matches(r, retriever, prefer_domestic), questions=question_matches(r['skill'])) for r in requirements]
