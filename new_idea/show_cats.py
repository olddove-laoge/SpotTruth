import pandas as pd
df = pd.read_csv('data/train.csv', encoding='utf-8')
cats = df['cat'].unique().tolist()
for c in cats:
    print(repr(c))
