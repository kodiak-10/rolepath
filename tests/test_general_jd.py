import json
from pathlib import Path
from types import SimpleNamespace
from rolepath.jd import parse_jd
from rolepath.matching import course_matches
from rolepath import llm

JD = '''【岗位JD】
1.产品原型制作：用 Vibe Coding 独立产出高质量交互 HTML / Web 原型，交付研发落地。
2.AI内容生产：围绕学习主题，用 AI批量生产配套封面、趣味视频、练习题等内容。
3.提示词与评测调优：针对单轮、多轮对话场景做 Prompt Engineering、模型评测与系统化调优，解决幻觉与输出稳定性问题。
4.跨团队协调与项目管理：对齐教研、交互、UI，排优先级、把控项目进度，推动需求从调研到上线闭环。
职位要求
1.本科及以上在读；每周到岗5天，连续实习3个月。
2.具备编程基础，能熟练阅读和修改代码，习惯 AI辅助编程。
3.精通提示词工程，理解 LLM 原理，能独立完成对话场景的评测与调优。
4.有产品 sense：能站在用户视角看问题，将复杂信息用不同视觉和交互思呈现转化为优秀的用户体验。
5.沟通协作能力强，能在快节奏中推动多方对齐、把控进度。
加分项
1.有独立部署 Vibe Coding / AI作品。
2.熟悉工业级 Agent 生产链路。
3.熟悉 Python、HTML 等前后端手段，能独立处理API调用与后端对接。
4.对教育行业有真正的热情——这是我们最看重的底色。'''


def test_screenshot_requirements_are_not_marketing_or_five_generic_tags():
    parsed = parse_jd(JD)
    req = {r['skill']:r for r in parsed['requirements']}
    assert {'原型设计','AI辅助编程','HTML','AIGC','提示词工程','模型评测','代码阅读与修改','交互设计','沟通协作','API集成'} <= req.keys()
    assert '内容营销' not in req
    assert req['Python']['priority'] == req['Agent']['priority'] == '加分项'
    assert req['HTML']['priority'] == '常规要求'  # Also appears in required duties.
    assert req['提示词工程']['importance'] == '原文明示重点'
    assert '幻觉与输出稳定性' in req['模型评测']['detail']
    assert any('教育行业' in row['text'] and not row['skills'] for row in parsed['source_review'])
    assert any(c['text']=='每周到岗5天' for c in parsed['constraints'])


def test_unknown_professions_keep_requirements_visible():
    for jd in ['审计实习生\n负责凭证审核、函证与底稿归档。', '游戏策划\n独立设计关卡，维护数值平衡。', '招聘实习生\n组织面试，维护人才库。']:
        parsed = parse_jd(jd)
        assert parsed['source_review'][-1]['text'] in jd
        assert not parsed['source_review'][-1]['skills']
        assert not parsed['requirements']  # No invented match to a known role.


def test_creator_and_platform_do_not_override_relevance():
    hits = [SimpleNamespace(resource={'platform':'B站','preferred_creator':True,'skills':['SQL']},score=.2),
            SimpleNamespace(resource={'platform':'官方站点','skills':['SQL']},score=.8)]
    ret=SimpleNamespace(search=lambda *a,**kw:list(hits))
    assert course_matches({'skill':'SQL','evidence':'数据库查询'},ret)[0].score == .8


def test_llm_retains_detailed_non_catalog_requirement(monkeypatch):
    row=dict(skill='关卡难度设计',detail='独立设计新手关卡的难度曲线',priority='常规要求',evidence_ids=['L1'],importance='未标注')
    monkeypatch.setattr(llm,'_message',lambda *a,**kw:(json.dumps({'requirements':[row]}),None))
    result=llm.parse_jd_with_llm('独立设计新手关卡的难度曲线')
    assert result['requirements'][0]['detail']==row['detail']
    assert result['source_review'][0]['skills']==['关卡难度设计']


def test_home_and_document_ui_are_general(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('LLM_API_KEY','')
    root=Path(__file__).resolve().parents[1]
    app=AppTest.from_file(str(root/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert not any('传音' in b.label for b in app.button)
    assert 'Ask materials' not in app.radio(key='page').options
    assert app.button(key='global_note_chat').label == 'Ask'
    app.radio(key='page').set_value('岗位分析').run()
    assert not any('黑马' in c.label for c in app.checkbox)
    app.text_area(key='jd_text').set_value(JD).run()
    app.button(key='do_parse').click().run()
    assert not app.exception
    assert '内容营销' not in [r['skill'] for r in app.session_state.jd_result['requirements']]
