# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_csv('data/train.csv', encoding='utf-8')
print(f"数据量: {len(df)}")
print(f"\n品类分布:")
for cat, cnt in df['cat'].value_counts().items():
    print(f"  {cat}: {cnt}")
print(f"\n标签分布:")
print(df['label'].value_counts())
