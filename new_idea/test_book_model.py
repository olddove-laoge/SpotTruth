"""
测试book品类LoRA模型 - 训练前vs训练后对比
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

MODEL_PATH = "D:/C_data/SpotTruth/new_idea/output/lora/book/checkpoint-579"
CACHE_DIR = r"C:\Users\lyh23\.cache\huggingface\hub\models--hfl--chinese-roberta-wwm-ext\snapshots\5c58d0b8ec1d9014354d691c538661bf00bfdb44"
LABELS = {0: "差评", 1: "好评"}


def load_base_model():
    """加载基座模型（LoRA训练前）"""
    print("=" * 60)
    print("【LoRA训练前】基座模型: hfl/chinese-roberta-wwm-ext")
    print("=" * 60)
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=2)
    model.eval()
    return model, tokenizer


def load_lora_model():
    """加载LoRA模型（训练后）- 合并权重"""
    print("\n" + "=" * 60)
    print("【LoRA训练后】基座模型 + book领域LoRA适配器 (merged)")
    print("=" * 60)
    tokenizer = AutoTokenizer.from_pretrained(CACHE_DIR)
    base_model = AutoModelForSequenceClassification.from_pretrained(CACHE_DIR, num_labels=2)
    model = PeftModel.from_pretrained(base_model, MODEL_PATH)
    model = model.merge_and_unload()
    model.eval()
    return model, tokenizer


def predict(text, model, tokenizer):
    """预测单条文本"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(** inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        pred = torch.argmax(probs, dim=-1).item()
    return LABELS[pred], probs[0][pred].item(), {
        "差评": round(probs[0][0].item(), 4),
        "好评": round(probs[0][1].item(), 4)
    }


def text_ellipsis(text, max_len=30):
    """单条文本截断（仅用于表格展示，不影响预测）"""
    return text[:max_len] + ".." if len(text) > max_len else text


def main():
    test_texts = [
        # 好评5条（原有）
        "这本书真的超出预期，本来只是随便翻翻，结果越看越入迷。作者文笔细腻，故事讲得特别真实，很多情节都能让人产生共鸣。不管是人物塑造还是情感表达都很到位，看完心里暖暖的，很治愈。已经推荐给身边的朋友，绝对值得一读。",
        "买之前看了很多评价，犹豫了很久才下手，读完一点都不后悔。内容很扎实，知识点讲得通俗易懂",
        "孩子今年上小学，一直不太爱看书，没想到这本他居然特别喜欢。里面的故事有趣又有意义，语言简单好懂，插图也很可爱。每天晚上都主动让我给他读，不仅培养了阅读习惯，还学到了很多道理，作为家长真的很满意。",
        "这是我今年读过最棒的一本书，逻辑清晰，观点深刻，看完有种豁然开朗的感觉。作者不只是在讲故事，更是在传递一种生活态度和思考方式。很多段落我都反复读了好几遍，每次都有新体会，强烈推荐。",
        "书的内容很充实，既有理论又有案例，读起来完全不费劲。能看出作者很用心，写得很真诚，没有多余的废话。虽然有点厚，但一点都不拖沓，越往后越精彩。看完还想再看第二遍，是一本可以收藏的好书。",
        "非常满意，下次还会购买",
        # 好评新增5条
        "反复翻阅了好几遍，依旧觉得回味无穷。书中的文字温柔又有力量，没有华丽的辞藻，却字字戳心。无论是对生活的感悟，还是对人性的刻画，都格外细腻真实。读完之后内心特别平静，仿佛被温柔拥抱过，是一本能治愈浮躁、安抚情绪的宝藏书籍，闲暇时读上几页，整个人都能慢下来。",
        "冲着作者口碑入手，读完彻底被圈粉。内容干货满满，逻辑严谨又通俗易懂，没有晦涩难懂的理论，全是贴近生活的实用内容。每一个观点都有详实案例支撑，看完能真正学到东西、用到实处。装帧设计也很精致，拿在手里质感十足，自学或收藏都再合适不过。",
        "原本对这类书不抱期待，没想到读完彻底改观。故事节奏恰到好处，人物形象鲜活立体，每一个角色都有血有肉，情感过渡自然不生硬。情节跌宕起伏却不刻意，代入感极强，跟着书中人物哭哭笑笑，仿佛亲身经历了一段别样人生。合上书依旧意犹未尽，绝对是不容错过的佳作。",
        "送给朋友的礼物，自己先忍不住读完了。内容温暖治愈，传递的价值观特别正向，既能让人感受生活美好，也能教会人坦然面对困境。文笔流畅优美，读起来行云流水，没有丝毫卡顿感。篇幅适中，通勤、睡前阅读都合适，读完心里满是温暖与力量。",
        "实打实的诚意之作，能清晰感受到作者的用心。内容有深度却不晦涩，有温度却不矫情，兼顾思想性和可读性。不仅能开阔眼界、提升认知，还能引发对生活、对自我的深度思考。纸张厚实，排版舒适，阅读体验感拉满，是一本值得细细品读、反复回味的好书。",
        # 好评短评5条（新增）
        "这本书超好看，内容精彩，性价比高！",
        "读起来很舒服，文字易懂，收获满满。",
        "孩子超爱读，插图精美，值得推荐！",
        "内容很实用，看完对工作超有帮助。",
        "印刷质量好，内容不枯燥，值得入手。",
        
        # 中评5条
        "这本书整体比较中规中矩，没有特别大的亮点，但也不算难看。文笔还算流畅，读起来不费劲，故事框架也比较完整。只是情节稍显平淡，没有太多让人印象深刻的地方，人物塑造也比较普通。打发时间随便看看可以，不用抱太高的期待。",
        "只能算勉强及格的一本书。优点是语言通俗易懂，内容贴近生活，部分段落还能让人有点共鸣。但节奏有些拖沓，后半段明显乏力，观点也不够深刻，看完没有太多收获。属于可看可不看的类型，不算浪费时间，但也算不上好书。",
        "有优点也有明显的不足。前半部分写得还不错，逻辑清晰，内容也比较扎实，能看进去。可越往后越敷衍，情节松散，有些地方甚至前后矛盾。纸张和印刷还算正常，整体无功无过，读完没有惊喜，也没有特别想吐槽的地方。",
        "阅读体验很一般，既不惊艳也不算踩雷。作者的文字功底尚可，叙述比较平实，没有太多花哨的技巧。但内容缺乏新意，很多桥段都比较套路，情感表达也不够到位。适合没事的时候翻一翻，看完就忘，不会再读第二遍。",
        "中规中矩的一本读物，优点和缺点都很明显。好的地方是故事完整，三观正向，读起来轻松无压力。缺点是深度不够，人物不够立体，亮点太少。如果没什么书看的时候可以读一读，特意购买阅读就没太大必要了。",

        # 差评5条（原有）
        "看完特别失望，内容空洞，全是流水账，没什么实质性内容。文笔也很一般，情节老套，看了开头就能猜到结尾，完全不值得花时间读。感觉就是为了凑字数写的，浪费钱。",
        "宣传说得天花乱坠，实际一看完全不是那么回事。观点牵强，逻辑混乱，很多地方都讲不通。读起来非常枯燥，翻了几页就看不下去了，还不如网上随便找的文章好看。",
        "书的质量太差了，纸张很薄，印刷模糊，还有好几页错字。内容也很敷衍，感觉就是东拼西凑出来的，毫无诚意。买完就后悔了，放家里积灰都嫌占地方，不推荐购买。",
        "期望值太高，结果落差特别大。故事不吸引人，人物也很单薄，没有记忆点。越看越没劲，勉强看完，完全没留下什么印象。同类型的书比这本好太多了，真心不建议买。",
        "整体很一般，既不精彩也不实用，看完没什么收获。语言平淡，节奏拖沓，很多章节都是多余的。没有传说中那么好，纯属被评价炒起来的，性价比很低，不太推荐。",

        # 差评新增5条
        "读完满是失望，完全名不副实。内容杂乱无章，东一榔头西一棒子，没有清晰主线和逻辑。文笔粗糙生硬，读起来晦涩又别扭，毫无文学性可言。既没有有趣故事，也没有实用价值，浪费时间和精力，真心建议避坑。",
        "质量和内容双拉胯，堪称年度最踩雷书籍。纸张劣质，装订松散，翻几页就脱页，印刷更是模糊不清。内容敷衍了事，全是网上随处可见的陈词滥调，东拼西凑毫无原创性，读起来枯燥乏味、毫无营养，买完就后悔莫及。",
        "抱着极大期待阅读，结果越读越无语。情节拖沓冗长，废话连篇，核心内容少得可怜。人物塑造扁平空洞，没有任何闪光点，完全无法让人产生共鸣。逻辑漏洞百出，情节牵强附会，强行煽情却毫无感染力，勉强读完只觉得浪费时间。",
        "性价比极低，完全不值得入手。内容浅薄无味，既无深度也无内涵，通篇都是空洞口号和无意义抒情。语言表达平淡无奇，节奏混乱，读起来毫无趣味。同价位优质书籍比比皆是，这本毫无竞争力，不推荐购买。",
        "彻底踩雷的一本书，看完只剩吐槽。宣传夸大其词，实际内容与宣传相差甚远。知识点零散不系统，讲解含糊不清，根本起不到学习作用。文笔平庸，故事乏味，整体毫无亮点，放书架都嫌占地方，真心建议大家避开这个坑。",
        # 差评短评5条（新增）
        "内容太差，完全不值这个价！",
        "印刷模糊，错字多，质量拉胯。",
        "故事无聊，看了几页就弃了。",
        "性价比低，不推荐购买。",
        "内容敷衍，纯属浪费钱。"
    ]
    base_model, tokenizer = load_base_model()
    lora_model, _ = load_lora_model()

    print("\n" + "=" * 80)
    # 调整列宽，避免文本截断后显示拥挤
    print(f"{'文本摘要':<30} {'LoRA前':<10} {'LoRA后':<10}")
    print("=" * 80)

    # 关键修复：遍历原文本，仅对展示的文本摘要截断，预测仍用原文本
    for full_text in test_texts:
        # 预测用完整文本，保证结果准确
        base_pred, base_conf, base_probs = predict(full_text, base_model, tokenizer)
        lora_pred, lora_conf, lora_probs = predict(full_text, lora_model, tokenizer)
        
        # 仅展示时截断文本，不影响预测结果
        display_text = text_ellipsis(full_text, max_len=30)
        change = "->" if base_pred == lora_pred else "XX"
        print(f"{display_text:<30} {base_pred}({base_conf:.0%}) {change} {lora_pred}({lora_conf:.0%})")

    print("\n【详细概率对比】")
    print("-" * 80)
    for text in test_texts:
        _, _, base_probs = predict(text, base_model, tokenizer)
        _, _, lora_probs = predict(text, lora_model, tokenizer)
        print(f"文本: {text}")
        print(f"  LoRA前: 差评={base_probs['差评']}, 好评={base_probs['好评']}")
        print(f"  LoRA后: 差评={lora_probs['差评']}, 好评={lora_probs['好评']}")
        print()


if __name__ == "__main__":
    main()