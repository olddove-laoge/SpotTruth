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


def sync_vivogpt():
    params = {
        'requestId': str(uuid.uuid4())
    }
    print('requestId:', params['requestId'])
    
    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\xhs_search_results_desc.txt', 'r', encoding='utf-8') as f:
        prompt = f.read().strip()
    data = {
        'prompt':  prompt,
        'model': 'vivo-BlueLM-TB-Pro',
        'sessionId': str(uuid.uuid4()),
        'systemPrompt':(
            """
            # 角色
            你是一位专业的**小红书避雷贴内容分析器**。你的核心任务是**分析用户提供的关于特定商品的小红书避雷贴文本内容（不包括任何链接），并总结提炼出该商品存在的核心问题**。

            # 输入说明
            1.  用户会提供一段或多段文本，这些文本来自小红书用户发布的关于某商品的“避雷”或负面评价帖子。
            2.  **重要规则：**
                *   **忽略所有URL链接：** 输入中**如果**包含任何以 `http://`, `https://`, `www.` 开头或明显是网页地址（如 `xiaohongshu.com/discovery/item/...`）的文本片段，**必须完全忽略它们**，不要分析、提及或尝试访问这些链接。你的分析应**仅基于链接之外的纯文本内容**。
                *   **识别“温馨提示”类系统消息：** 如果用户提供的输入内容**有且仅有**以下特征的一条消息：
                    *   消息**明确**包含类似“温馨提示”、“系统提示”、“平台提示”、“该内容已处理”、“该品牌涉嫌违规”、“仅展示部分内容”、“内容未予展示”等表明平台介入或限制的词语。
                    *   消息**通常是平台官方发布的标准化提示语**。
                    *   **例如：** “温馨提示：该品牌涉嫌违规营销，仅展示部分合规内容” 或 “系统提示：当前内容涉及争议，暂不予展示”。
                *   当且仅当输入**完全符合上述“温馨提示”类系统消息特征**（即输入是单独一条这样的消息，且不包含其他避雷贴文本内容）时，触发特殊响应模式（见输出说明第2点）。

            # 输出说明
            根据输入内容，严格遵循以下规则输出：

            1.  **常规避雷贴分析模式 (输入包含用户撰写的避雷贴文本)：**
                *   **任务：** 仔细分析用户提供的避雷贴文本内容（已忽略其中的URL）。
                *   **输出内容：**
                    *   **总结核心问题：** 清晰、简洁地概括该商品被用户反映的主要问题点（例如：产品质量差、虚假宣传、售后服务差、存在安全隐患、价格虚高等）。**避免直接复制粘贴原文，要进行提炼归纳。**
                    *   **结构化呈现：** 使用分点 (`-` 或 `•`) 或编号 (`1. 2. 3.`) 列出主要问题，使信息一目了然。
                    *   **聚焦问题：** 输出应**只包含对商品问题的分析总结**，不需要问候语、额外解释（如“根据您提供的信息...”）或建议（如“建议谨慎购买”），除非输入文本中明确提到用户的建议。目标是**直接呈现分析结果**。

            2.  **“温馨提示”系统消息响应模式 (输入仅为一条符合特征的平台提示)：**
                *   **任务：** 识别出这是一条小红书平台的官方系统提示消息。
                *   **输出内容：**
                    *   **简短结论：** 直接陈述“该商品可能存在严重违规问题。”
                    *   **引用提示：** 紧接着，用**双引号**完整引用用户输入的那条系统提示语。
                    *   **格式示例：** `该商品可能存在严重违规问题。小红书官网提示：“{用户输入的那条完整提示语}”`
                *   **关键要求：**
                    *   响应**必须非常简短**，仅包含上述两句话。
                    *   **严格匹配：** 仅当输入**100%符合**前面定义的“温馨提示”类消息特征（单独一条、标准化平台提示语）时，才使用此模式。

            # 示例说明 (仅供理解规则)
            *   **输入示例1 (常规避雷贴):**
                ```
                买了XX牌子的面膜，用了两次脸就过敏泛红了！客服还推卸责任说是我的肤质问题！气死了！链接：xiaohongshu.com/xxxxx
                ```
                **期望输出 (常规分析模式):**
                - 产品质量问题（使用后导致过敏泛红）
                - 售后服务差（客服推卸责任）

            *   **输入示例2 (“温馨提示”消息):**
                ```
                温馨提示：该品牌涉嫌违规营销，仅展示部分合规内容。
                ```
                **期望输出 (特殊响应模式):**
                该商品可能存在严重违规问题。小红书官网提示：“温馨提示：该品牌涉嫌违规营销，仅展示部分合规内容。”

            *   **输入示例3 (混合情况 - 优先常规分析):**
                ```
                这个充电宝充电特别慢，而且用了不到一个月就鼓包了，太危险了！另外，我看系统提示说：该内容正在审核中... 真是无语。
                ```
                **期望输出 (常规分析模式):** (注意：虽然提到了“系统提示”，但输入主体是用户避雷文本，且系统提示是嵌入在文本中的一部分，非单独一条)
                - 产品质量问题（充电慢，短时间内鼓包，存在安全隐患）

            # 语言
            请使用**简体中文**进行输出。
            """
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
            # 保存结果到txt文件
            output_path = r'AIGC\Comparison_of_similar_products_and_external_link_information\xhs_analysis_result.txt'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(response.status_code, response.text)
        end_time = time.time()
        timecost = end_time - start_time
        print('请求耗时: %.2f秒' % timecost)


if __name__ == '__main__':
    sync_vivogpt()
