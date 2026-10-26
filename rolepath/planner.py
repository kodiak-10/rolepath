"""Source-linked study tasks with daily allocations and an explicit total budget."""
from datetime import date, timedelta
import math
import uuid
from .matching import course_matches, question_matches

DELIVERABLES = {
    '需求分析': '描述一个目标用户的问题，区分现象、需求与解决方案，列出三条待验证假设。',
    'PRD': '写一页 PRD，包含用户、目标、范围、主流程、异常情况与验收标准。',
    '原型设计': '画出一个核心任务的三屏原型，说明页面跳转与失败提示。',
    '竞品分析': '在同一用户任务下比较两款产品，记录功能证据、差异与适用人群。',
    '项目协作': '为一个小功能列出需求评审、开发、测试和上线检查点，注明依赖与负责人角色。',
    '用户运营': '选择一个用户流失场景，列出识别口径、触达方案和验证指标。',
    '数据分析': '用明确标注为模拟的数据计算活跃与留存指标，写出计算口径和结论边界。',
    'AIGC': '用同一主题制作两个生成内容版本，记录提示词、差异与人工核查结果。',
    'Agent': '搭建一个小型智能体，记录输入、工具调用、输出和一次失败案例。',
    '视频生产': '产出一段短视频，保存脚本、分镜与生成或剪辑过程，并检查字幕和事实。',
    '产品设计': '为一个用户任务画出操作流程，说明功能边界、权限与异常情况。',
}


def plan_tasks(assessed, retriever, hours_per_week, days, start=None, prefer_domestic=True):
    if not math.isfinite(hours_per_week) or hours_per_week <= 0 or not 1 <= days <= 180:
        raise ValueError('时间参数无效')
    start = start or date.today()
    capacity = math.floor(hours_per_week * days / 7 * 60)
    daily = [capacity // days + (i < capacity % days) for i in range(days)]
    output, used_questions, missing_resources = [], set(), []
    rank = {'暂无证据': 0, '个人自述（待验证）': 1, '材料提及（待验证）': 2}
    ordered = sorted(assessed, key=lambda a: (a['priority'] == '加分项', a.get('importance') != '原文明示重点', rank.get(a['status'], 3)))
    for item in ordered:
        skill = item['skill']
        hits = course_matches(item, retriever, prefer_domestic)
        if not hits:
            missing_resources.append(skill)
            continue
        primary = hits[0].resource
        focus = primary.get('focus', {}).get(skill, primary['description'])
        candidates = [dict(kind='学习' if item['status'] == '暂无证据' else '复习',
            title=f"{skill}：{focus}", minutes=int(primary.get('minutes_by_skill', {}).get(skill, primary.get('minutes', 60))) if item['status'] == '暂无证据' else 30,
            acceptance='完成指定部分，上传笔记；写出关键结论、一个应用例子和一个待解问题。', question=None)]
        qs = [q for q in question_matches(skill) if q['id'] not in used_questions]
        if qs:
            q = qs[0]
            candidates.append(dict(kind=q['kind'], title=q['title'], minutes=q['minutes'], acceptance=q['deliverable'], question=q))
        else:
            candidates.append(dict(kind='成果练习（非真题）', title=f'{skill}：提交学习成果', minutes=35,
                acceptance=DELIVERABLES.get(skill, f'围绕 JD 原文“{item["evidence"]}”，应用所学提交一个例子，列出假设与验证方式。')+' 这是学习作业，不是企业真题。', question=None))
        for candidate in candidates:
            minutes = candidate['minutes']
            if minutes > sum(daily):
                break
            todo, sessions = minutes, []
            for i in range(days):
                take = min(todo, daily[i])
                if take:
                    sessions.append({'date': str(start + timedelta(days=i)), 'minutes': take})
                    daily[i] -= take
                    todo -= take
                if todo == 0:
                    break
            q = candidate['question']
            if q:
                used_questions.add(q['id'])
            output.append(dict(id=str(uuid.uuid4()), skill=skill, kind=candidate['kind'], title=candidate['title'],
                minutes=minutes, due=sessions[-1]['date'], sessions=sessions, acceptance=candidate['acceptance'],
                resource_id=primary['id'], resource_title=primary['title'], resource_url=primary['url'],
                resource_creator=primary.get('creator', '官方资料/原发布方'), focus=focus,
                chapters=primary.get('chapters', {}).get(skill, []),
                matching_reason=f'资源目录标注覆盖「{skill}」；'+('岗位准备建议：' if item.get('origin') == 'guidance' else '对应 JD 原文：')+item['evidence'],
                requirement_origin=item.get('origin', 'jd'),
                source_checked_at=primary.get('checked_at', '原有资源，未本轮核验'),
                source_note=primary.get('freshness_note', '按原站内容核对适用性'),
                question=q, evidence_status=item['status'], priority=item['priority'], status='待完成'))
    return output, dict(capacity_minutes=capacity, scheduled_minutes=capacity-sum(daily), remaining_minutes=sum(daily),
        unscheduled_skills=[x['skill'] for x in ordered if not any(t['skill']==x['skill'] for t in output)],
        missing_resources=missing_resources,
        missing_questions=[x['skill'] for x in ordered if not question_matches(x['skill'])])
