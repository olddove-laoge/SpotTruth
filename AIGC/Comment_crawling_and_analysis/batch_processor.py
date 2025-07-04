# 批量评论分析处理器(仅使用snownlp)
import csv
from snownlp_analyzer import predict_sentiment

def analyze_reviews(input_file, output_file):
    """
    批量处理评论文件(仅使用snownlp)
    :param input_file: 输入txt文件路径
    :param output_file: 输出csv文件路径
    """
    # 使用snownlp分析器
    predictor = predict_sentiment
    
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        reviews = [line.strip() for line in f if line.strip()]
    
    # 处理每条评论
    results = []
    for review in reviews:
        try:
            result = predictor(review)
            results.append({
                '评价': review,
                '评论类型': result['sentiment'],
                '情感得分': result['raw_score'],
                '置信度': result['confidence']
            })
        except Exception as e:
            print(f"处理评论失败: {review[:30]}... 错误: {str(e)}")
            results.append({
                '评价': review,
                '评论类型': '错误',
                '情感得分': 0,
                '置信度': 0
            })
    
    # 写入CSV文件
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['评价', '评论类型', '情感得分', '置信度'])
        writer.writeheader()
        writer.writerows(results)
    
    # 统计情感分布
    stats = {'正面':0, '中性':0, '负面':0}
    for result in results:
        if result['评论类型'] in stats:
            stats[result['评论类型']] += 1
    
    total = len(results)
    print(f"\n处理完成，共分析{total}条评论，结果已保存到{output_file}")
    print("\n=== 情感分布统计 ===")
    print(f"正面评价: {stats['正面']}条 ({stats['正面']/total:.1%})")
    print(f"中性评价: {stats['中性']}条 ({stats['中性']/total:.1%})")
    print(f"负面评价: {stats['负面']}条 ({stats['负面']/total:.1%})")
    
    # 将情感分布统计写入CSV文件
    stats_file = output_file.replace('.csv', '_stats.csv')
    with open(stats_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['情感类型', '数量', '占比'])
        writer.writerow(['正面', stats['正面'], f"{stats['正面']/total:.1%}"])
        writer.writerow(['中性', stats['中性'], f"{stats['中性']/total:.1%}"])
        writer.writerow(['负面', stats['负面'], f"{stats['负面']/total:.1%}"])
        writer.writerow(['总计', total, '100%'])
    print(f"情感分布统计已保存到{stats_file}")

if __name__ == '__main__':
    # 使用示例
    input_txt = r'AIGC\Comment_crawling_and_analysis\reviews.txt'  # 输入文件路径
    output_csv = r'AIGC\Comment_crawling_and_analysis\analysis_result.csv'  # 输出文件路径
    
    analyze_reviews(input_txt, output_csv)
