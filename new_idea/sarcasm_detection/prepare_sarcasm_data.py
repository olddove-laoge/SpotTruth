# prepare_sarcasm_data.py
"""
准备讽刺检测训练数据
- 从10个品类各抽取100条正常评论（50好评+50差评）
- 混合阴阳怪气评论
"""

import json
import os
import random

random.seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "D:/C_data/SpotTruth/new_idea/data"
IRONY_FILE = os.path.join(SCRIPT_DIR, "data", "irony_corpus.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "data", "sarcasm_train.json")

# 品类列表（对应data/下的文件夹名）
CATEGORIES = [
    "book", "tablet", "electronics", "fruit", "shampoo", 
    "dairy", "clothing", "water_heater", "hotel", "computer", "phone"
]

# 每个品类抽取数量
SAMPLES_PER_CATEGORY = 100  # 50好评 + 50差评


def load_category_data(category):
    """加载品类数据"""
    train_file = os.path.join(DATA_DIR, category, "train.json")
    if not os.path.exists(train_file):
        print(f"  [警告] {category} 不存在，跳过")
        return []
    
    with open(train_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def sample_balanced(data, n_pos, n_neg):
    """平衡采样好评和差评"""
    pos_samples = [d for d in data if d.get('label', 0) == 1]
    neg_samples = [d for d in data if d.get('label', 0) == 0]
    
    # 随机采样
    random.shuffle(pos_samples)
    random.shuffle(neg_samples)
    
    pos_selected = pos_samples[:n_pos]
    neg_selected = neg_samples[:n_neg]
    
    return pos_selected + neg_selected


def main():
    print("=" * 50)
    print("准备讽刺检测训练数据")
    print("=" * 50)
    
    # 加载阴阳怪气数据
    print("\n[1] 加载阴阳怪气数据...")
    with open(IRONY_FILE, 'r', encoding='utf-8') as f:
        irony_data = json.load(f)
    
    # 标记为1（讽刺）
    for item in irony_data:
        item['label'] = 1  # 1 = 讽刺
        item['category'] = 'irony'
    
    print(f"    阴阳怪气评论: {len(irony_data)}条")
    
    # 加载正常评论
    print("\n[2] 加载正常评论...")
    normal_samples = []
    
    for cat in CATEGORIES:
        print(f"    处理 {cat}...", end=" ")
        data = load_category_data(cat)
        if not data:
            print("跳过")
            continue
        
        # 统计好评差评数量
        pos_count = sum(1 for d in data if d.get('label', 0) == 1)
        neg_count = sum(1 for d in data if d.get('label', 0) == 0)
        
        # 平衡采样：50好评 + 50差评
        n_per_class = SAMPLES_PER_CATEGORY // 2
        samples = sample_balanced(data, n_per_class, n_per_class)
        
        # 添加品类标签
        for item in samples:
            item['label'] = 0  # 0 = 正常
            item['category'] = cat
        
        normal_samples.extend(samples)
        print(f"{len(samples)}条 (好评{sum(1 for s in samples if s['label']==1)}, 差评{sum(1 for s in samples if s['label']==0)})")
    
    print(f"\n    正常评论总计: {len(normal_samples)}条")
    
    # 合并数据
    print("\n[3] 合并数据...")
    all_data = irony_data + normal_samples
    random.shuffle(all_data)
    
    # 重新编号
    for i, item in enumerate(all_data):
        item['id'] = i + 1
    
    # 统计
    n_irony = sum(1 for d in all_data if d['label'] == 1)
    n_normal = sum(1 for d in all_data if d['label'] == 0)
    
    print(f"    总计: {len(all_data)}条")
    print(f"    - 阴阳怪气(标签=1): {n_irony}条")
    print(f"    - 正常评论(标签=0): {n_normal}条")
    print(f"    - 正常评论中: 好评{len(normal_samples)//2}条, 差评{len(normal_samples)//2}条")
    
    # 保存
    print(f"\n[4] 保存到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print("\n完成!")
    
    # 打印样本
    print("\n" + "=" * 50)
    print("样本预览:")
    print("=" * 50)
    for i, item in enumerate(all_data[:5]):
        label = "阴阳怪气" if item['label'] == 1 else "正常"
        cat = item.get('category', 'unknown')
        text = item.get('text', '')[:40]
        print(f"{i+1}. [{label}] ({cat}) {text}...")


if __name__ == "__main__":
    main()
