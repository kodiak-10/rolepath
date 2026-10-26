from __future__ import annotations
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def load_roles():
    return json.loads((DATA_DIR / "roles.json").read_text(encoding="utf-8"))

def load_resources():
    return json.loads((DATA_DIR / "resources.json").read_text(encoding="utf-8"))

def load_questions():
    return json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))

SKILL_ALIASES = {
    "产品思维": ["产品思维", "产品 sense", "产品sense"],
    "AI应用基础": ["AI应用基础", "AI工具使用", "AI 工具使用", "大模型应用基础"],
    "需求分析": ["需求分析", "需求挖掘", "需求调研"],
    "PRD": ["prd", "需求文档", "产品需求文档"],
    "竞品分析": ["竞品分析", "竞品调研", "竞争产品分析"],
    "用户研究": ["用户研究", "用户访谈", "用户调研"],
    "LLM": ["llm", "大语言模型", "大模型"],
    "RAG": ["rag", "检索增强生成", "向量数据库"],
    "Agent": ["agent", "智能体", "tool calling", "工具调用"],
    "SQL": ["sql", "mysql", "数据库查询"],
    "Python": ["python", "pandas"],
    "Excel": ["excel", "数据透视表", "电子表格"],
    "数据分析": ["数据分析", "数据处理", "业务分析", "数据复盘", "产品数据"],
    "数据可视化": ["数据可视化", "可视化", "图表分析", "dashboard"],
    "运营指标": ["运营指标", "转化率", "留存率", "用户增长", "漏斗分析"],
    "原型设计": ["原型设计", "原型制作", "产品原型", "web原型", "web 原型", "原型图", "axure", "figma"],
    "产品设计": ["产品设计", "产品方案"],
    "项目协作": ["项目跟进", "需求评审", "跟进产品需求", "项目管理", "跨团队协调"],
    "AIGC": ["aigc", "ai内容生成", "ai 内容生成", "ai内容生产", "ai 内容生产"],
    "多模态": ["多模态"],
    "内容营销": ["内容营销", "内容运营"],
    "用户运营": ["用户运营", "智能运营工具"],
    "海外业务": ["海外用户", "海外业务", "出海产品", "海外内容营销"],
    "海外社媒": ["海外社媒", "社媒运营"],
    "本地化": ["本地化", "智能翻译"],
    "视频生产": ["视频生产", "视频制作", "视频剪辑"],
    "算法与数据结构": ["算法", "数据结构", "手撕", "手写代码"],
    "Java": ["java", "springboot", "spring boot"],
    "前端开发": ["前端开发", "javascript", "typescript", "react", "vue"],
    "提示词工程": ["prompt engineering", "提示词", "提示工程"],
    "模型评测": ["模型评测", "模型评测与系统化调优", "评测与调优", "评测调优", "幻觉", "输出稳定性"],
    "AI辅助编程": ["vibe coding", "ai辅助编程", "ai 辅助编程"],
    "代码阅读与修改": ["阅读和修改代码", "代码阅读", "代码调试"],
    "HTML": ["html"],
    "API集成": ["api调用", "api 调用", "后端对接", "接口对接"],
    "交互设计": ["交互设计", "交互原型", "用户体验", "交互思呈现"],
    "沟通协作": ["沟通协作", "多方对齐", "跨团队"],
    "软件测试": ["软件测试", "测试用例", "自动化测试"],
}

ALL_SKILLS = list(SKILL_ALIASES)
