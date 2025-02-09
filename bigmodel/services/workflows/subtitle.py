import asyncio
from typing import Dict, Any, List

from bigmodel.prompts.chinese_parser import ChinesePydanticOutputParser
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from pydantic import BaseModel, Field

from bigmodel.models.subtitle import SubtitleInput, AssociationResult, PointSummary, SubtitleOutput
from bigmodel.prompts.base import PromptTemplateRegistry
from bigmodel.prompts.constants import PromptTemplateType
from bigmodel.services.workflows.base import BaseWorkflow
from bigmodel.services.workflows.workflow_registry import WorkflowRegistry
from langchain.callbacks import get_openai_callback
from langchain.callbacks.tracers.logging import LoggingCallbackHandler
import logging


@WorkflowRegistry.register("subtitle_summary")
class SubtitleWorkflow(BaseWorkflow):
    # 1. 定义关联性分析的输出结构
    class AssociationAnalysis(BaseModel):
        """定义期望的输出结构"""
        association: bool = Field(description="是否关联，当分数超过80分时为true，否则为false")
        score: float = Field(description="关联分数，范围0-100，50-80分表示有关联，80-90分表示强关联，90-100分表示超强关联")
        explanation: str = Field(description="关联性分析说明，解释关联程度和原因")

    # 2. 定义关键点提取的输出结构
    class KeyPoints(BaseModel):
        """定义关键点输出结构"""
        key_points: List[str] = Field(description="关键点列表")

    # 3. 定义单点总结的输出结构
    class PointSummaryOutput(BaseModel):
        """定义单点总结输出结构"""
        point_summary: str = Field(description="总结内容")

    # 创建解析器实例
    association_parser = ChinesePydanticOutputParser(pydantic_object=AssociationAnalysis)
    points_parser = ChinesePydanticOutputParser(pydantic_object=KeyPoints)
    summary_parser = ChinesePydanticOutputParser(pydantic_object=PointSummaryOutput)

    def __init__(self, *args, **kwargs):
        # 首先调用父类的初始化方法，确保传递所有参数
        super().__init__(*args, **kwargs)
        # 配置日志记录器
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('langchain')
        # 创建回调处理器
        self.callback_handler = LoggingCallbackHandler(logger)

    async def _analyze_association(self, input_params: SubtitleInput) -> AssociationResult:
        """分析字幕关联性"""
        try:
            with get_openai_callback() as cb:
                # 1. 获取格式说明并添加中文说明
                format_instructions = self.association_parser.get_format_instructions()

                # 2. 创建提示词模板
                template = PromptTemplateRegistry.get_template(PromptTemplateType.SUBTITLE_ASSOCIATION)
                
                # 3. 准备输入参数，包含格式说明
                params = {
                    **input_params.model_dump(),
                    "输出格式要求": format_instructions
                }
                print("association 输入参数：", params)

                # 4. 创建处理链,使用 LoggingCallbackHandler
                chain = (
                        template.prompt |
                        self.llm.with_config({"callbacks": [self.callback_handler]}) |
                        self.association_parser
                )

                # 5. 执行链并获取结果
                result1 = await chain.ainvoke(params)
                
                # 打印回调统计信息
                print(f"Total Tokens: {cb.total_tokens}")
                print(f"Prompt Tokens: {cb.prompt_tokens}")
                print(f"Completion Tokens: {cb.completion_tokens}")
                print(f"Total Cost (USD): ${cb.total_cost}")

                if not result1:
                    raise ValueError("LLM返回结果为空")

                return AssociationResult(
                    association=result1.association,
                    score=result1.score,
                    explanation=result1.explanation
                )

        except Exception as e:
            print(f"解析关联性结果出错: {str(e)}")
            # 返回默认值，包含所有必需字段
            return AssociationResult(
                association=False, 
                score=0.0, 
                explanation="处理过程中发生错误"
            )

    def _split_points(self, text: str) -> List[str]:
        """将文本分割为关键点列表"""
        return [point.strip() for point in text.split("\n") if point.strip()]

    async def _extract_points(self, input_params: SubtitleInput) -> List[str]:
        """提取关键点"""
        try:
            with get_openai_callback() as cb:
                # 1. 获取格式说明
                format_instructions = self.points_parser.get_format_instructions()

                # 2. 创建提示词模板
                template = PromptTemplateRegistry.get_template(PromptTemplateType.SUBTITLE_POINT)
                
                # 3. 准备输入参数，包含格式说明
                params = {
                    **input_params.model_dump(),
                    "输出格式要求:": format_instructions
                }

                print("extract_point 输入参数：", params)
                # 4. 创建处理链,使用 LoggingCallbackHandler
                chain = (
                        template.prompt |
                        self.llm.with_config({"callbacks": [self.callback_handler]}) |
                        self.points_parser
                )

                # 5. 执行链并获取结果
                result2 = await chain.ainvoke(params)
                
                # 打印回调统计信息
                print(f"Total Tokens: {cb.total_tokens}")
                print(f"Prompt Tokens: {cb.prompt_tokens}")
                print(f"Completion Tokens: {cb.completion_tokens}")
                print(f"Total Cost (USD): ${cb.total_cost}")

                if not result2 or not result2.key_point:
                    raise ValueError("未能提取到有效的关键点")

                return result2.key_point

        except Exception as e:
            print(f"提取关键点出错: {str(e)}")
            return ["解析错误"]

    async def _summarize_point(self, input_params: SubtitleInput, point: str) -> PointSummary:
        """总结单个关键点"""
        try:
            with get_openai_callback() as cb:
                # 1. 获取格式说明
                format_instructions = self.summary_parser.get_format_instructions()
                
                # 2. 创建提示词模板
                template = PromptTemplateRegistry.get_template(PromptTemplateType.SUBTITLE_SUMMARY)
                
                # 3. 准备输入参数，包含格式说明
                params = {
                    **input_params.model_dump(),
                    "point": point,
                    "输出格式要求:": format_instructions
                }
                

                # 4. 创建处理链,使用 LoggingCallbackHandler
                chain = (
                        template.prompt |
                        self.llm.with_config({"callbacks": [self.callback_handler]}) |
                        self.summary_parser
                )

                # 5. 执行链并获取结果
                result3 = await chain.ainvoke(params)
                
                # 打印回调统计信息
                print(f"Total Tokens: {cb.total_tokens}")
                print(f"Prompt Tokens: {cb.prompt_tokens}")
                print(f"Completion Tokens: {cb.completion_tokens}")
                print(f"Total Cost (USD): ${cb.total_cost}")

                if not result3:
                    raise ValueError("LLM返回结果为空")

                return PointSummary(
                    point=point,
                    summary=result3.point_summary,
                    key_elements=result3.key_elements,
                    context_relevance=result3.context_relevance
                )

        except Exception as e:
            print(f"总结关键点出错: {str(e)}")
            # 返回包含所有必需字段的默认值
            return PointSummary(
                point=point,
                summary="处理过程中发生错误",
                key_elements=["无法提取关键要素"],
                context_relevance="无法分析上下文关联"
            )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行字幕处理工作流"""
        try:
            # 验证并转换输入参数
            input_params = SubtitleInput(**params)

            # 并行执行关联性分析和关键点提取
            # association_task = asyncio.create_task(self._analyze_association(input_params))
            points_task = asyncio.create_task(self._extract_points(input_params))

            # 等待两个任务完成
            # association_result, key_points = await asyncio.gather(association_task, points_task)
            key_points = await asyncio.gather(points_task)
            # 使用信号量控制并发数量
            semaphore = asyncio.Semaphore(2)  # 限制最大并发数为 2

            async def process_point(point: str) -> PointSummary:
                async with semaphore:
                    return await self._summarize_point(input_params, point)

            # 创建所有任务但控制并发执行
            summary_tasks = [
                process_point(point)
                for point in key_points
            ]

            # 等待所有总结任务完成
            point_summaries = await asyncio.gather(*summary_tasks)

            # 合并所有总结
            summarized_subtitle = "\n".join(ps.summary for ps in point_summaries)

            # 构建输出结果
            output = SubtitleOutput(
                # association_result=association_result,
                key_points=key_points,
                point_summaries=point_summaries,
                summarized_subtitle=summarized_subtitle
            )

            return output.model_dump()

        except Exception as e:
            # 记录错误日志
            print(f"字幕处理工作流执行出错: {str(e)}")
            # 返回错误信息
            raise ValueError(f"字幕处理工作流执行失败: {str(e)}")
