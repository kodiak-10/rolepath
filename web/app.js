'use strict';

/* ---------- 教学演示数据（与 Streamlit 版一致） ---------- */

const JD_TEXT = '转化漏斗分析实习生（教学演示JD，非真实招聘）：1. 负责注册与活动转化漏斗的日常监控，计算各环节转化率与流失率；2. 熟练使用 Excel 进行数据整理，了解 SQL 取数；3. 具备基础数据分析能力，能输出结论与验证建议；4. 有漏斗分析或运营指标复盘经验优先。';

const SKILL_ALIASES = {
  '运营指标': ['运营指标', '转化率', '留存率', '用户增长', '漏斗分析', '活跃', 'A/B', 'AB实验'],
  'Excel': ['excel', '数据透视表', '电子表格', 'vlookup'],
  'SQL': ['sql', 'mysql', '数据库查询', '取数'],
  '数据分析': ['数据分析', '数据处理', '业务分析', '数据复盘', '产品数据', 'numpy', 'pandas'],
  '项目管理': ['项目执行', '项目交付', '项目管理', '进度管理', '活动落地', '跨部门'],
  '人力资源': ['人力资源', '组织发展', '人才发展', '人才培养', '招聘', '校招', 'HR'],
  '内容运营': ['内容运营', '小红书', '账号运营', '内容策划', '创意', '选题', '文案'],
  'AI工具': ['AI', '人工智能', '大模型', '提示词', 'AIGC'],
  '沟通协作': ['沟通', '协作', '共情', '感知力', '表达', '汇报'],
};

const RESOURCES = {
  '运营指标': { id: 'res012', title: 'Google Analytics 帮助中心', url: 'https://support.google.com/analytics/', creator: 'Google', kind: '官方文档', minutes: 40, focus: '事件、转化、流量来源与指标口径；为注册流程画一张指标树。', reason: 'JD 涉及指标、转化或留存，先统一口径，再练习从数据得出结论。', quality: '官方公开文档，出处和指标定义可核对。', verified: true },
  'Excel': { id: 'res006', title: 'Microsoft Excel 帮助与学习', url: 'https://support.microsoft.com/zh-cn/excel', creator: 'Microsoft', kind: '官方文档', minutes: 45, focus: '公式、筛选、表格与数据透视表；用订单表完成月度汇总。', reason: 'JD 明确提到 Excel、表格或数据透视表，优先练公式、清洗和汇总。', quality: '官方公开文档，按功能查阅，不必通读。', verified: true },
  'SQL': { id: 'res003', title: 'SQLBolt 交互式 SQL 练习', url: 'https://sqlbolt.com/', creator: 'SQLBolt', kind: '交互练习', minutes: 45, focus: 'SELECT、过滤、JOIN 与聚合；完成分组统计并保存可运行 SQL。', reason: 'JD 需要数据库查询或取数，先用交互练习建立可验证的基础。', quality: '练习可在浏览器中完成，题目与结果直接可核对。', verified: true },
  '数据分析': { id: 'res004', title: 'Pandas 官方入门教程', url: 'https://pandas.pydata.org/docs/getting_started/intro_tutorials/index.html', creator: 'Pandas', kind: '官方教程', minutes: 50, focus: 'DataFrame、读取文件、分组与缺失值；输出三条业务观察。', reason: 'JD 强调数据处理或业务分析，先练清洗、计算和结论表达。', quality: '项目官方教程，示例与 API 可核对。', verified: true },
  '项目管理': { id: 'bili001-p25', title: '产品经理快速入门 · 项目管理是什么', url: 'https://www.bilibili.com/video/BV1nv411e7zd/?p=25', creator: '黑马程序员', kind: '已核对章节', minutes: 30, focus: '目标、任务、节点与协作边界；产出一页项目推进表。', reason: 'JD 要求推进项目执行与交付，先建立可检查的任务和节点。', quality: '已核对发布者与章节；未逐集试听，只安排该章节。', verified: true },
  '视频剪辑': { id: 'bili005-p26', title: 'Coze 实战 · 利用剪映生成最终视频', url: 'https://www.bilibili.com/video/BV12omoB4ExF/?p=26', creator: '黑马程序员', kind: '已核对章节', minutes: 35, focus: '理解素材到成片的流程并完成导出；再用一条 30–60 秒作品练节奏与字幕。', reason: 'JD 把视频剪辑列为作品或加分项，先用一个完整短作品证明基础。', quality: '已核对发布者与章节；这是 AI 视频工作流中的成片章节，不是完整剪辑课。', verified: true },
  '内容运营': { id: 'ref023', title: 'HubSpot Academy：内容营销', url: 'https://academy.hubspot.com/courses/content-marketing', creator: 'HubSpot Academy', kind: '官方课程', minutes: 50, focus: '受众、内容目标、选题与分发；完成一篇模拟笔记和复盘指标。', reason: 'JD 提到内容、账号运营或创意，先补内容策略与可复用方法。', quality: '原机构公开课程，含学习内容与测验；不代表小红书平台规则。', verified: true },
  'AI工具': { id: 'cn005', title: '阿里云百炼：文生文 Prompt 指南', url: 'https://help.aliyun.com/zh/model-studio/prompt-engineering-guide', creator: '阿里云百炼', kind: '官方文档', minutes: 40, focus: '指令、上下文、输出格式与结果核验；记录同一任务的两版 Prompt。', reason: 'JD 强调 AI 实际用法，重点是完成任务、核验结果并说明过程。', quality: '模型平台官方文档，方法与当前接口以原站为准。', verified: true },
  '用户研究': { id: 'res013', title: 'Nielsen Norman Group：User Research', url: 'https://www.nngroup.com/articles/which-ux-research-methods/', creator: 'Nielsen Norman Group', kind: '研究指南', minutes: 45, focus: '按问题选择访谈、问卷或可用性测试；写五条中立访谈问题。', reason: 'JD 涉及用户洞察或调研，先学会提出问题并区分事实与推测。', quality: '专业研究机构公开指南，方法论和适用范围可核对。', verified: true },
  '产品能力': { id: 'res007', title: 'Atlassian：Product requirements document', url: 'https://www.atlassian.com/agile/product-management/requirements', creator: 'Atlassian', kind: '实践指南', minutes: 50, focus: '需求背景、范围、用户故事与验收标准；写一页 PRD。', reason: 'JD 提到产品思维或需求分析，需要从用户问题推进到可交付方案。', quality: '专业协作工具的公开指南，模板与方法可核对。', verified: true },
  '市场营销': { id: 'ref023', title: 'HubSpot Academy：内容营销', url: 'https://academy.hubspot.com/courses/content-marketing', creator: 'HubSpot Academy', kind: '官方课程', minutes: 45, focus: '目标用户、内容、渠道与转化；做一个微型活动方案。', reason: 'JD 涉及市场、品牌或投放，先理解用户、渠道和转化之间的关系。', quality: '原机构公开课程；范围偏内容营销，不作为完整市场营销体系。', verified: true },
  '财务分析': { id: 'res006', title: 'Microsoft Excel 帮助与学习', url: 'https://support.microsoft.com/zh-cn/excel', creator: 'Microsoft', kind: '官方文档', minutes: 45, focus: '用表格整理收入、成本和预算，解释口径、差异与待验证假设。', reason: 'JD 提到财务、预算或经营分析，先用可复算的数据建立分析习惯。', quality: '官方工具文档；不替代会计或财务专业课程。', verified: true },
};

const SUPPLEMENTS = {
  '运营指标': [
    { title: '产品运营 · 活跃的定义与指标', url: 'https://www.bilibili.com/video/BV1QL411A7q6/?p=9', creator: '黑马产品经理', kind: '已核对章节' },
    { title: '产品运营 · 留存与流失的定义', url: 'https://www.bilibili.com/video/BV1QL411A7q6/?p=11', creator: '黑马产品经理', kind: '已核对章节' },
  ],
  'SQL': [
    { title: 'MySQL 8.4 官方参考手册', url: 'https://dev.mysql.com/doc/refman/8.4/en/', creator: 'MySQL', kind: '官方文档' },
    { title: '尚硅谷 · 最基本 SELECT 查询', url: 'https://www.bilibili.com/video/BV1iq4y1u7vj/?p=14', creator: '尚硅谷', kind: '已核对章节' },
  ],
  '数据分析': [
    { title: 'Pandas GroupBy 用户指南', url: 'https://pandas.pydata.org/docs/user_guide/groupby.html', creator: 'Pandas', kind: '官方文档' },
  ],
  '项目管理': [
    { title: 'Atlassian：User stories', url: 'https://www.atlassian.com/agile/project-management/user-stories', creator: 'Atlassian', kind: '实践指南' },
    { title: '产品经理快速入门 · 需求评审会', url: 'https://www.bilibili.com/video/BV1nv411e7zd/?p=51', creator: '黑马程序员', kind: '已核对章节' },
  ],
  '视频剪辑': [
    { title: 'Coze 实战 · 根据提示词及图片制作视频', url: 'https://www.bilibili.com/video/BV12omoB4ExF/?p=22', creator: '黑马程序员', kind: '已核对章节' },
  ],
  '内容运营': [
    { title: '产品运营 · 社区化和内容运营', url: 'https://www.bilibili.com/video/BV1QL411A7q6/?p=10', creator: '黑马产品经理', kind: '已核对章节' },
  ],
  'AI工具': [
    { title: '扣子官方：低代码工作流入门', url: 'https://docs.coze.cn/guides_workflow', creator: '扣子官方', kind: '官方文档 · 部分节点可能收费' },
    { title: '李宏毅：生成式人工智能导论', url: 'https://www.bilibili.com/video/BV1BJ4m1e7g8/', creator: '李宏毅 / 啥都会一点的研究生', kind: '已核对课程' },
  ],
  '用户研究': [
    { title: '用户研究与市场、竞品分析的关系', url: 'https://www.woshipm.com/user-research/5184902.html', creator: '用研那些事儿 / 人人都是产品经理', kind: '署名实践文章' },
  ],
  '产品能力': [
    { title: '产品经理快速入门 · 需求池讲解', url: 'https://www.bilibili.com/video/BV1nv411e7zd/?p=42', creator: '黑马程序员', kind: '已核对章节' },
    { title: 'Atlassian：User stories', url: 'https://www.atlassian.com/agile/project-management/user-stories', creator: 'Atlassian', kind: '实践指南' },
  ],
};

const RESOURCE_RULES = [
  { key: '运营指标', aliases: SKILL_ALIASES['运营指标'] },
  { key: 'Excel', aliases: SKILL_ALIASES.Excel },
  { key: 'SQL', aliases: SKILL_ALIASES.SQL },
  { key: '数据分析', aliases: SKILL_ALIASES['数据分析'] },
  { key: '项目管理', aliases: SKILL_ALIASES['项目管理'] },
  { key: '人力资源', aliases: SKILL_ALIASES['人力资源'] },
  { key: '视频剪辑', aliases: ['视频剪辑', '剪辑', '视频制作', '剪映', 'Premiere', 'PR'] },
  { key: '内容运营', aliases: SKILL_ALIASES['内容运营'] },
  { key: 'AI工具', aliases: SKILL_ALIASES.AI工具 },
  { key: '实习准备', aliases: ['实习经验', '实习准备', '互联网实习', '求职准备'] },
  { key: '沟通协作', aliases: SKILL_ALIASES['沟通协作'] },
  { key: '用户研究', aliases: ['用户研究', '用户调研', '访谈', '问卷', '消费者洞察', '用户体验'] },
  { key: '产品能力', aliases: ['产品思维', '需求分析', '产品设计', '原型', '产品经理', '需求文档'] },
  { key: '市场营销', aliases: ['市场', '营销', '品牌', '投放', '广告', '增长'] },
  { key: '客户与销售', aliases: ['销售', '客户成功', '商务', '谈判', '客户沟通'] },
  { key: '财务分析', aliases: ['财务', '会计', '预算', '成本', '经营分析'] },
  { key: '培训与教学', aliases: ['培训', '教学', '课程设计', '讲师', '教研'] },
];

const DELIVERABLES = { '数据分析': '用明确标注为模拟的数据计算活跃与留存指标，写出计算口径和结论边界。' };
const PRACTICES = {
  '人力资源': '选一个校招或人才培养项目，写出目标、对象、流程、分工、风险与复盘指标，形成一页项目方案。',
  '实习准备': '把当前 JD 拆成五项能力，为每项补一个可展示作品或证据，整理成一页作品集目录。',
  '沟通协作': '用“结论—证据—请求”写一段 3 分钟汇报，并列出两种反对意见及回应。',
  '客户与销售': '模拟一次客户沟通，写出需求澄清问题、方案价值、异议处理与下一步行动。',
  '培训与教学': '设计一节 20 分钟微课，包含学习目标、讲解、练习、反馈与验收标准。',
};

function practiceFor(skill, evidence) {
  return DELIVERABLES[skill] || PRACTICES[skill] || `围绕 JD 原文“${evidence}”完成一个小成果，列出假设、执行过程和验证方式。`;
}

function resourceFor(skill) {
  const name = String(skill || '').trim();
  const normalized = name.toLowerCase();
  const rule = RESOURCE_RULES.find((item) => item.aliases.some((alias) => hasAlias(normalized, alias)));
  return rule && RESOURCES[rule.key] ? { ...RESOURCES[rule.key], key: rule.key } : null;
}

function matchedResources(reqs) {
  return reqs.map((item) => {
    const course = resourceFor(item.skill);
    return {
      skill: item.skill, priority: item.priority, evidence: item.evidence, detail: item.detail || item.evidence,
      course, supplements: course ? (SUPPLEMENTS[course.key] || []) : [],
      reason: course ? course.reason : '暂未收录与这项能力直接对应、且出处可核对的具体课程；先用岗位专项练习建立成果。',
      practice: course ? '' : practiceFor(item.skill, item.detail || item.evidence),
    };
  });
}

const QUESTIONS = {
  'SQL': { id: 'q005', title: '超过经理收入的员工', kind: 'SQL笔试练习', minutes: 35, deliverable: '在原站阅读表结构、独立编写 SQL 并测试，记录关联条件。', url: 'https://leetcode.cn/problems/employees-earning-more-than-their-managers/', source: '力扣 LeetCode' },
};

const STAGES = ['落地页访问', '点击注册', '完成手机验证', '填写资料', '注册成功'];
const CHANNELS = { '渠道 A · 应用商店': [8000, 3600, 2700, 2160, 1900], '渠道 B · 信息流广告': [6000, 3000, 900, 720, 630] };
const STEPS = STAGES.slice(0, -1).map((s, i) => `${s} → ${STAGES[i + 1]}`);
const TARGET_STEP = 1;
const stepRates = (counts) => counts.slice(0, -1).map((c, i) => counts[i + 1] / c * 100);
const TARGET_RATE_B = stepRates(CHANNELS['渠道 B · 信息流广告'])[TARGET_STEP];
const TARGET_RATE_A = stepRates(CHANNELS['渠道 A · 应用商店'])[TARGET_STEP];
const RATE_TOLERANCE = 2.0;
const CAUSE_HINTS = ['验证码', '短信', '手机号', '运营商', '到达', '延迟', '加载', '输入', '验证'];
const TEST_HINTS = ['a/b', 'ab实验', 'ab 实验', '实验', '对照', '埋点', '日志', '访谈', '灰度', '分渠道', '成功率'];

const NEXT_STEP_TEXTS = {
  recompute: '重新对照数据表逐环节计算转化率：转化率 = 下一环节人数 ÷ 上一环节人数，再比较两个渠道的差距。',
  check_denominator: '核对计算口径：该环节转化率应使用相邻两环节人数相除，而不是除以最初访问量。',
  hypothesis: '把原因改写成可检验的假设，例如「渠道 B 的短信验证码到达率低」，并说明用什么数据能证实或排除。',
  design_test: '为假设设计一个对照验证：如分渠道对比验证码发送成功率日志，或小流量 A/B 实验。',
  write_recap: '把本次结论整理成一页复盘，并尝试用 SQL 从事件明细复算漏斗，巩固取数口径。',
  extend_window: '尝试更换时间窗口或增加渠道数据，检查结论是否稳定，再写进你的作品集。',
};

const AI_NOTICE = 'AI 暂时不可用，请稍后重试';
const VIEW_LABELS = { space: '我的空间', jd: '看岗位', prep: '准备学习', work: '岗位实操', feedback: '查看反馈' };
const SPACE_NAVS = ['概览', '学习笔记', '历史记录'];
const PREP_NAVS = ['计划与行动', '课程与题目', '学习任务'];

/* ---------- 规则评分（保留原有实现） ---------- */

function grade(submission) {
  const cause = (submission.cause || '').trim();
  const verification = (submission.verification || '').trim();
  const stepOk = submission.step === TARGET_STEP;
  const rateBOk = Math.abs(Number(submission.rate_b || 0) - TARGET_RATE_B) <= RATE_TOLERANCE;
  const rateAOk = Math.abs(Number(submission.rate_a || 0) - TARGET_RATE_A) <= RATE_TOLERANCE;
  const causeOk = cause.length >= 20;
  const causeSpecific = CAUSE_HINTS.some((w) => cause.includes(w));
  const verificationOk = verification.length >= 20;
  const verificationSpecific = TEST_HINTS.some((w) => verification.toLowerCase().includes(w));
  const score = 40 * stepOk + 15 * rateBOk + 15 * rateAOk + 10 * causeOk + 5 * causeSpecific + 10 * verificationOk + 5 * verificationSpecific;
  const nextSteps = [];
  if (!stepOk) nextSteps.push('recompute');
  if (!(rateBOk && rateAOk)) nextSteps.push('check_denominator');
  if (!(causeOk && causeSpecific)) nextSteps.push('hypothesis');
  if (!(verificationOk && verificationSpecific)) nextSteps.push('design_test');
  nextSteps.push('write_recap');
  if (score === 100) nextSteps.push('extend_window');
  return { score, step_ok: stepOk, rate_b_ok: rateBOk, rate_a_ok: rateAOk, cause_ok: causeOk, cause_specific: causeSpecific, verification_ok: verificationOk, verification_specific: verificationSpecific, next_steps: nextSteps };
}

function feedbackPoints(fb) {
  const strengths = [], fixes = [];
  if (fb.step_ok) strengths.push('环节定位正确：渠道 B 在「点击注册 → 完成手机验证」的流失明显高于渠道 A。');
  else fixes.push('环节定位有误：请逐环节计算转化率，找出渠道 B 与渠道 A 差距最大的一步。');
  for (const [channel, ok, value] of [['B', fb.rate_b_ok, TARGET_RATE_B], ['A', fb.rate_a_ok, TARGET_RATE_A]]) {
    if (ok) strengths.push(`渠道 ${channel} 该环节转化率计算正确（${value}%）。`);
    else fixes.push(`渠道 ${channel} 转化率与参考值（${value}%）不符，请核对计算口径。`);
  }
  if (fb.cause_ok && fb.cause_specific) strengths.push('原因假设具体、可检验。');
  else if (!fb.cause_ok) fixes.push('原因说明不足 20 字，请写成完整的可检验假设。');
  else fixes.push('假设还不够具体：请落到验证码发送、到达或输入体验等可观测环节。');
  if (fb.verification_ok && fb.verification_specific) strengths.push('验证方法可执行。');
  else if (!fb.verification_ok) fixes.push('验证方法不足 20 字，请说明用什么数据或实验来检验假设。');
  else fixes.push('验证方法缺少可操作手段：例如分渠道对比短信发送成功率日志，或小流量 A/B 实验。');
  return [strengths, fixes];
}

/* ---------- 关键词预览（保留原有实现） ---------- */

function hasAlias(text, alias) {
  if (/^[A-Za-z0-9_ ]+$/.test(alias)) {
    return new RegExp(`(?<![A-Za-z])${alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![A-Za-z])`, 'i').test(text);
  }
  return text.toLowerCase().includes(alias.toLowerCase());
}

function extractSkills(text) {
  const found = new Map();
  const units = text.split(/[\n；;。]+/).map((s) => s.trim()).filter(Boolean);
  for (const unit of units) {
    for (const fragment of unit.match(/[^；;\n。，,]+/g) || []) {
      const sentence = fragment.replace(/^[ \t\r\-*•0-9、.：:]+|[ \t\r\-*•0-9、.：:]+$/g, '');
      if (!sentence) continue;
      for (const [skill, aliases] of Object.entries(SKILL_ALIASES)) {
        if (!aliases.some((a) => hasAlias(sentence, a))) continue;
        const bonus = /(优先|加分|更佳|plus|bonus)/i.test(sentence);
        if (!found.has(skill)) {
          found.set(skill, { skill, priority: bonus ? '加分项' : '常规要求', evidence: unit });
        } else if (!bonus) {
          const row = found.get(skill);
          row.priority = '常规要求';
          row.evidence = unit;
        }
      }
    }
  }
  return [...found.values()];
}

/* ---------- 计划生成（沿用时间预算，匹配可核对资料或岗位实践） ---------- */

function isoDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function planTasks(requirements, hoursPerWeek, days, live) {
  live = live || { resources: {}, questions: {} };
  const capacity = Math.floor(hoursPerWeek * days / 7 * 60);
  const daily = Array.from({ length: days }, (_, i) => Math.floor(capacity / days) + (i < capacity % days ? 1 : 0));
  const start = new Date();
  const tasks = [];
  const usedQuestions = new Set();
  for (const item of requirements) {
    const skill = item.skill;
    const primary = live.resources[skill] || resourceFor(skill) || null;
    const qsrc = live.questions[skill] || QUESTIONS[skill] || null;
    const question = qsrc && !usedQuestions.has(qsrc.id) ? qsrc : null;
    const candidates = [];
    if (primary) {
      candidates.push({ kind: '学习', title: `${skill}：${primary.focus}`, minutes: primary.minutes, acceptance: '完成指定部分，上传笔记；写出关键结论、一个应用例子和一个待解问题。' });
    }
    candidates.push(question
      ? { kind: question.kind, title: question.title, minutes: question.minutes, acceptance: question.deliverable, question }
      : { kind: '成果练习（非真题）', title: `${skill}：提交学习成果`, minutes: 35, acceptance: practiceFor(skill, item.evidence) + ' 这是学习作业，不是企业真题。' });
    for (const candidate of candidates) {
      let todo = candidate.minutes;
      if (todo > daily.reduce((a, b) => a + b, 0)) break;
      const sessions = [];
      for (let i = 0; i < days && todo > 0; i++) {
        const take = Math.min(todo, daily[i]);
        if (take) {
          const d = new Date(start);
          d.setDate(d.getDate() + i);
          sessions.push({ date: isoDate(d), minutes: take });
          daily[i] -= take;
          todo -= take;
        }
      }
      if (candidate.question) usedQuestions.add(candidate.question.id);
      const reason = primary
        ? `已核对资料「${primary.title}」匹配「${skill}」；对应 JD 原文：${item.evidence}`
        : `暂无合适的可核对课程，安排岗位实践；对应 JD 原文：${item.evidence}`;
      tasks.push({
        skill, kind: candidate.kind, title: candidate.title, minutes: candidate.minutes,
        due: sessions[sessions.length - 1].date, acceptance: candidate.acceptance, question: candidate.question || null,
        resource_title: primary ? primary.title : '', resource_url: primary ? primary.url : '', resource_creator: primary ? primary.creator : '',
        matching_reason: reason,
      });
    }
  }
  const remaining = daily.reduce((a, b) => a + b, 0);
  return { tasks, summary: { capacity_minutes: capacity, scheduled_minutes: capacity - remaining, remaining_minutes: remaining, unscheduled_skills: requirements.filter((r) => !tasks.some((t) => t.skill === r.skill)).map((r) => r.skill) } };
}

/* ---------- 状态与持久化 ---------- */

const STORAGE_KEY = 'rolepath_web_practice_v2';
let storageOk = true;

function defaultState() {
  return {
    view: 'space', spaceNav: '概览', prepNav: '计划与行动',
    jd: { raw: '', draft: '', requirements: null, mode: null },
    sliders: { hours: 8, days: 14 },
    plan: null, attempts: [], notes: [],
    practiceDraft: { step: 0, rate_b: 0, rate_a: 0, cause: '', verification: '' },
    doll: { open: false, messages: [], draft: '', mode: 'chat' },
    feedbackIndex: 0,
  };
}

let state = defaultState();
try {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) {
    const saved = JSON.parse(raw);
    if (saved && typeof saved === 'object') {
      const base = defaultState();
      state = Object.assign(base, saved);
      state.jd = Object.assign(base.jd, saved.jd || {});
      state.sliders = Object.assign(base.sliders, saved.sliders || {});
      state.practiceDraft = Object.assign(base.practiceDraft, saved.practiceDraft || {});
      state.doll = Object.assign(base.doll, saved.doll || {});
      if (!Array.isArray(state.attempts)) state.attempts = [];
      if (!Array.isArray(state.notes)) state.notes = [];
      if (!Array.isArray(state.doll.messages)) state.doll.messages = [];
    }
  }
} catch (e) { storageOk = false; }

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  catch (e) { storageOk = false; const el = document.getElementById('storage-warning'); if (el) el.hidden = false; }
}

/* 瞬态（不持久化）：请求进行中、提示、笔记编辑等 */
let jdBusy = false, jdError = '';
let dollBusy = false, dollNote = null;
let dollResume = { target: '', text: '', memory: null, sourceName: '' };
let planMsg = '', workError = false, noteError = '', editingNoteId = null;

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = (id) => document.getElementById(id);
const latestAttempt = () => state.attempts[0] || null;
const isStr = (v) => typeof v === 'string';
const httpsUrl = (u) => isStr(u) && /^https:\/\//i.test(u);

function hashText(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return ('00000000' + h.toString(16)).slice(-8) + '-' + s.length;
}

function nowStamp() {
  const d = new Date();
  return `${isoDate(d)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function linkHtml(url, text) {
  return httpsUrl(url)
    ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`
    : esc(text);
}

/* ---------- 服务端调用（同源 Function；任何失败都降级为通用提示） ---------- */

const API_BASE = '/functions/v1/app/';

async function post(route, body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const res = await fetch(API_BASE + route, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal: controller.signal,
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) { return null; }
  finally { clearTimeout(timer); }
}

function validJdPayload(data) {
  return !!data && data.ok === true && Array.isArray(data.requirements)
    && data.requirements.every((r) => r && typeof r === 'object' && isStr(r.skill) && r.skill.trim());
}

function normalizeRequirements(rows) {
  return rows.map((r) => ({
    skill: r.skill.trim(),
    priority: isStr(r.priority) && r.priority ? r.priority : '常规要求',
    evidence: isStr(r.evidence) ? r.evidence : '',
    detail: isStr(r.detail) && r.detail ? r.detail : (isStr(r.evidence) ? r.evidence : ''),
    importance: isStr(r.importance) ? r.importance : '',
  }));
}

/* ---------- 通用渲染 ---------- */

function navigate(view, prepNav, spaceNav) {
  if (!VIEW_LABELS[view]) view = 'space';
  state.view = view;
  if (prepNav && PREP_NAVS.includes(prepNav)) state.prepNav = prepNav;
  if (spaceNav && SPACE_NAVS.includes(spaceNav)) state.spaceNav = spaceNav;
  save();
  render();
  window.scrollTo(0, 0);
}

function renderNav() {
  const done = {
    jd: Array.isArray(state.jd.requirements),
    prep: !!state.plan,
    work: state.attempts.length > 0,
    feedback: state.attempts.length > 0,
  };
  const labels = { space: '我的空间', jd: '1 看岗位', prep: '2 准备学习', work: '3 岗位实操', feedback: '4 查看反馈' };
  for (const btn of document.querySelectorAll('#page-nav button')) {
    const view = btn.dataset.go;
    btn.textContent = labels[view] + (done[view] ? ' ' : '');
    if (done[view]) {
      const check = document.createElement('span');
      check.className = 'nav-check';
      check.setAttribute('aria-hidden', 'true');
      check.textContent = '✓';
      btn.appendChild(check);
    }
    if (view === state.view) btn.setAttribute('aria-current', 'page');
    else btn.removeAttribute('aria-current');
  }
}

function subnavHtml(items, current, action) {
  return `<div class="subnav" role="tablist">${items.map((name) =>
    `<button type="button" role="tab" data-action="${action}" data-nav="${esc(name)}" aria-selected="${name === current}">${esc(name)}</button>`).join('')}</div>`;
}

function render() {
  renderNav();
  for (const section of document.querySelectorAll('main > section')) section.hidden = section.id !== `view-${state.view}`;
  if (state.view === 'space') renderSpace();
  else if (state.view === 'jd') renderJd();
  else if (state.view === 'prep') renderPrep();
  else if (state.view === 'work') renderWork();
  else if (state.view === 'feedback') renderFeedbackPage();
  renderDoll();
}

/* ---------- 我的空间 ---------- */

function activityLines() {
  const rows = [];
  if (state.plan) rows.push({ time: state.plan.created_at, text: `学习计划 · ${state.plan.tasks.length} 个任务 · ${state.plan.hours} 小时/周 × ${state.plan.days} 天` });
  for (const a of state.attempts.slice(0, 5)) rows.push({ time: a.created_at, text: `岗位练习 · 得分 ${a.feedback.score}/100 · ${a.submission.step_label}` });
  for (const n of state.notes.slice(0, 5)) rows.push({ time: n.updated_at || n.created_at, text: `学习笔记 · ${n.title}` });
  return rows.sort((a, b) => String(b.time).localeCompare(String(a.time))).slice(0, 6);
}

function renderSpace() {
  const nav = SPACE_NAVS.includes(state.spaceNav) ? state.spaceNav : '概览';
  let html = subnavHtml(SPACE_NAVS, nav, 'space-nav');
  if (nav === '概览') html += spaceOverviewHtml();
  else if (nav === '学习笔记') html += spaceNotesHtml();
  else html += spaceHistoryHtml();
  $('space-body').innerHTML = html;
}

function spaceOverviewHtml() {
  const attempt = latestAttempt();
  const taskCount = state.plan ? state.plan.tasks.length : 0;
  const activities = activityLines();
  return `<div class="rp-hero">
      <h1>你的下一步，<br>从这里变清晰。</h1>
      <p>探索感兴趣的工作，拆解真实岗位要求。把想去的方向，变成今天可以完成的一小步。</p>
    </div>
    <div class="hero-actions">
      <button type="button" class="primary" data-action="demo-load">体验岗位任务 →</button>
      <button type="button" data-go="jd">分析我的 JD →</button>
      <button type="button" data-go="prep" data-prep="${state.plan ? '学习任务' : '计划与行动'}">${state.plan ? '继续学习 →' : '制定学习计划 →'}</button>
    </div>
    <div class="metrics">
      <div class="metric"><span>计划任务</span><b>${taskCount}</b></div>
      <div class="metric"><span>练习提交</span><b>${state.attempts.length}</b></div>
      <div class="metric"><span>最近得分</span><b>${attempt ? attempt.feedback.score + ' / 100' : '—'}</b></div>
    </div>
    ${state.plan ? '' : '<p class="muted">从零开始也没关系。分析一份岗位描述后，就可以制定自己的第一份计划。</p>'}
    <div class="card"><h2>最近动态</h2>
      ${activities.length ? `<ul class="activity">${activities.map((r) => `<li><span class="muted">${esc(r.time)}</span> ${esc(r.text)}</li>`).join('')}</ul>` : '<p class="muted">还没有记录。载入教学 JD 或写下第一份笔记，这里会显示你的进展。</p>'}
    </div>
    ${attempt ? practiceRecordHtml() : ''}`;
}

function spaceNotesHtml() {
  const editing = editingNoteId ? state.notes.find((n) => n.id === editingNoteId) : null;
  return `<div class="rp-library-heading"><h1>学习笔记</h1><p>把零散的学习，变成自己的积累。</p></div>
    <form class="card solid" id="note-form">
      <h2>${editing ? '编辑笔记' : '新建笔记'}</h2>
      <label>标题<input id="note-title" type="text" maxlength="100" value="${editing ? esc(editing.title) : ''}" placeholder="例：漏斗口径复盘"></label>
      <label>内容<textarea id="note-body" rows="4" maxlength="8000" placeholder="写下学到的口径、结论或待解问题…">${editing ? esc(editing.body) : ''}</textarea></label>
      ${noteError ? `<p class="error">${esc(noteError)}</p>` : ''}
      <div class="row-buttons">
        <button type="button" class="primary" data-action="note-save">${editing ? '更新笔记' : '保存笔记'}</button>
        ${editing ? '<button type="button" data-action="note-cancel">取消编辑</button>' : ''}
      </div>
    </form>
    ${state.notes.length ? state.notes.map((n) => `<div class="card note-row">
      <h2>${esc(n.title)}</h2>
      <p class="note-body">${esc(n.body)}</p>
      <p class="muted">更新于 ${esc(n.updated_at || n.created_at)}</p>
      <div class="row-buttons">
        <button type="button" class="primary" data-action="note-chat" data-id="${esc(n.id)}">与笔记对话</button>
        <button type="button" data-action="note-edit" data-id="${esc(n.id)}">编辑</button>
        <button type="button" data-action="note-delete" data-id="${esc(n.id)}">删除</button>
      </div>
    </div>`).join('') : '<div class="card"><p class="muted">你的知识，从这里开始。保存第一份笔记后，可以让狗蛋结合笔记回答问题。</p></div>'}`;
}

function spaceHistoryHtml() {
  if (!state.attempts.length) {
    return `<div class="card"><h2>历史记录</h2><p class="info">还没有练习提交。去「岗位实操」完成第一次练习。</p>
      <button type="button" class="primary" data-go="work">去岗位实操 →</button></div>`;
  }
  return `<div class="card"><h2>历史记录 · 岗位练习</h2>
    <div class="table-wrap"><table><thead><tr><th>提交时间</th><th>得分</th><th>定位环节</th><th></th></tr></thead>
    <tbody>${state.attempts.map((a, i) => `<tr><td>${esc(a.created_at)}</td><td class="num">${a.feedback.score} / 100</td><td>${esc(a.submission.step_label)}</td>
      <td><button type="button" data-action="history-view" data-index="${i}">查看这次反馈 →</button></td></tr>`).join('')}</tbody></table></div>
    <p class="muted">记录保存在本浏览器；重新提交会保存为新的练习记录。</p></div>`;
}

/* ---------- 看岗位 ---------- */

function requirementsTableHtml(reqs) {
  return `<div class="table-wrap"><table><thead><tr><th>能力要求</th><th>要求类别</th><th>对应原文</th><th>具体要求</th></tr></thead>
    <tbody>${reqs.map((r) => `<tr><td>${esc(r.skill)}</td><td>${esc(r.priority)}</td><td>${esc(r.evidence)}</td><td>${esc(r.detail || r.evidence)}</td></tr>`).join('')}</tbody></table></div>`;
}

function renderJd() {
  const parsed = Array.isArray(state.jd.requirements) ? state.jd : null;
  let html = `<p class="kicker">教学演示 JD · 非真实招聘</p>
    <h1>把目标 JD 变成可检查的能力要求</h1>
    <p class="lede">粘贴 JD 原文，解析结果会保留原文证据。也可以先载入教学演示 JD 体验完整流程。</p>
    <div class="card">
      <h2>教学演示 JD</h2>
      <pre class="jd-raw">${esc(JD_TEXT)}</pre>
      <button type="button" data-action="demo-load" ${jdBusy ? 'disabled' : ''}>载入并解析教学 JD →</button>
    </div>
    <div class="card solid">
      <label>自定义 JD 原文
        <textarea id="jd-input" rows="7" maxlength="20000" placeholder="粘贴岗位名称、职责、任职要求、优先条件和实习时间…">${esc(state.jd.draft || '')}</textarea>
      </label>
      ${jdError ? `<p class="error">${esc(jdError)}</p>` : ''}
      <button type="button" class="primary" data-action="jd-parse" ${jdBusy ? 'disabled' : ''}>解析岗位要求</button>
      ${jdBusy ? '<p class="searching">正在解析岗位要求…</p><div class="skeleton" aria-hidden="true"><span class="skel-line"></span><span class="skel-line"></span><span class="skel-line short"></span></div>' : ''}
    </div>`;
  if (parsed) {
    const llm = parsed.mode === 'llm';
    html += `<div class="card">
      <h2>能力要求</h2>
      <p class="muted">解析方式：${llm ? 'LLM 抽取（带原文验证，仍需逐条核对）' : '关键词预览（非 AI，不代表完整岗位分析）'}</p>
      ${llm ? '' : `<p class="warn">${esc(AI_NOTICE)}；已降级为关键词预览，请逐条核对 JD 原文。</p>`}
      ${parsed.requirements.length ? requirementsTableHtml(parsed.requirements) : '<p class="warn">未发现可识别的技能，请核查 JD 原文；关键词词库并不覆盖所有岗位要求。</p>'}
      <p class="info">学历、毕业年份、地点与实习时间请先自行确认；学习计划不能替代这些条件。</p>
      <button type="button" class="primary" data-go="prep" data-prep="计划与行动">生成学习计划 →</button>
    </div>`;
  }
  $('jd-body').innerHTML = html;
}

async function parseJd(text) {
  text = (text || '').trim();
  if (!text) { jdError = '请先粘贴 JD 原文再解析。'; render(); return; }
  jdError = '';
  jdBusy = true;
  render();
  const data = await post('jd', { text });
  let requirements, mode;
  if (validJdPayload(data)) { requirements = normalizeRequirements(data.requirements); mode = 'llm'; }
  else { requirements = extractSkills(text); mode = 'keyword'; }
  state.jd = { raw: text, draft: text, requirements, mode };
  jdBusy = false;
  save();
  render();
}

/* ---------- 准备学习 ---------- */

function renderPrep() {
  const nav = PREP_NAVS.includes(state.prepNav) ? state.prepNav : '计划与行动';
  let html = subnavHtml(PREP_NAVS, nav, 'prep-nav');
  if (nav === '计划与行动') html += prepPlanHtml();
  else if (nav === '课程与题目') html += prepCoursesHtml();
  else html += prepTasksHtml();
  $('prep-body').innerHTML = html;
}

function practiceEntryHtml() {
  const attempt = latestAttempt();
  const next = state.plan && state.plan.tasks.length ? state.plan.tasks[0] : null;
  return `<div class="practice-entry">
    <h2>岗位练习 · 转化漏斗分析</h2>
    <p>以数据分析实习生身份完成一个模拟导师任务：对比渠道注册漏斗，定位流失环节并提交分析结论，获得规则点评。</p>
    ${next ? `<p class="muted">当前应做：${esc(next.title)} · ${esc(next.due)} 截止 · ${next.minutes} 分钟</p>` : ''}
    <button type="button" class="primary" data-go="work">进入实习工作台 →</button>
    ${attempt ? `<p class="muted">最近提交：${esc(attempt.created_at)} · 得分 ${attempt.feedback.score}/100<br>下一步建议：${esc(NEXT_STEP_TEXTS[attempt.feedback.next_steps[0]])}</p>` : ''}
  </div>`;
}

function practiceRecordHtml() {
  const attempt = latestAttempt();
  if (!attempt) return '';
  return `<div class="card"><h2>岗位练习记录 · 转化漏斗分析</h2>
    <p>最近提交：${esc(attempt.created_at)} · 得分 ${attempt.feedback.score}/100</p>
    <p>下一步建议：${esc(NEXT_STEP_TEXTS[attempt.feedback.next_steps[0]])}</p>
    <button type="button" data-go="work">继续练习 →</button></div>`;
}

function prepPlanHtml() {
  const reqs = Array.isArray(state.jd.requirements) ? state.jd.requirements : null;
  if (!reqs || !reqs.length) {
    return `<h1>能力证据与个性化学习计划</h1>
      <p class="info">先在「看岗位」载入或解析一份 JD，再制定学习计划。</p>
      <button type="button" class="primary" data-go="jd">去看岗位 →</button>
      ${practiceRecordHtml()}`;
  }
  const role = (state.jd.raw.split('\n')[0] || '').slice(0, 40);
  let html = `<h1>能力证据与个性化学习计划</h1>
    <div class="rp-role-banner"><span>正在准备</span>${esc(role)}</div>
    <div class="card solid">
      <div class="controls">
        <label>每周可用学习时间（小时）
          <input id="hours" type="range" min="1" max="30" value="${Number(state.sliders.hours) || 8}">
          <output id="hours-out">${Number(state.sliders.hours) || 8}</output>
        </label>
        <label>准备周期（天）
          <input id="days" type="range" min="3" max="90" value="${Number(state.sliders.days) || 14}">
          <output id="days-out">${Number(state.sliders.days) || 14}</output>
        </label>
      </div>
      <p class="muted">规划器会遵循总时间预算。固定练习任务只是候选计划，不代表标准化课时。</p>
      <button type="button" class="primary" data-action="make-plan">生成并保存学习路径</button>
      ${planMsg ? `<p class="info">${esc(planMsg)}</p>` : ''}
    </div>`;
  if (!state.plan) {
    html += '<p class="info">还没有保存的学习路径。调整上方时间预算后点击「生成并保存学习路径」。</p>';
    return html;
  }
  const { tasks, summary } = state.plan;
  html += `<div class="metrics">
      <div class="metric"><span>计划总预算</span><b>${(summary.capacity_minutes / 60).toFixed(1)} 小时</b></div>
      <div class="metric"><span>已安排任务</span><b>${tasks.length}</b></div>
      <div class="metric"><span>待安排技能</span><b>${summary.unscheduled_skills.length}</b></div>
    </div>
    <p class="muted">这里展示最近一次保存的计划；修改 JD 或时间后，请重新生成计划。每个学习预算是本次章节学习与练习时间，不是学完整套课程。</p>
    ${summary.unscheduled_skills.length ? `<p class="warn">当前计划未安排：${esc(summary.unscheduled_skills.join('、'))}。可增加每周学习时间或准备周期后重新生成。</p>` : ''}
    ${tasks.length ? `<div class="rp-now"><strong>当前推荐行动</strong> ${esc(tasks[0].title)}</div>` : ''}
    <h2>按技能准备：资料 · 题目 · 实操</h2>`;
  const skills = [...new Set(tasks.map((t) => t.skill))];
  const practiceSkill = skills.includes('运营指标') ? '运营指标' : skills[0];
  for (const skill of skills) {
    const group = tasks.filter((t) => t.skill === skill);
    const withResource = group.find((t) => t.resource_url);
    const questions = group.filter((t) => t.question).slice(0, 2);
    html += `<div class="card skill-card"><h2>${esc(skill)}</h2>
      ${withResource ? `<p>准备资料：${linkHtml(withResource.resource_url, withResource.resource_title)}<br><span class="muted">${esc(withResource.resource_creator)}</span></p>` : '<p class="muted">暂无核验过的匹配资料，已安排成果练习。</p>'}
      ${questions.map((t) => `<p>练习题：${linkHtml(t.question.url, t.question.title)}<br><span class="muted">${esc(t.question.kind)} · ${esc(t.question.source || '')}</span></p>`).join('')}
      <details><summary>任务验收标准</summary>
        ${group.map((t) => `<p><strong>${esc(t.title)}</strong><br>${esc(t.acceptance)}<br><span class="muted">${esc(t.matching_reason)}</span></p>`).join('')}
      </details>
      ${skill === practiceSkill ? practiceEntryHtml() : ''}
    </div>`;
  }
  return html;
}

function prepTasksHtml() {
  if (!state.plan) {
    return `<h1>执行任务</h1><p class="info">目前还没有学习计划。去「计划与行动」创建。</p>
      <button type="button" class="primary" data-go="prep" data-prep="计划与行动">去计划与行动 →</button>`;
  }
  const { tasks } = state.plan;
  return `<h1>执行任务</h1>
    <div class="card"><h2>学习路径 · 来源可核对</h2>
    <div class="table-wrap"><table><thead><tr><th>技能</th><th>类型</th><th>任务</th><th>分钟</th><th>截止日期</th><th>资源链接</th></tr></thead>
    <tbody>${tasks.map((t) => `<tr><td>${esc(t.skill)}</td><td>${esc(t.kind)}</td><td>${esc(t.title)}</td><td class="num">${t.minutes}</td><td class="num">${esc(t.due)}</td>
      <td>${t.resource_url ? `${linkHtml(t.resource_url, t.resource_title)}<br><span class="muted">${esc(t.resource_creator)}</span>` : '无'}</td></tr>`).join('')}</tbody></table></div>
    <details><summary>任务验收标准与匹配依据</summary>
      ${tasks.map((t) => `<p><strong>${esc(t.title)}</strong><br>${esc(t.acceptance)}${t.question ? `<br>${linkHtml(t.question.url, `原题：${t.question.title}（${t.question.source || ''}）`)}` : ''}<br><span class="muted">${esc(t.matching_reason)}</span></p>`).join('')}
    </details>
    <p class="muted">资源链接指向原站；是否需登录、付费及地区限制以原站为准。计划保存在本浏览器。</p></div>`;
}

/* ---------- 课程与题目（按当前 JD 自动匹配） ---------- */

function prepCoursesHtml() {
  const reqs = Array.isArray(state.jd.requirements) ? state.jd.requirements : null;
  let html = `<h1>为目标岗位寻找学习资源</h1>`;
  if (!reqs || !reqs.length) {
    html += `<p class="info">先载入或解析一份 JD。这里会按每项能力自动匹配课程、资料和对应的实践任务。</p>
      <button type="button" class="primary" data-go="jd">去看岗位 →</button>`;
    return html;
  }
  const matches = matchedResources(reqs);
  const curatedCount = matches.filter((item) => item.course).length;
  const practiceCount = matches.length - curatedCount;
  html += `<div class="card solid resource-intro">
    <p class="kicker">具体出处 · 按需学习 · 不用搜索页凑数</p>
    <p>已按当前岗位的 <strong>${matches.length}</strong> 项能力整理：${curatedCount} 项有出处可核对的具体资料，${practiceCount} 项暂无合适课程，改为岗位专项实践。</p>
    <p class="muted">这里只使用官方文档、机构课程或已核对发布者与章节的视频；目录核查不等于完整教学质量评审。社区经验贴和泛搜索页不会自动加入。</p>
  </div>`;
  for (const match of matches) {
    const course = match.course;
    const question = course ? (QUESTIONS[course.key] || null) : null;
    html += `<div class="card resource-card">
      <p class="resource-kicker">${esc(match.priority)} · ${course ? esc(course.kind) : '原创岗位实践'}</p>
      <h2>${esc(match.skill)}</h2>
      <p>${esc(match.reason)}</p>
      ${course ? `<p class="resource-actions">${linkHtml(course.url, `打开资料：${course.title}`)}</p>
        <p><strong>先学什么：</strong>${esc(course.focus)}</p>
        <p class="muted">${esc(course.creator)} · 建议本次投入 ${course.minutes} 分钟；这是学习预算，不是整课时长。</p>
        <p class="resource-quality"><strong>质量依据：</strong>${esc(course.quality)}</p>
        ${match.supplements.length ? `<details><summary>补充资料（${match.supplements.length}）</summary>${match.supplements.map((item) => `<p>${linkHtml(item.url, item.title)}<br><span class="muted">${esc(item.creator)} · ${esc(item.kind)}</span></p>`).join('')}</details>` : ''}`
        : `<div class="resource-gap"><strong>暂不推荐来源不明的课程</strong><p>${esc(match.practice)}</p></div>`}
      ${question ? `<p><strong>配套练习：</strong>${linkHtml(question.url, question.title)}<br><span class="muted">${esc(question.source)} · ${question.minutes} 分钟</span></p>` : ''}
      <details><summary>匹配依据：当前 JD 原文</summary><p class="evidence">${esc(match.evidence || match.detail)}</p></details>
    </div>`;
  }
  html += `<details><summary>资源使用说明</summary>
    <p>官方资料用于查准概念，机构课程用于建立方法，已核对章节只学标注部分。遇到收费、登录或地区限制请先确认；没有合适课程时，直接完成可检查的岗位实践，不收藏低质搜索页。</p></details>`;
  return html;
}

/* ---------- 岗位实操 ---------- */

function funnelRows() {
  const totals = STAGES.map((_, i) => Object.values(CHANNELS).reduce((a, c) => a + c[i], 0));
  return [...Object.entries(CHANNELS), ['合计', totals]];
}

function funnelTableHtml() {
  return `<div class="table-wrap"><table id="funnel-table">
    <thead><tr><th>渠道</th>${STAGES.map((s) => `<th>${esc(s)}</th>`).join('')}</tr></thead>
    <tbody>${funnelRows().map(([name, counts]) => `<tr><td>${esc(name)}</td>${counts.map((c) => `<td class="num">${c.toLocaleString('zh-CN')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function renderWork() {
  const d = state.practiceDraft;
  const planTask = state.plan && state.plan.tasks.length
    ? (state.plan.tasks.find((t) => t.kind !== '学习') || state.plan.tasks[0]) : null;
  const attempt = latestAttempt();
  $('work-body').innerHTML = `<p class="kicker">教学演示 · 导师、任务与数据均为模拟</p>
    <h1>实习工作台 · 转化漏斗分析</h1>
    <p class="muted">教学演示：导师、任务与数据均为模拟，不代表真实企业或真实用户数据。</p>
    <div class="card solid mentor-card">
      <h2>导师任务</h2>
      <p>你是增长团队的数据分析实习生。请对比两个获客渠道近一周的注册漏斗，找出渠道 B 相对渠道 A 流失异常严重的环节，计算该环节两个渠道的转化率，并提出可能原因与验证方法。</p>
      <p class="muted">交付要求：定位一个环节；给出两个转化率数字；把原因写成可检验的假设；给出至少一种验证方法。</p>
      ${planTask ? `<p class="muted">来自当前计划：${esc(planTask.title)}（${esc(planTask.due)} 截止）</p>` : ''}
    </div>
    <div class="card">
      <h2>练习数据 · 近一周注册漏斗（模拟数据）</h2>
      ${funnelTableHtml()}
      <p class="muted">口径提示：环节转化率 = 下一环节人数 ÷ 上一环节人数 × 100%。请逐环节自行计算，不要除以最初访问量。</p>
    </div>
    <form class="card solid" id="submission">
      <label>渠道 B 流失异常严重的环节
        <select id="step">${STEPS.map((s, i) => `<option value="${i}" ${Number(d.step) === i ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select>
      </label>
      <div class="controls">
        <label>该环节渠道 B 转化率（%）
          <input id="rate-b" type="number" min="0" max="100" step="0.1" value="${esc(d.rate_b)}">
        </label>
        <label>该环节渠道 A 转化率（%）
          <input id="rate-a" type="number" min="0" max="100" step="0.1" value="${esc(d.rate_a)}">
        </label>
      </div>
      <label>可能原因（写成可检验的假设）
        <textarea id="cause" maxlength="1000" rows="3">${esc(d.cause)}</textarea>
      </label>
      <label>验证方法（如何证实或排除假设）
        <textarea id="verification" maxlength="1000" rows="3">${esc(d.verification)}</textarea>
      </label>
      ${workError ? '<p class="error" id="form-error">请填写可能原因和验证方法后再提交。</p>' : ''}
      <button type="submit" class="primary">提交分析结论</button>
    </form>
    <div id="feedback">${attempt
      ? feedbackCardHtml(attempt) + `<p class="muted">重新提交会保存为新的练习记录。</p>
        <div class="row-buttons"><button type="button" data-go="prep" data-prep="计划与行动">返回学习计划 →</button>
        <button type="button" class="primary" data-go="feedback">查看反馈 →</button></div>`
      : '<p class="info">提交后这里会显示导师反馈。</p>'}</div>`;
}

function feedbackCardHtml(attempt) {
  const fb = attempt.feedback;
  const sub = attempt.submission;
  const [strengths, fixes] = feedbackPoints(fb);
  return `<div class="card solid feedback-card"><h2>导师反馈（规则点评，非 AI 生成）</h2>
    <p class="muted">本次得分</p><div class="score">${fb.score} / 100</div>
    ${strengths.length ? `<h2>做得好的地方</h2><ul class="points good">${strengths.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>` : ''}
    ${fixes.length ? `<h2>需要修正</h2><ul class="points fixes">${fixes.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>` : ''}
    <h2>下一步建议</h2><ul class="points">${fb.next_steps.map((c) => `<li>${esc(NEXT_STEP_TEXTS[c])}</li>`).join('')}</ul>
    <details><summary>查看本次提交</summary>
      <p>环节：${esc(sub.step_label)}</p>
      <p>渠道 B 转化率：${esc(sub.rate_b)}% · 渠道 A 转化率：${esc(sub.rate_a)}%</p>
      <p>可能原因：${esc(sub.cause)}</p>
      <p>验证方法：${esc(sub.verification)}</p>
    </details>
    <p class="muted">提交时间：${esc(attempt.created_at)}</p></div>`;
}

function submitPractice() {
  const d = state.practiceDraft;
  const cause = String(d.cause || '').trim();
  const verification = String(d.verification || '').trim();
  if (!cause || !verification) { workError = true; render(); return; }
  workError = false;
  const step = Number(d.step) || 0;
  const submission = { step, step_label: STEPS[step], rate_b: Number(d.rate_b) || 0, rate_a: Number(d.rate_a) || 0, cause, verification };
  const feedback = grade(submission);
  state.attempts.unshift({ created_at: nowStamp(), submission, feedback });
  state.feedbackIndex = 0;
  save();
  render();
  const box = $('feedback');
  if (box) box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------- 查看反馈 ---------- */

function renderFeedbackPage() {
  if (!state.attempts.length) {
    $('feedback-body').innerHTML = `<h1>查看反馈</h1>
      <p class="info">还没有练习提交。完成一次岗位实操后，这里会显示评分依据与下一步。</p>
      <button type="button" class="primary" data-go="work">去岗位实操 →</button>`;
    return;
  }
  const idx = Math.min(Math.max(Number(state.feedbackIndex) || 0, 0), state.attempts.length - 1);
  const attempt = state.attempts[idx];
  $('feedback-body').innerHTML = `<h1>查看反馈</h1>
    ${idx > 0 ? `<p class="muted">正在查看第 ${idx + 1} 条历史记录（共 ${state.attempts.length} 条）。</p>` : ''}
    ${feedbackCardHtml(attempt)}
    <div class="row-buttons">
      <button type="button" class="primary" data-go="prep" data-prep="计划与行动">返回学习计划 →</button>
      <button type="button" data-go="work">继续练习 →</button>
    </div>`;
}

/* ---------- 狗蛋伴侣 ---------- */

function buildContext() {
  const parts = ['当前页面：' + VIEW_LABELS[state.view]];
  if (state.jd && state.jd.raw) {
    parts.push('岗位：' + (state.jd.raw.split('\n')[0] || '').slice(0, 60));
    if (Array.isArray(state.jd.requirements)) parts.push('JD 能力要求：' + state.jd.requirements.map((r) => r.skill).join('、'));
  }
  if (state.plan && state.plan.tasks.length) {
    parts.push('计划任务：' + state.plan.tasks.slice(0, 8).map((t) => `${t.due} ${t.title}（${t.minutes}分钟）`).join('；'));
    parts.push('当前应做：' + state.plan.tasks[0].title);
  }
  const attempt = latestAttempt();
  if (state.view === 'work' || attempt) {
    parts.push('练习数据（模拟）：' + JSON.stringify(funnelRows().map(([name, counts]) => ({ 渠道: name, ...Object.fromEntries(STAGES.map((s, i) => [s, counts[i]])) }))));
    parts.push('环节列表：' + STEPS.join('；'));
    parts.push('口径：环节转化率 = 下一环节人数 ÷ 上一环节人数 × 100%');
  }
  if (attempt) {
    parts.push('最近提交：' + JSON.stringify(attempt.submission));
    parts.push('规则反馈：' + JSON.stringify(attempt.feedback));
    parts.push('最近得分：' + attempt.feedback.score + '/100');
    const [strengths, fixes] = feedbackPoints(attempt.feedback);
    parts.push('做得好的地方：' + strengths.join('；'));
    parts.push('需要修正：' + fixes.join('；'));
    parts.push('下一步建议：' + attempt.feedback.next_steps.map((c) => NEXT_STEP_TEXTS[c]).join('；'));
  }
  if (Array.isArray(state.jd.requirements) && state.jd.requirements.length) {
    const resources = matchedResources(state.jd.requirements).slice(0, 8);
    parts.push('匹配学习安排：' + resources.map((item) => item.course
      ? `${item.skill} → 已核对资料《${item.course.title}》`
      : `${item.skill} → 暂无合适课程，岗位实践：${item.practice}`).join('；'));
  }
  if (dollNote) parts.push(`笔记《${dollNote.title}》：${dollNote.body}`);
  return parts.join('\n').slice(0, 12000);
}

function resumeMemoryLabel() {
  const memory = dollResume.memory;
  if (!memory || typeof memory !== 'object') return '';
  const count = (key) => Array.isArray(memory[key]) ? memory[key].length : 0;
  return `简历记忆已建立:教育 ${count('education')} 项 · 技能 ${count('skills')} 项 · 经历 ${count('experiences')} 项 · 项目 ${count('projects')} 项。可更换 JD 后直接重新优化。`;
}

function renderResumeMemory() {
  const note = $('doll-resume-memory');
  const label = resumeMemoryLabel();
  note.hidden = !label;
  note.textContent = label;
  $('doll-resume-text').placeholder = dollResume.memory
    ? '已建立结构化记忆;粘贴新简历可重新建立,或直接按当前 JD 重新优化。'
    : '上传 PDF/DOCX/TXT/MD,或粘贴简历全文…';
  document.querySelector('[data-action="doll-resume-send"]').textContent = dollResume.memory ? '按当前 JD 重新优化' : '建立记忆并按 JD 优化';
}

function renderDoll() {
  const open = !!state.doll.open;
  const panel = $('doll-panel');
  panel.hidden = !open;
  document.body.classList.toggle('doll-open', open);
  $('doll-launcher').setAttribute('aria-expanded', String(open));
  if (!open) return;
  const noteLine = $('doll-note-line');
  noteLine.hidden = !dollNote;
  if (dollNote) noteLine.textContent = `正在结合笔记：《${dollNote.title}》`;
  const msgs = state.doll.messages;
  const statusLine = $('doll-status');
  if (statusLine) statusLine.textContent = `陪伴中 · 本次 ${msgs.length} 条`;
  $('doll-quicks').innerHTML = Object.entries(VIEW_LABELS).map(([view, label]) =>
    `<button type="button" data-go="${view}" ${view === state.view ? 'aria-current="page"' : ''}>${esc(label)}</button>`).join('');
  $('doll-messages').innerHTML =
    (msgs.length ? msgs.map((m) => `<div class="msg ${m.role === 'user' ? 'user' : 'assistant'}${m.kind === 'resume' ? ' resume' : ''}">${esc(m.content)}</div>`).join('')
      : '<div class="doll-empty"><p>你好，我是狗蛋。可以问我岗位、学习计划或练习数据的问题；也可以从「学习笔记」带着笔记来对话。</p></div>')
    + (dollBusy ? '<div class="msg assistant thinking"><span class="think-dots" aria-hidden="true"><i></i><i></i><i></i></span><span>狗蛋正在思考…</span></div>' : '');
  const resumeMode = state.doll.mode === 'resume';
  $('doll-modes').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === state.doll.mode)));
  $('doll-resume-box').hidden = !resumeMode;
  $('doll-chat-row').hidden = resumeMode;
  const rTarget = $('doll-resume-target');
  if (rTarget.value !== dollResume.target) rTarget.value = dollResume.target;
  const rText = $('doll-resume-text');
  if (rText.value !== dollResume.text) rText.value = dollResume.text;
  renderResumeMemory();
  const input = $('doll-input');
  if (input.value !== state.doll.draft) input.value = state.doll.draft;
  const list = $('doll-messages');
  list.scrollTop = list.scrollHeight;
}

async function sendDoll() {
  const question = String(state.doll.draft || '').trim();
  if (!question || dollBusy) return;
  state.doll.messages.push({ role: 'user', content: question });
  state.doll.draft = '';
  dollBusy = true;
  save();
  renderDoll();
  const context = buildContext();
  const history = state.doll.messages.slice(0, -1).slice(-6);
  const data = await post('tutor', { context, history, question });
  const reply = data && data.ok === true && isStr(data.reply) && data.reply.trim() ? data.reply : AI_NOTICE;
  state.doll.messages.push({ role: 'assistant', content: reply });
  dollBusy = false;
  save();
  renderDoll();
}

async function sendDollResume() {
  if (dollBusy) return;
  const text = (dollResume.text || '').trim();
  const memory = !text && dollResume.memory && typeof dollResume.memory === 'object' ? dollResume.memory : null;
  if (!memory && text.length < 20) {
    state.doll.messages.push({ role: 'assistant', content: '简历内容太短啦,把完整简历(教育、经历、技能)上传或粘贴进来我再分析。' });
    save();
    renderDoll();
    return;
  }
  const target = (dollResume.target || '').trim();
  const jdText = String(state.jd.draft || '').trim();
  state.doll.messages.push({ role: 'user', content: memory
    ? '按当前 JD 重新优化简历' + (target ? `(目标:${target})` : '') + (jdText ? ' · 使用已建立的简历记忆' : '')
    : '建立简历记忆并按 JD 优化' + (target ? `(目标:${target})` : '') + (jdText ? ' · 已附当前 JD' : '') });
  dollBusy = true;
  save();
  renderDoll();
  const data = await post('resume', memory ? { memory, target, jd: jdText.slice(0, 12000) } : { resume: text, target, jd: jdText.slice(0, 12000) });
  const nextMemory = data && data.memory && typeof data.memory === 'object' && !Array.isArray(data.memory) ? data.memory : null;
  const resumeReply = data && data.ok === true && isStr(data.reply) && data.reply.trim() ? data.reply : AI_NOTICE;
  if (data && data.ok === true) {
    if (nextMemory) dollResume.memory = nextMemory;
    dollResume.text = '';
    $('doll-resume-file-name').textContent = (dollResume.sourceName ? dollResume.sourceName + ' · ' : '') + '已建立结构化简历记忆';
  }
  state.doll.messages.push({ role: 'assistant', kind: 'resume', content: resumeReply });
  dollBusy = false;
  save();
  renderDoll();
}

document.addEventListener('change', (e) => {
  if (e.target.id !== 'doll-resume-file') return;
  const file = e.target.files && e.target.files[0];
  e.target.value = '';
  if (!file) return;
  const nameEl = $('doll-resume-file-name');
  nameEl.textContent = '解析中…';
  dollResume.memory = null;
  dollResume.text = '';
  dollResume.sourceName = file.name;
  renderDoll();
  extractResumeFile(file).then((text) => {
    dollResume.text = text;
    nameEl.textContent = file.name + ' · 已提取 ' + text.length + ' 字,可编辑后建立简历记忆';
    renderDoll();
  }).catch((err) => {
    nameEl.textContent = err && err.message ? err.message : '解析失败,请改用 TXT/MD 或粘贴全文。';
  });
});

/* ---------- 事件绑定（委托，视图重绘后仍然有效） ---------- */

document.addEventListener('click', (e) => {
  const go = e.target.closest('[data-go]');
  if (go) { navigate(go.dataset.go, go.dataset.prep, go.dataset.space); return; }
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  if (action === 'space-nav') { state.spaceNav = btn.dataset.nav; save(); render(); }
  else if (action === 'prep-nav') { state.prepNav = btn.dataset.nav; save(); render(); }
  else if (action === 'demo-load') { state.jd.draft = JD_TEXT; navigate('jd'); parseJd(JD_TEXT); }
  else if (action === 'jd-parse') { parseJd(state.jd.draft); }
  else if (action === 'make-plan') {
    const reqs = state.jd.requirements;
    if (!Array.isArray(reqs) || !reqs.length) { planMsg = '先在「看岗位」解析一份 JD。'; render(); return; }
    const hours = Number(state.sliders.hours) || 8;
    const days = Number(state.sliders.days) || 14;
    const { tasks, summary } = planTasks(reqs, hours, days);
    if (!tasks.length) { planMsg = '没有可安排的任务：请检查课程缺口或增加时间预算。未覆盖原有计划。'; }
    else {
      state.plan = { hours, days, tasks, summary, created_at: nowStamp() };
      planMsg = `已保存 ${tasks.length} 个任务。`;
    }
    save(); render();
  }
  else if (action === 'note-save') {
    const title = $('note-title').value.trim();
    const body = $('note-body').value.trim();
    if (!title || !body) { noteError = '请填写标题和内容。'; render(); return; }
    noteError = '';
    if (editingNoteId) {
      const note = state.notes.find((n) => n.id === editingNoteId);
      if (note) { note.title = title; note.body = body; note.updated_at = nowStamp(); }
      editingNoteId = null;
    } else {
      state.notes.unshift({ id: 'n' + Date.now() + Math.random().toString(36).slice(2, 7), title, body, created_at: nowStamp(), updated_at: nowStamp() });
    }
    save(); render();
  }
  else if (action === 'note-cancel') { editingNoteId = null; noteError = ''; render(); }
  else if (action === 'note-edit') { editingNoteId = btn.dataset.id; noteError = ''; render(); }
  else if (action === 'note-delete') {
    state.notes = state.notes.filter((n) => n.id !== btn.dataset.id);
    if (editingNoteId === btn.dataset.id) editingNoteId = null;
    if (dollNote && dollNote.id === btn.dataset.id) dollNote = null;
    save(); render();
  }
  else if (action === 'note-chat') {
    dollNote = state.notes.find((n) => n.id === btn.dataset.id) || null;
    state.doll.open = true;
    save(); render();
  }
  else if (action === 'history-view') {
    state.feedbackIndex = Number(btn.dataset.index) || 0;
    navigate('feedback');
  }
  else if (action === 'doll-close') { state.doll.open = false; dollNote = null; save(); renderDoll(); }
  else if (action === 'doll-send') { sendDoll(); }
  else if (action === 'doll-mode') { state.doll.mode = btn.dataset.mode === 'resume' ? 'resume' : 'chat'; save(); renderDoll(); }
  else if (action === 'doll-resume-send') { sendDollResume(); }
});

$('doll-launcher').addEventListener('click', () => { state.doll.open = !state.doll.open; save(); renderDoll(); });

document.addEventListener('submit', (e) => {
  if (e.target.id === 'submission') { e.preventDefault(); submitPractice(); }
  if (e.target.id === 'note-form') e.preventDefault();
});

function syncDraftInput(el) {
  const id = el.id;
  if (id === 'hours' || id === 'days') {
    state.sliders[id] = Number(el.value);
    const out = $(id + '-out');
    if (out) out.textContent = el.value;
    save();
  } else if (id === 'jd-input') { state.jd.draft = el.value; save(); }
  else if (id === 'step') { state.practiceDraft.step = Number(el.value); save(); }
  else if (id === 'rate-b') { state.practiceDraft.rate_b = el.value; save(); }
  else if (id === 'rate-a') { state.practiceDraft.rate_a = el.value; save(); }
  else if (id === 'cause') { state.practiceDraft.cause = el.value; save(); }
  else if (id === 'verification') { state.practiceDraft.verification = el.value; save(); }
  else if (id === 'doll-input') { state.doll.draft = el.value; save(); }
  else if (id === 'doll-resume-target') { dollResume.target = el.value; }
  else if (id === 'doll-resume-text') {
    if (el.value !== dollResume.text) {
      dollResume.text = el.value;
      if (dollResume.memory) {
        dollResume.memory = null;
        $('doll-resume-file-name').textContent = '原文已修改,将重新建立简历记忆';
        renderResumeMemory();
      }
    }
  }
}

document.addEventListener('input', (e) => syncDraftInput(e.target));
document.addEventListener('change', (e) => { if (e.target.id === 'step') syncDraftInput(e.target); });
document.addEventListener('keydown', (e) => {
  if (e.target.id === 'doll-input' && e.key === 'Enter' && !e.isComposing) { e.preventDefault(); sendDoll(); }
});

/* ---------- 启动 ---------- */

if (!storageOk) $('storage-warning').hidden = false;
if (!VIEW_LABELS[state.view]) state.view = 'space';
render();