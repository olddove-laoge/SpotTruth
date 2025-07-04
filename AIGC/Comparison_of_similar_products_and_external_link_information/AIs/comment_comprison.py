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

import csv


    


def sync_vivogpt():
    params = {
        'requestId': str(uuid.uuid4())
    }
    print('requestId:', params['requestId'])

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\analysis_result_200lines_stats.csv', 'r', encoding='utf-8') as f:
        productA_stats = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\keywords_200lines.csv', 'r', encoding='utf-8') as f:
        productA_keywords = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_comments_analysis\prod1_comment_analysis_stats.csv', 'r', encoding='utf-8') as f:
        productB_stats = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_keywords\prod1_comment_keywords.csv', 'r', encoding='utf-8') as f:
        productB_keywords = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_comments_analysis\prod2_comment_analysis_stats.csv', 'r', encoding='utf-8') as f:
        productC_stats = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_keywords\prod2_comment_keywords.csv', 'r', encoding='utf-8') as f:
        productC_keywords = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_comments_analysis\prod3_comment_analysis_stats.csv', 'r', encoding='utf-8') as f:
        productD_stats = f.read().strip()

    with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\relative_product_keywords\prod3_comment_keywords.csv', 'r', encoding='utf-8') as f:
        productD_keywords = f.read().strip()

    data = {
        'prompt':  (
            "产品A："
            "情感分布"
            + productA_stats +
            "差评关键词详情"
            + productA_keywords +
            "产品B："
            "情感分布"
            + productB_stats +
            "差评关键词详情"
            + productB_keywords +
            "产品C："
            "情感分布"
            + productC_stats +
            "差评关键词详情"
            + productC_keywords +
            "产品D："
            "情感分布"
            + productD_stats +
            "差评关键词详情"
            + productD_keywords
        ),
        'model': 'vivo-BlueLM-TB-Pro',
        'sessionId': str(uuid.uuid4()),
        'systemPrompt':(
            """
            # 角色与任务
            **你是一个专业的产品评论比较器。** 你的核心任务是根据用户提供的四个**同品类产品**的评论分析数据（前200条评论的情感分布和差评关键词详情），进行客观、详尽的对比分析，最终给出清晰的**产品优劣对比**和基于数据的**购买建议**。

            # 输入数据格式 (用户将严格按此提供四个产品的数据)
            ## 1. 产品情感分布 (每个产品独立提供)
            情感类型,数量,占比
            正面,76,38.0%
            中性,89,44.5%
            负面,35,17.5%
            总计,200,100%

            text

            ## 2. 差评关键词详情 (每个产品独立提供)
            关键词,出现频次,典型评论 (包含原文片段)
            [关键词1],[频次],[评论片段1],[评论片段2],...
            [关键词2],[频次],[评论片段1],[评论片段2],...
            （示例关键词可能是：故障、破损、异味、褪色、死机、漏液、做工差、客服差...）

            text

            # 你的工作流程与要求
            1.  **数据接收：** 等待用户依次提供四个产品的完整数据集（情感分布 + 差评关键词）。确认数据完整后开始分析。
            2.  **核心对比分析 (全品类通用维度)：**
                *   **负面评价率对比：** 直接比较四个产品的`负面`评价占比（如`17.5%`），这是核心满意度指标。
                *   **差评严重性分析：**
                    *   **高频问题识别：** 找出每个产品出现频次最高的1-3个差评关键词（如`故障(12次)`）。高频问题反映普遍缺陷。
                    *   **严重问题评估：** **重点识别涉及以下领域的差评关键词（权重最高）**：
                        *   **安全风险**（如：爆炸、漏电、起火、有毒、过敏）
                        *   **核心功能失效**（如：无法开机、不制冷、根本不能用）
                        *   **质量缺陷**（如：严重破损、断裂、开胶、短期内损坏）
                        *   **健康危害**（如：食物变质、含异物、材料有毒）
                        *   **欺诈/严重不符**（如：假货、与描述完全不符）
                    *   **典型评论解读：** 分析`典型评论`片段，理解差评的具体表现、用户痛苦程度和问题场景（如：是偶发故障还是设计缺陷？是主观体验差还是客观质量问题？）。
                *   **问题类型归类：** 将差评关键词归类到主要问题类型，对比各产品问题分布：
                    *   **致命问题**（安全/核心功能失效/健康危害/欺诈）
                    *   **严重质量问题**（材料/工艺/耐用性缺陷）
                    *   **体验问题**（使用不便、舒适度差、异味、外观瑕疵）
                    *   **服务问题**（物流慢、客服差、退货难）
                    *   **主观不满**（不符合个人喜好、性价比低）
                *   **正面/中性评价参考：** 高`正面`占比（>40%）可能表示产品有忠实用户；高`中性`占比可能反映评价分化或缺乏亮点。
            3.  **优劣对比总结：**
                *   清晰列出每个产品的**核心优势**（如：负面率最低、无安全/功能问题报告）和**主要劣势**（如：负面率最高、高频出现致命问题关键词）。
                *   明确指出在**差评率控制**和**问题严重性**方面表现**最优**和**最差**的产品。
            4.  **购买建议与原因：**
                *   **给出明确的推荐结论**（如：“推荐优先级：产品A > 产品C > 产品B；强烈不推荐产品D”）。
                *   **严格基于数据说明原因**：
                    *   *“推荐产品A因其负面率最低(12%)，且差评中无安全风险或核心功能失效报告。”*
                    *   *“不推荐产品D因其负面率最高(28%)，且高频出现‘故障’(15次)和‘爆炸风险’(3次)等致命问题关键词。”*
                    *   *“产品B虽负面率中等(18%)，但其差评集中在‘做工粗糙’(8次)等质量问题，需谨慎考虑。”*

            # 输出格式要求
            *   **结构清晰：** 按“核心分析 -> 优劣总结 -> 购买建议及原因”组织。
            *   **数据驱动：** **必须引用**具体数据（负面率%、关键词、频次、典型评论关键信息）。
            *   **客观中立：** 仅基于用户提供的数据分析，不做主观推测。
            *   **品类适配：** 根据品类特性调整问题权重（如电器重安全，服装重材质，食品重卫生）。
            *   **语言精炼：** 避免冗余，直击要点。

            **请等待用户提供四个同品类产品的完整数据，接收完毕后立即开始分析。**
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
            with open(r'AIGC\Comparison_of_similar_products_and_external_link_information\analysis_report.md', 'w', encoding='utf-8') as md_file:
                md_file.write(content)
                print('analysis_report.md saved')
    else:
        print(response.status_code, response.text)
    end_time = time.time()
    timecost = end_time - start_time
    print('请求耗时: %.2f秒' % timecost)


if __name__ == '__main__':
    sync_vivogpt()
