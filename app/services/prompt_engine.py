from typing import Dict, Any, List
from app.services.ai_service import ai_service

class PromptEngine:
    """动态提示词生成引擎"""
    
    def __init__(self):
        self.system_prompt = """你是一位拥有课程开发博士学位的资深教学设计师。你的任务是创建一份详细的教案。

请按照以下步骤进行：
1. 深入分析提供的教材内容
2. 仔细审阅教育者的具体要求
3. 将这两者融合成一个连贯的、符合指定格式的教案
4. 在设计每个教学活动时，请解释其背后的教学原理

请确保教案具有以下特点：
- 符合指定的教学模式和教学时长
- 包含清晰的学习目标
- 设计多样化的教学活动
- 提供有效的评估方法
- 考虑差异化教学策略"""

    def assemble_prompt(self, structured_content: Dict[str, Any], user_requirements: Dict[str, Any]) -> str:
        """组装完整的提示词"""
        
        prompt = f"<SYSTEM_INSTRUCTIONS>\n{self.system_prompt}\n</SYSTEM_INSTRUCTIONS>\n\n"
        
        # 添加教材内容
        prompt += "<TEXTBOOK_CONTENT>\n"
        if structured_content:
            prompt += self._format_textbook_content(structured_content)
        prompt += "\n</TEXTBOOK_CONTENT>\n\n"
        
        # 添加用户要求
        prompt += "<EDUCATOR_REQUIREMENTS>\n"
        prompt += self._format_user_requirements(user_requirements)
        prompt += "\n</EDUCATOR_REQUIREMENTS>\n\n"
        
        # 添加输出格式要求
        prompt += "<OUTPUT_FORMAT>\n"
        prompt += self._get_output_format()
        prompt += "\n</OUTPUT_FORMAT>\n\n"
        
        # 添加最终指令
        prompt += "<FINAL_INSTRUCTION>\n"
        prompt += "现在，请开始生成教案。请一步步思考，确保所有要求都得到满足，并解释关键活动的设计思路。"
        prompt += "\n</FINAL_INSTRUCTION>"
        
        return prompt
    
    async def generate_lesson_plan(self, structured_content: Dict[str, Any], user_requirements: Dict[str, Any], provider: str = None) -> str:
        """使用AI生成教案"""
        prompt = self.assemble_prompt(structured_content, user_requirements)
        return await ai_service.generate_text(prompt, provider=provider)
    
    async def analyze_content(self, content: str, provider: str = None) -> Dict[str, Any]:
        """使用AI分析教材内容"""
        return await ai_service.analyze_document(content, provider=provider)
    
    def _format_textbook_content(self, content: Dict[str, Any]) -> str:
        """格式化教材内容"""
        formatted = ""
        
        if "metadata" in content:
            metadata = content["metadata"]
            formatted += f"教材标题: {metadata.get('title', '未知')}\n"
            formatted += f"作者: {metadata.get('author', '未知')}\n"
            formatted += f"主题: {metadata.get('subject', '未知')}\n"
            formatted += f"页数: {metadata.get('page_count', '未知')}\n\n"
        
        if "pages" in content:
            formatted += "教材内容:\n"
            for page in content["pages"]:
                formatted += f"第{page.get('page_number', '?')}页:\n"
                formatted += f"{page.get('text', '')[:500]}...\n\n"
        
        return formatted
    
    def _format_user_requirements(self, requirements: Dict[str, Any]) -> str:
        """格式化用户要求"""
        formatted = ""
        
        formatted += f"年级: {requirements.get('grade_level', '未指定')}\n"
        formatted += f"学科: {requirements.get('subject', '未指定')}\n"
        formatted += f"课程时长: {requirements.get('duration_minutes', '未指定')}分钟\n"
        formatted += f"学习目标: {requirements.get('learning_objectives', '未指定')}\n"
        formatted += f"教学模式: {requirements.get('pedagogical_style', '未指定')}\n"
        
        if requirements.get('activities'):
            formatted += f"期望活动: {', '.join(requirements['activities'])}\n"
        
        if requirements.get('assessment_methods'):
            formatted += f"评估方法: {', '.join(requirements['assessment_methods'])}\n"
        
        if requirements.get('differentiation_strategies'):
            formatted += f"差异化策略: {requirements['differentiation_strategies']}\n"
        
        return formatted
    
    def _get_output_format(self) -> str:
        """获取输出格式要求"""
        return """请使用以下格式输出教案：

# 课程标题

## 学习目标
- [具体的学习目标]

## 所需材料
- [列出所需的教学材料]

## 教学步骤
### 导入 (X分钟)
[导入活动的详细描述]

### 主体教学 (X分钟)
[主要教学内容的详细步骤]

### 总结 (X分钟)
[总结活动的描述]

## 评估方法
[具体的评估方法和标准]

## 差异化教学策略
[针对不同学习者的教学策略]

## 教学反思
[教师可以记录的教学反思要点]"""
