"""记忆模块

短期记忆：当前文书的处理过程记录
长期记忆：跨文件的统计规律（编码分布、常见异常、策略有效性）
"""
from dataclasses import dataclass, field
from collections import defaultdict
import time


@dataclass
class StepRecord:
    """单步执行记录"""
    tool_id: str
    tool_name: str
    success: bool
    duration_seconds: float
    output_summary: str
    error: str = ""
    retry_count: int = 0
    strategy_used: str = ""

    def to_dict(self):
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "output_summary": self.output_summary,
            "error": self.error,
            "retry_count": self.retry_count,
            "strategy_used": self.strategy_used,
        }


@dataclass
class DocumentMemory:
    """单份文书的短期记忆"""
    filename: str
    quality_score: float
    anomalies: list
    doc_type: str
    trial_level: str

    actions: list = field(default_factory=list)       # 执行过的动作列表
    decisions: list = field(default_factory=list)      # Agent的决策记录
    errors: list = field(default_factory=list)         # 错误记录
    strategy_changes: list = field(default_factory=list)  # 策略变更记录
    started_at: float = 0.0
    completed_at: float = 0.0

    def post_init(self):
        if self.started_at == 0.0:
            self.started_at = time.time()

    def record_decision(self, thought: str, tools_selected: list):
        """记录一次决策"""
        self.decisions.append({
            "timestamp": time.time(),
            "thought": thought,
            "tools_selected": tools_selected,
        })

    def record_action(self, step: StepRecord):
        """记录一次工具执行"""
        self.actions.append(step.to_dict())

    def record_error(self, tool_id: str, error: str):
        """记录一次错误"""
        self.errors.append({
            "timestamp": time.time(),
            "tool_id": tool_id,
            "error": error,
        })

    def record_strategy_change(self, reason: str, old_strategy: str, new_strategy: str):
        """记录策略变更"""
        self.strategy_changes.append({
            "timestamp": time.time(),
            "reason": reason,
            "old_strategy": old_strategy,
            "new_strategy": new_strategy,
        })

    def to_dict(self):
        return {
            "filename": self.filename,
            "quality_score": self.quality_score,
            "anomalies": self.anomalies,
            "doc_type": self.doc_type,
            "trial_level": self.trial_level,
            "actions": self.actions,
            "decisions": self.decisions,
            "errors": self.errors,
            "strategy_changes": self.strategy_changes,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_actions": len(self.actions),
            "total_errors": len(self.errors),
        }


class LongTermMemory:
    """跨文件的长期统计记忆（全局单例）"""

    def __init__(self):
        self.total_docs_processed: int = 0
        self.encoding_distribution: dict[str, int] = defaultdict(int)
        self.doc_type_distribution: dict[str, int] = defaultdict(int)
        self.common_anomalies: dict[str, int] = defaultdict(int)
        self.strategy_effectiveness: dict[str, float] = {}  # 策略名 → 成功率
        self.total_llm_calls: int = 0
        self.total_cost_estimate: float = 0.0

    def update_from_doc(self, doc_memory: DocumentMemory):
        """从一份文书的处理记录中更新长期记忆"""
        self.total_docs_processed += 1
        self.encoding_distribution[doc_memory.doc_type] += 1

        for anomaly in doc_memory.anomalies:
            self.common_anomalies[anomaly] += 1

    def get_encoding_priority(self) -> list[str]:
        """根据历史统计返回编码尝试优先级"""
        sorted_encodings = sorted(
            self.encoding_distribution.items(),
            key=lambda x: x[1], reverse=True
        )
        return [enc for enc, _ in sorted_encodings]

    def get_anomaly_heatmap(self) -> dict:
        """返回异常热力图数据"""
        return dict(self.common_anomalies)

    def get_summary(self) -> dict:
        return {
            "total_docs_processed": self.total_docs_processed,
            "encoding_distribution": dict(self.encoding_distribution),
            "doc_type_distribution": dict(self.doc_type_distribution),
            "common_anomalies": dict(self.common_anomalies),
            "total_llm_calls": self.total_llm_calls,
            "total_cost_estimate": self.total_cost_estimate,
        }


# 全局单例
global_memory = LongTermMemory()
