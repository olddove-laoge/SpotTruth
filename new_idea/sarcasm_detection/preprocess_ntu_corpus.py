# preprocess_ntu_corpus.py
"""
预处理NTU讽刺语料库
- 繁体转简体
- 解析XML格式
- 输出JSON格式
"""

import re
import json
import os
from opencc import OpenCC

# 初始化繁体转简体
cc = OpenCC('t2s')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "data", "NTU_Irony_Corpus.txt")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "data", "irony_corpus.json")


def extract_text_from_message(message_tag):
    """从<message>标签中提取纯文本，去除所有XML标签"""
    # 去除所有<xxx>标签，保留标签内的文本
    text = message_tag
    
    # 移除所有XML标签及其属性
    text = re.sub(r'<[^>]+>', '', text)
    
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def parse_corpus(input_file):
    """解析语料库文件"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 跳过文件头部注释（以##开头的行）
    lines = content.split('\n')
    content = '\n'.join(line for line in lines if not line.startswith('##'))
    
    # 提取所有<message>标签内容
    pattern = r'<message>(.*?)</message>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    print(f"找到 {len(matches)} 条消息")
    
    corpus = []
    for i, match in enumerate(matches):
        # 提取纯文本
        text = extract_text_from_message(match)
        
        # 繁体转简体
        text_simplified = cc.convert(text)
        
        # 跳过空文本
        if len(text_simplified) < 5:
            continue
        
        corpus.append({
            "id": i + 1,
            "text": text_simplified,
            "label": 1,  # 1 = 讽刺/阴阳怪气
            "source": "NTU_Irony_Corpus"
        })
    
    return corpus


def main():
    print("=" * 50)
    print("NTU讽刺语料库预处理")
    print("=" * 50)
    
    # 解析语料库
    corpus = parse_corpus(INPUT_FILE)
    
    print(f"\n处理完成，共 {len(corpus)} 条讽刺语料")
    
    # 打印样本
    print("\n样本预览:")
    for i, item in enumerate(corpus[:3]):
        print(f"{i+1}. {item['text'][:50]}...")
    
    # 保存为JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
