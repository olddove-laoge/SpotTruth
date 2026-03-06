# 05_sarcasm_detector.py
"""
Step 5: 反讽/阴阳怪气识别模块
- 规则初筛 + LLM复核
"""

import re

# 可疑模式（可能包含阴阳怪气）
SUSPICIOUS_PATTERNS = [
    r"好.*啊", r"真是.*啊", r"太.*了", r"感动.*",
    r"竟然.*", r"居然.*", r"太好了.*", r"不错.*",
    r"棒.*呢", r"优秀.*呢", r"厉害.*啊", r"还好.*吧",
    r"勉强.*", r"还行.*吧", r"，也就.*", r"所谓的",
    r"服了.*", r"醉.*", r"呵呵.*", r"笑了.*",
]


def is_suspicious(text: str) -> bool:
    """规则初筛：判断是否可疑"""
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def llm_judge_sarcasm(text: str) -> str:
    """LLM判断是否为阴阳怪气"""
    # TODO: 调用LLM API
    pass


def detect_sarcasm(text: str) -> dict:
    """主函数：反讽识别"""
    is_sus = is_suspicious(text)
    
    if not is_sus:
        return {"is_suspicious": False, "type": "正常"}
    
    result = llm_judge_sarcasm(text)
    return {"is_suspicious": True, "type": result}


def batch_detect(comments: list) -> list:
    """批量检测"""
    results = []
    suspicious_batch = []
    
    for i, comment in enumerate(comments):
        if is_suspicious(comment):
            suspicious_batch.append((i, comment))
    
    if suspicious_batch:
        # TODO: 批量调用LLM
        pass
    
    return results
