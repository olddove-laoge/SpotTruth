import os
from keywords import KeywordAnalyzer

class BatchKeywordAnalyzer:
    def __init__(self, api_key):
        """
        初始化批量分析器
        :param api_key: OpenAI API密钥
        """
        self.analyzer = KeywordAnalyzer(api_key=api_key)
        
        # 输入输出目录路径
        self.input_dir = r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_comments'
        self.output_dir = r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_keywords'
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def analyze_all(self):
        """
        分析输入目录下的所有txt文件
        """
        # 遍历输入目录下的所有txt文件
        for filename in os.listdir(self.input_dir):
            if filename.endswith('.txt'):
                try:
                    # 构建完整文件路径
                    input_path = os.path.join(self.input_dir, filename)
                    output_filename = filename.replace('.txt', '_keywords.csv')
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    # 执行分析
                    self.analyzer.analyze(input_path=input_path, output_path=output_path)
                    print(f"成功分析文件: {filename}")
                    
                except Exception as e:
                    print(f"分析文件 {filename} 时出错: {str(e)}")

if __name__ == "__main__":
    # 使用预设API密钥初始化
    analyzer = BatchKeywordAnalyzer(api_key="sk-959db6c460bb4ace9a066bd4c065981e")
    analyzer.analyze_all()
