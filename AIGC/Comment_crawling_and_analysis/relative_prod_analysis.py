import os
from batch_processor import analyze_reviews

def process_all_comments():
    # 定义输入和输出目录
    input_dir = os.path.join('AIGC', 'Comparison_of_similar_products_and_external_link_information', 'relative_product_comments')
    output_dir = os.path.join('AIGC', 'Comparison_of_similar_products_and_external_link_information', 'relative_product_comments_analysis')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 遍历输入目录中的所有txt文件
    for filename in os.listdir(input_dir):
        if filename.endswith('.txt'):
            # 构建输入文件路径
            input_file = os.path.join(input_dir, filename)
            
            # 构建输出文件路径
            base_name = os.path.splitext(filename)[0]
            output_file = os.path.join(output_dir, f"{base_name}_analysis.csv")
            
            # 处理文件
            print(f"\n正在处理文件: {filename}")
            analyze_reviews(input_file, output_file)
            print(f"处理完成，结果已保存到: {output_file}")

if __name__ == '__main__':
    process_all_comments()
    print("\n所有文件处理完成！")
