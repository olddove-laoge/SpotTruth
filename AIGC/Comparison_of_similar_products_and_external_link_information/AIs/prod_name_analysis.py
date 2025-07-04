import uuid
import time
import requests
from auth_util import gen_sign_headers

# 请替换APP_ID、APP_KEY
APP_ID = '2025254003'
APP_KEY = 'bfJejlCQjoGreteT'
URI = '/vivogpt/completions'
DOMAIN = 'api-ai.vivo.com.cn'
METHOD = 'POST'
def read_prompt_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read().strip()

def sync_vivogpt():
    params = {
        'requestId': str(uuid.uuid4())
    }
    prompt = read_prompt_from_file(r'AIGC\Comment_crawling_and_analysis\product_name.txt')

    print('requestId:', params['requestId'])
    data = {
        'prompt':  prompt,
        'model': 'vivo-BlueLM-TB-Pro',
        'sessionId': str(uuid.uuid4()),
        'systemPrompt':(
            "你是一个电商商品名解析器。你的任务："
            "1.  分析用户输入的淘宝/电商商品标题。"
            "2.  **剥离所有干扰信息**：品牌名、营销词（如“网红”）、地域词（如“云南”“陕西”）、工艺词（如“手工”“现烤”）、规格（如“330ml*6”）、场景词（如“早餐”）、冗余描述（如“解馋”“特产”）。"
            "3.  **保留核心特征**：仅保留定义产品**核心物理属性**（如“冰皮”）、**基础功能**（如“防蓝光”）或**本质品类**的关键词（人群词如“男士”“儿童”仅当其为产品核心属性时保留）。"
            "4.  **输出唯一结果**：直接输出最简化的核心产品名称，**绝对禁止**添加任何括号、注释、解释或符号。"
            ""
            "**铁律规则**："
            "- ✅ **必须保留**：直接影响产品本质的特征词（例：`低糖`碳酸饮料、`辣味`零食）"
            "- ❌ **必须去除**："
            "  - 地域词（云南、陕西、北京等）"
            "  - 品牌/型号（好巧、iPhone）"
            "  - 营销词（营养、网红、清爽解腻）"
            "  - 工艺描述（手工、现烤、生榨）"
            "  - 规格参数（330ml*6、10片装）"
            "  - 场景词（早餐、送礼、办公室）"
            "  - 冗余品类词（当已有更精准词时，“小吃”“糕点”等）"
            "  - 所有非名称文本（括号、箭头、注释等）"
            ""
            "**错误示例 → 正确修复**："
            "× 云南鲜花饼传统糕点 → ✔ 鲜花饼  *(严打地域词“云南”)*"
            "× **云南糕点** *(注释)...* → ✔ 糕点  *(禁止任何额外符号/注释)*"
            ""
            "**电商示例 (输入 → 纯净输出)**："
            "1. 云南鲜花饼传统糕点手工现烤玫瑰饼礼盒特产小吃 → **鲜花饼**"
            "2. 陕西手工烤面筋片辣条麻辣零食 → **辣条**"
            "3. 【清爽解腻】好巧陈皮沙糖桔子生榨果汁汽水330ml*6低糖 → **低糖汽水**"
            "4. 儿童防蓝光眼镜学生护目镜电脑游戏抗辐射 → **防蓝光眼镜**"
            "5. GA男士控油爽肤水祛痘礼盒 → **男士爽肤水**"
            ""
            "**现在请直接输出核心产品名称：**"
        ),
        'extra': {
            'temperature': 1.5
        }
    }
    headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
    headers['Content-Type'] = 'application/json'

    start_time = time.time()
    url = 'https://{}{}'.format(DOMAIN, URI)
    response = requests.post(url, json=data, headers=headers, params=params)

    if response.status_code == 200:
        res_obj = response.json()
        print(f'response:{res_obj}')
        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            print(f'final content:\n{content}')
            # 将结果写入文件
            with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\simple_prod_name.txt', 'w', encoding='utf-8') as f:
                f.write(content)
    else:
        print(response.status_code, response.text)
        with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\simple_prod_name.txt', 'w', encoding='utf-8') as f:
            f.write(f"Error: {response.status_code} - {response.text}")

if __name__ == '__main__':
    sync_vivogpt()
