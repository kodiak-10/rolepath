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


def learning_requirements(parsed, include_guidance=True):
    """Keep inferred preparation separate from the employer's stated requirements."""
    rows = list(parsed['requirements'])
    seen = {r['skill'] for r in rows}
    if include_guidance:
        for item in parsed.get('orientation', {}).get('learning', []):
            if item['skill'] not in seen:
                rows.append(dict(skill=item['skill'], detail=item['goal'], evidence=item['reason'],
                                 priority='岗位入门建议', origin='guidance', importance='未标注'))
                seen.add(item['skill'])
    return rows
