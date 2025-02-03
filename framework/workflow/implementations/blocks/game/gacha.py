import random
from typing import Any, Dict
from framework.workflow.core.block import Block
from framework.workflow.core.workflow.input_output import Input, Output
from framework.ioc.container import DependencyContainer
from framework.im.message import IMMessage, TextMessage

class GachaSimulator(Block):
    """抽卡模拟器 block"""
    
    def __init__(self, container: DependencyContainer, rates: Dict[str, float] = None):
        inputs = {
            "message": Input("message", IMMessage, "Input message containing gacha command")
        }
        outputs = {
            "response": Output("response", IMMessage, "Response message with gacha results")
        }
        super().__init__("gacha_simulator", inputs, outputs)
        
        # 默认抽卡概率
        self.rates = rates or {
            "SSR": 0.03,  # 3%
            "SR": 0.12,   # 12%
            "R": 0.85     # 85%
        }
        
    def _single_pull(self) -> str:
        rand = random.random()
        cumulative = 0
        for rarity, rate in self.rates.items():
            cumulative += rate
            if rand <= cumulative:
                return rarity
        return list(self.rates.keys())[-1]  # 保底
        
    def execute(self, message: IMMessage) -> Dict[str, Any]:
        # 解析命令
        command = message.content
        is_ten_pull = "十连" in command
        pulls = 10 if is_ten_pull else 1
        
        # 抽卡
        results = [self._single_pull() for _ in range(pulls)]
        
        # 生成结果统计
        stats = {rarity: results.count(rarity) for rarity in self.rates.keys()}
        
        # 生成详细信息
        details = []
        for rarity in results:
            if rarity == "SSR":
                details.append("🌟 SSR")
            elif rarity == "SR":
                details.append("✨ SR")
            else:
                details.append("⭐ R")
                
        result_text = f"抽卡结果: {'、'.join(details)}"
        stats_text = "统计:\n" + "\n".join(f"{rarity}: {count}" for rarity, count in stats.items())
        
        return {
            "response": IMMessage(
                sender="<@bot>",
                message_elements=[
                    TextMessage(result_text),
                    TextMessage(stats_text)
                ]
            )
        } 