import json
from copy import deepcopy
import pytest
from rolepath.resource_research import public_url,collect_evidence,validate_selection,planning_materials

URL='https://www.icourse163.org/course/example'
TEXT='课程包含机械制图基础、公差配合和识图练习，并要求完成三视图绘制与尺寸标注。'

def events():return [dict(type='web_search_call',status='completed',action=dict(queries=['机械设计 入门课程'],sources=[dict(url=URL)])),dict(type='web_extractor_call',status='completed',urls=[URL],output='The useful information in '+URL+' for user goal test as follows: \n\nEvidence in page: \n'+TEXT+'\n\nSummary: \nTool summary')]

def payload():
    source=collect_evidence(events())[0][0]
    return dict(overview='先理解图纸，再练习标注。',items=[dict(source_id=source['id'],kind='course',title='机械制图',creator='示例高校',skills=['机械制图'],reason='针对图纸识读',learn='先完成三视图',evidence_ids=[next(iter(source['paragraphs']))],access_note='以原站当前开放情况为准',minutes=45,company_label='',claim_ids=[])],gaps=[])

@pytest.mark.parametrize('url',['http://127.0.0.1/a','http://169.254.169.254/latest','http://localhost','http://a.local/x','https://name:pass@example.com','javascript:alert(1)','data:text/plain,test','https://example.com:9000/x'])
def test_non_public_links_rejected(url):assert not public_url(url)

def test_search_results_and_page_content_must_both_exist():
    sources,trace=collect_evidence(events())
    assert sources[0]['url']==URL
    assert trace['search_calls']==1 and trace['read_calls']==1
    for items in [events()[:1],events()[1:]]:
        with pytest.raises(ValueError):collect_evidence(items)

def test_ambiguous_or_unsearched_pages_are_not_claimed_as_verified():
    for urls in [[URL,'https://other.example.com/a'],['https://other.example.com/a']]:
        e=events();e[1]['urls']=urls
        with pytest.raises(ValueError):collect_evidence(e)

def test_model_cannot_add_a_source_or_invent_a_quote():
    sources,_=collect_evidence(events())
    for change in [dict(source_id='S2'),dict(evidence_ids=['S2P1']),dict(skills=['SQL']),dict(minutes=True),dict(kind='official_interview')]:
        p=payload();p['items'][0].update(change)
        with pytest.raises(ValueError):validate_selection(p,sources,['机械制图'])

def test_selected_web_resources_are_usable_in_time_budgeted_plan():
    from rolepath.retrieval import LexicalRetriever
    from rolepath.planner import plan_tasks
    sources,_=collect_evidence(events());result=validate_selection(payload(),sources,['机械制图'])
    result['created_at']='2026-10-27T00:00:00+00:00'
    resources,questions=planning_materials(result,[sources[0]['id']])
    tasks,budget=plan_tasks([dict(skill='机械制图',priority='常规要求',status='暂无证据',evidence='学习制图',detail='学习制图')],LexicalRetriever(resources),8,14,extra_questions=questions)
    assert tasks[0]['resource_url']==URL
    assert budget['scheduled_minutes']<=budget['capacity_minutes']
    assert planning_materials(result,[])==([],[])

def test_user_selected_resource_precedes_catalogue_without_creator_bonus():
    from rolepath.matching import course_matches
    from rolepath.retrieval import LexicalRetriever
    sources,_=collect_evidence(events());result=validate_selection(payload(),sources,['机械制图']);result['created_at']='2026-10-27T00:00:00Z'
    resources,_=planning_materials(result,[sources[0]['id']]);other=dict(resources[0],id='curated',title='旧收藏课程',selected_for_plan=False,domestic_platform=True)
    hits=course_matches(dict(skill='机械制图',evidence='识图练习'),LexicalRetriever([other,*resources]))
    assert hits[0].resource['id']==resources[0]['id']


def test_batched_tool_output_uses_url_headers_and_ignores_provider_summary():
    from rolepath.resource_research import extraction_pages
    other='https://example.org/course'
    block=lambda url,text:'The useful information in '+url+' for user goal test as follows: \n\nEvidence in page: \n'+text+'\n\nSummary: \nDo not cite this generated summary.'
    item=dict(urls=[URL,other],output=block(other,'second page')+'\n\n=======\n'+block(URL,TEXT))
    assert extraction_pages(item)==[(other,'second page'),(URL,TEXT)]
    with pytest.raises(ValueError):extraction_pages(dict(item,output=TEXT))


def test_quote_is_read_from_source_ids_without_model_rewriting():
    sources,_=collect_evidence(events())
    result=validate_selection(payload(),sources,['机械制图'])
    assert result['items'][0]['evidence']==TEXT
    row=payload();row['items'][0].update(kind='company_bank',company_label='某企业',claim_ids=[next(iter(sources[0]['paragraphs']))])
    with pytest.raises(ValueError):validate_selection(row,sources,['机械制图'])
