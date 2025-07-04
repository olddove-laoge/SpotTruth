from openai import OpenAI

class KeywordAnalyzer200Lines:
    # 文件路径常量
    DEFAULT_INPUT_PATH = r'AIGC\Comment_crawling_and_analysis\reviews.txt'
    DEFAULT_OUTPUT_PATH = r'AIGC\Comparison_of_similar_products_and_external_link_information\keywords_200lines.csv'
    
    def __init__(self, api_key, base_url="https://api.deepseek.com", model="deepseek-chat"):
        """
        初始化关键词分析器（200行版本）
        :param api_key: OpenAI API密钥
        :param base_url: API基础URL
        :param model: 使用的模型名称
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = (
            "你是一个产品雷点分析工具，请提取10个商品评价雷点关键词以及它们出现的频次"
            "（出现判定可以稍微宽一些），还有关键词对应的典型差评（1-3条），只能输出"
            "这几个，要满足'关键词,频次,典型差评1，典型差评2（如有，若没有用空格代替），"
            "典型差评3（同典型差评2）'的格式，同一关键词下典型评论不能相同，其他任何东西都不要输出"
        )

    def analyze(self, input_path=None, output_path=None):
        """
        执行关键词分析（仅读取前200行）
        :param input_path: 输入文件路径
        :param output_path: 输出文件路径
        """
        input_path = input_path or self.DEFAULT_INPUT_PATH
        output_path = output_path or self.DEFAULT_OUTPUT_PATH
        
        # 读取输入文件前200行
        with open(input_path, 'r', encoding='utf-8') as file:
            lines = []
            for i, line in enumerate(file):
                if i >= 200:  # 只读取前200行
                    break
                lines.append(line)
            text = ''.join(lines)
        
        # 调用API分析
        response = self._call_api(text)
        
        # 写入结果
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(response)

    def _call_api(self, text):
        """
        内部方法：调用API进行分析
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=1.0,
            stream=False
        )
        return response.choices[0].message.content

# 直接执行功能
if __name__ == "__main__":
    analyzer = KeywordAnalyzer200Lines(api_key="sk-959db6c460bb4ace9a066bd4c065981e")
    analyzer.analyze()  # 使用默认路径执行
