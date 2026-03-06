# 03_data_preprocessor.py
"""
Step 3: 数据预处理
- 清洗、分词、生成各品类训练数据
"""

import pandas as pd
import json
import re
import os

CATEGORIES = ["book", "tablet", "phone", "fruit", "shampoo", "dairy", "clothing", "computer", "water_heater", "hotel"]

# 中文到英文映射
CAT_MAPPING = {
    "书籍": "book",
    "平板": "tablet",
    "手机": "phone",
    "水果": "fruit",
    "洗发水": "shampoo",
    "奶制品": "dairy",
    "衣服": "clothing",
    "计算机": "computer",
    "热水器": "water_heater",
    "酒店": "hotel",
}


def clean_text(text: str) -> str:
    """文本清洗"""
    if pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_train_dev(df: pd.DataFrame, train_ratio=0.8):
    """划分训练集/验证集"""
    train = df.sample(frac=train_ratio, random_state=42).copy()
    dev = df.drop(train.index).copy()
    return train, dev


def process_category(cat_name: str, input_path="data/train.csv"):
    """处理单个品类的数据"""
    # 获取中文类别名
    chinese_name = [k for k, v in CAT_MAPPING.items() if v == cat_name][0]
    
    df = pd.read_csv(input_path, encoding='utf-8')
    cat_df = df[df['cat'] == chinese_name].copy()
    
    if len(cat_df) == 0:
        print(f"警告: {cat_name} 数据为空")
        return
    
    cat_df['review'] = cat_df['review'].apply(clean_text)
    cat_df = cat_df[cat_df['review'].str.len() > 0]
    cat_df = cat_df[['review', 'label']].rename(columns={'review': 'text'})
    
    train, dev = split_train_dev(cat_df, train_ratio=0.8)
    
    output_dir = f"data/{cat_name}"
    os.makedirs(output_dir, exist_ok=True)
    
    train_list = train.to_dict('records')
    dev_list = dev.to_dict('records')
    
    with open(f"{output_dir}/train.json", 'w', encoding='utf-8') as f:
        json.dump(train_list, f, ensure_ascii=False, indent=2)
    with open(f"{output_dir}/dev.json", 'w', encoding='utf-8') as f:
        json.dump(dev_list, f, ensure_ascii=False, indent=2)
    
    print(f"{cat_name}: {len(train_list)} train, {len(dev_list)} dev")


if __name__ == "__main__":
    for cat in CATEGORIES:
        process_category(cat)
    print("\n所有品类数据处理完成！")
