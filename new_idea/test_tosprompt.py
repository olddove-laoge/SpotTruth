"""
TOSPrompt 讽刺检测模型测试程序

使用方法:
    python test_tosprompt.py                           # 交互模式
    python test_tosprompt.py --text "呵呵太好了"       # 单条测试
    python test_tosprompt.py --file test_data.txt      # 批量测试文件
    python test_tosprompt.py --batch                   # 使用内置测试集
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
from config import paths as paths_config


class TOSPromptTester:
    """TOSPrompt 模型测试器"""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.yes_token_id = None
        self.no_token_id = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print(f"🖥️  使用设备: {self.device}")
        self._load_model()

    def _load_model(self):
        """加载模型"""
        model_path = paths_config.sarcasm_dir

        if not os.path.exists(model_path):
            print(f"❌ 模型目录不存在: {model_path}")
            print(f"   请确认 sarcasm_detection/output_prompt 目录存在")
            return False

        try:
            print(f"📥 正在加载模型...")
            print(f"   路径: {model_path}")

            self.model = AutoModelForMaskedLM.from_pretrained(model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # 获取"是"和"否"的token id
            self.yes_token_id = self.tokenizer.encode("是", add_special_tokens=False)[0]
            self.no_token_id = self.tokenizer.encode("否", add_special_tokens=False)[0]

            self.model.to(self.device)
            self.model.eval()

            print("✅ 模型加载成功!")
            print(f"   是 token id: {self.yes_token_id}")
            print(f"   否 token id: {self.no_token_id}")
            return True

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False

    def is_loaded(self):
        """检查模型是否已加载"""
        return self.model is not None and self.tokenizer is not None

    def detect(self, text, topic="商品"):
        """
        检测单条文本是否为讽刺

        返回:
            dict: 包含检测结果和详细信息
        """
        if not self.is_loaded():
            return {"error": "模型未加载"}

        # 构造提示模板
        prompt = f"{text} 是对 {topic} 的讽刺吗？[MASK]"

        try:
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=128,
                padding=True
            )

            # 移动到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 模型推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

                # 找到 [MASK] 位置
                mask_token_id = self.tokenizer.mask_token_id
                mask_positions = (inputs["input_ids"] == mask_token_id).nonzero(as_tuple=True)

                if len(mask_positions[1]) == 0:
                    return {"error": "未找到 [MASK] 位置"}

                mask_idx = mask_positions[1][0].item()
                mask_logits = logits[0, mask_idx, :]

                # 获取 "是" 和 "否" 的 logits
                yes_logit = mask_logits[self.yes_token_id].item()
                no_logit = mask_logits[self.no_token_id].item()

                # Softmax 计算概率
                exp_yes = np.exp(yes_logit)
                exp_no = np.exp(no_logit)
                total = exp_yes + exp_no
                yes_prob = exp_yes / total
                no_prob = exp_no / total

                # 判断结果
                is_sarcasm = yes_prob > no_prob
                confidence = yes_prob if is_sarcasm else no_prob

                return {
                    "text": text,
                    "topic": topic,
                    "prompt": prompt,
                    "logits": {
                        "是": round(yes_logit, 4),
                        "否": round(no_logit, 4)
                    },
                    "probabilities": {
                        "是": round(yes_prob, 6),
                        "否": round(no_prob, 6)
                    },
                    "is_sarcasm": bool(is_sarcasm),
                    "confidence": round(confidence, 6),
                    "result_text": "✅ 是讽刺" if is_sarcasm else "❌ 不是讽刺"
                }

        except Exception as e:
            return {"error": str(e), "text": text}

    def print_result(self, result):
        """打印检测结果"""
        if "error" in result:
            print(f"\n❌ 错误: {result['error']}")
            return

        print("\n" + "=" * 60)
        print("🎭 TOSPrompt 讽刺检测结果")
        print("=" * 60)
        print(f"\n📄 输入文本: {result['text']}")
        print(f"📌 话题: {result['topic']}")
        print(f"\n📝 构造Prompt:")
        print(f"   {result['prompt']}")
        print(f"\n🔢 模型输出 (Logits):")
        print(f"   '是': {result['logits']['是']:>10.4f}")
        print(f"   '否': {result['logits']['否']:>10.4f}")
        print(f"\n📊 Softmax 概率:")
        print(f"   '是': {result['probabilities']['是']:>10.6f} ({result['probabilities']['是']*100:.4f}%)")
        print(f"   '否': {result['probabilities']['否']:>10.6f} ({result['probabilities']['否']*100:.4f}%)")
        print(f"\n🎯 最终结果: {result['result_text']}")
        print(f"   置信度: {result['confidence']:.6f}")
        print("=" * 60)


def interactive_mode(tester):
    """交互模式"""
    print("\n🎭 TOSPrompt 交互测试模式")
    print("输入文本进行讽刺检测，输入 'quit' 退出\n")

    while True:
        try:
            text = input("📄 输入文本 (或 'quit'): ").strip()

            if text.lower() in ['quit', 'exit', 'q', '退出']:
                print("👋 再见!")
                break

            if not text:
                continue

            topic = input("📌 输入话题 [默认: 商品]: ").strip() or "商品"

            result = tester.detect(text, topic)
            tester.print_result(result)

        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


def test_builtin_dataset(tester):
    """测试内置数据集"""
    test_cases = [
        # (文本, 话题, 期望结果)
        ("这个商品真的很好用", "商品", None),
        ("呵呵，真是太好了呢", "商品", None),
        ("哇，这个包装真是精美，打开全是碎的", "快递", None),
        ("物流真快呢，三天就送到了", "快递", None),
        ("宇宙第一大军火商", "三星", None),
        ("不比了，不比了，你第一，你第一，乖哈", "手机", None),
        ("良心无价，利润算啥", "企业", None),
        ("这个价格真是良心啊，太便宜了", "商品", None),
    ]

    print("\n🧪 批量测试内置数据集")
    print(f"共 {len(test_cases)} 条测试数据\n")

    results = []
    for i, (text, topic, _) in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] ", end="")
        result = tester.detect(text, topic)
        results.append(result)

        if "error" not in result:
            emoji = "🎭" if result["is_sarcasm"] else "✅"
            print(f"{emoji} {text[:30]}... -> {result['result_text']}")
        else:
            print(f"❌ 错误: {result['error']}")

    # 统计
    print("\n" + "=" * 60)
    print("📊 测试统计")
    print("=" * 60)

    total = len([r for r in results if "error" not in r])
    sarcasm_count = len([r for r in results if r.get("is_sarcasm")])
    normal_count = total - sarcasm_count

    print(f"总测试数: {len(test_cases)}")
    print(f"成功检测: {total}")
    print(f"  🎭 讽刺: {sarcasm_count} ({sarcasm_count/total*100:.1f}%)")
    print(f"  ✅ 正常: {normal_count} ({normal_count/total*100:.1f}%)")
    print(f"  ❌ 错误: {len(test_cases) - total}")

    # 显示详细信息
    print("\n📝 详细结果:")
    for i, result in enumerate(results, 1):
        if "error" not in result:
            status = "🎭" if result["is_sarcasm"] else "✅"
            print(f"\n  {i}. {status} {result['text']}")
            print(f"      概率: 是={result['probabilities']['是']:.4f}, 否={result['probabilities']['否']:.4f}")


def test_from_file(tester, filepath):
    """从文件加载测试数据"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        texts = [line.strip() for line in lines if line.strip()]

        print(f"\n📁 从文件加载 {len(texts)} 条测试数据")

        for i, text in enumerate(texts, 1):
            print(f"\n[{i}/{len(texts)}]")
            result = tester.detect(text)
            tester.print_result(result)

    except Exception as e:
        print(f"❌ 读取文件失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='TOSPrompt 讽刺检测模型测试')
    parser.add_argument('--text', '-t', type=str, help='单条测试文本')
    parser.add_argument('--topic', type=str, default='商品', help='话题（默认: 商品）')
    parser.add_argument('--file', '-f', type=str, help='测试数据文件路径')
    parser.add_argument('--batch', '-b', action='store_true', help='使用内置测试集')

    args = parser.parse_args()

    # 初始化测试器
    print("=" * 60)
    print("🎭 TOSPrompt 讽刺检测模型测试")
    print("=" * 60)

    tester = TOSPromptTester()

    if not tester.is_loaded():
        print("\n❌ 模型加载失败，无法继续测试")
        return 1

    # 根据参数选择模式
    if args.text:
        # 单条测试
        result = tester.detect(args.text, args.topic)
        tester.print_result(result)

    elif args.file:
        # 文件批量测试
        test_from_file(tester, args.file)

    elif args.batch:
        # 内置测试集
        test_builtin_dataset(tester)

    else:
        # 交互模式
        interactive_mode(tester)

    return 0


if __name__ == '__main__':
    sys.exit(main())
