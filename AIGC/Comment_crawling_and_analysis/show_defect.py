import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import sys

class KeywordVisualizer:
    def __init__(self, file_path, expected_rows=10, figsize=(20, 7)):
        """初始化可视化器
        file_path: CSV文件路径
        expected_rows: 预期处理的行数（默认10行）
        figsize: 图表尺寸（默认20×7）
        """
        self.file_path = file_path
        self.expected_rows = expected_rows
        self.figsize = figsize
        self.df = None
        self.fig = None
        self.wordcloud = None
        
        # 配置绘图参数
        self._configure_plt_settings()
        # 加载数据
        self._load_data()

    def _configure_plt_settings(self):
        """配置绘图参数"""
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

    def _load_data(self):
        """加载并校验数据"""
        try:
            self.df = pd.read_csv(self.file_path, 
                                header=None, 
                                usecols=[0,1], 
                                names=['关键词', '出现次数'])
        except FileNotFoundError:
            raise Exception(f"文件 {self.file_path} 未找到，请检查路径")
        except pd.errors.ParserError:
            raise Exception("CSV文件解析错误，请检查文件格式")

        # 数据行数校验
        actual_rows = len(self.df)
        if actual_rows < self.expected_rows:
            print(f"警告：文件包含 {actual_rows} 行数据（预期至少{self.expected_rows}行）")
        elif actual_rows > self.expected_rows:
            print(f"提示：使用前{self.expected_rows}行（共{actual_rows}行）")
            self.df = self.df.head(self.expected_rows)

    def visualize(self, separate=True):
        """生成可视化图表
        :param separate: 是否生成单独的图表，默认为False生成复合图表
        """
        if separate:
            # 生成单独图表
            self.bar_fig = plt.figure(figsize=(10, 7))
            self._draw_bar_chart(self.bar_fig.add_subplot(111))
            
            self.pie_fig = plt.figure(figsize=(10, 7))
            self._draw_pie_chart(self.pie_fig.add_subplot(111))
            
            self.wordcloud_fig = plt.figure(figsize=(10, 7))
            self._draw_wordcloud(self.wordcloud_fig.add_subplot(111))
            
            return self.bar_fig, self.pie_fig, self.wordcloud_fig
        else:
            # 生成复合图表
            self.fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=self.figsize)
            self._draw_bar_chart(ax1)
            self._draw_pie_chart(ax2)
            self._draw_wordcloud(ax3)
            plt.tight_layout()
            return self.fig

    def _draw_bar_chart(self, ax):
        """绘制柱状图"""
        bars = ax.bar(self.df['关键词'], self.df['出现次数'], 
                     color='#1f77b4', edgecolor='black')
        ax.set(title='关键词出现次数统计', 
              xlabel='关键词', 
              ylabel='出现次数')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                       xy=(bar.get_x() + bar.get_width()/2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom')

    def _draw_pie_chart(self, ax):
        """绘制饼图"""
        wedges, texts, autotexts = ax.pie(
            self.df['出现次数'],
            labels=self.df['关键词'],
            autopct=lambda p: f'{p:.1f}%\n({int(p*sum(self.df["出现次数"])/100)})',
            startangle=90,
            colors=plt.cm.tab20c.colors,
            textprops={'fontsize': 9},
            wedgeprops={'edgecolor': 'w', 'linewidth': 1.2}
        )
        ax.set(title='关键词出现比例分布')
        ax.axis('equal')
        ax.legend(wedges, self.df['关键词'],
                 title="关键词",
                 loc="center left",
                 bbox_to_anchor=(1, 0, 0.5, 1))

    def _draw_wordcloud(self, ax):
        """绘制词云图"""
        word_freq = dict(zip(self.df['关键词'], self.df['出现次数']))
        font_path = 'C:/Windows/Fonts/simhei.ttf'  # Windows系统字体路径
        
        wc = WordCloud(
            font_path=font_path,
            background_color='white',
            width=800,
            height=600,
            max_words=200,
            prefer_horizontal=1.0,
            colormap='tab20c'
        ).generate_from_frequencies(word_freq)
        
        ax.imshow(wc, interpolation='bilinear')
        ax.set(title='关键词词云', xticks=[], yticks=[])
        ax.axis('off')
        self.wordcloud = wc

    def save_plot(self, filename='关键词统计.png', dpi=300, separate=True):
        """保存图表到指定pics目录
        :param separate: 是否分开保存三个图表，默认为False保存复合图表
        """
        import os
        # 确保pics目录存在
        output_dir = r'static'
        os.makedirs(output_dir, exist_ok=True)
        
        if separate:
            # 分开保存三个图表
            if hasattr(self, 'bar_fig'):
                bar_path = os.path.join(output_dir, f"柱状图_{filename}")
                self.bar_fig.savefig(bar_path, dpi=dpi, bbox_inches='tight')
                print(f"柱状图已保存为 {bar_path}")
                
                pie_path = os.path.join(output_dir, f"饼图_{filename}")
                self.pie_fig.savefig(pie_path, dpi=dpi, bbox_inches='tight')
                print(f"饼图已保存为 {pie_path}")
                
                wc_path = os.path.join(output_dir, f"词云_{filename}")
                self.wordcloud_fig.savefig(wc_path, dpi=dpi, bbox_inches='tight')
                print(f"词云图已保存为 {wc_path}")
            else:
                print("请先调用 visualize(separate=True) 方法生成单独图表")
        else:
            # 保存复合图表
            if self.fig:
                save_path = os.path.join(output_dir, filename)
                self.fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
                print(f"复合图表已保存为 {save_path}")
            else:
                print("请先调用 visualize() 方法生成图表")

    def show_data(self):
        """显示前N行数据"""
        print(f"\n使用的数据预览（前{self.expected_rows}行）：")
        print(self.df.head(self.expected_rows))

class SentimentVisualizer:
    def __init__(self, stats_file):
        """初始化情感可视化器"""
        self.stats_file = stats_file
        self.stats_data = None
        self.fig = None
        self._load_data()

    def _load_data(self):
        """加载情感统计数据"""
        try:
            self.stats_data = pd.read_csv(self.stats_file)
        except Exception as e:
            raise Exception(f"加载情感统计文件失败: {str(e)}")

    def draw_sentiment_pie(self):
        """绘制情感占比饼图"""
        labels = self.stats_data['情感类型'][:-1]  # 排除总计行
        sizes = self.stats_data['数量'][:-1]
        colors = ['#66b3ff', '#99ff99', '#ff9999']
        
        self.fig = plt.figure(figsize=(8, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%',
                startangle=90, colors=colors,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        plt.title('评论情感分布', fontsize=15)
        plt.axis('equal')
        return self.fig

    def save_plot(self, filename='情感分布.png', dpi=300):
        """保存情感分布图"""
        import os
        output_dir = r'AIGC\Comment_crawling_and_analysis\pics'
        os.makedirs(output_dir, exist_ok=True)
        
        if self.fig:
            save_path = os.path.join(output_dir, filename)
            self.fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
            print(f"情感分布图已保存为 {save_path}")
        else:
            print("请先调用 draw_sentiment_pie() 方法生成图表")

if __name__ == "__main__":
    try:
        # 检查wordcloud是否安装
        try:
            from wordcloud import WordCloud
        except ImportError:
            print("请先安装所需库：pip install wordcloud")
            sys.exit(1)

        # 关键词可视化
        keyword_analyzer = KeywordVisualizer(
            file_path=r'AIGC\Comment_crawling_and_analysis\keywords.csv',
            expected_rows=10
        )
        keyword_analyzer.visualize()
        keyword_analyzer.save_plot()
        keyword_analyzer.show_data()

        # 情感统计可视化
        stats_file = r'AIGC\Comment_crawling_and_analysis\analysis_result_stats.csv'
        sentiment_analyzer = SentimentVisualizer(stats_file)
        sentiment_analyzer.draw_sentiment_pie()
        sentiment_analyzer.save_plot()

    except Exception as e:
        print(f"发生错误：{str(e)}")
