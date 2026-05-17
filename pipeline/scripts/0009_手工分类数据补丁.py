import pandas as pd
import os

import os as _os
# === 路径适配（由管线V2.0网页版注入） ===
_PV2 = _os.environ.get("PV2_WORKSPACE", "")
if _PV2:
    _PV2_IN = _os.path.join(_PV2, "input")
    _PV2_OUT = _os.path.join(_PV2, "output")
    _os.makedirs(_os.path.join(_PV2, "005_data"), exist_ok=True)
    _os.makedirs(_os.path.join(_PV2, "_data"), exist_ok=True)



# ==========================================
# 1. 配置路径
# ==========================================
BASE_PATH = _PV2 + "/" if _PV2 else "/Users/weiyueshao/Desktop/pipeline_v2/"
OUTPUT_CSV = os.path.join(BASE_PATH, "005_data/trademark_judgment_scale_analysis.csv")

# ==========================================
# 2. 填入刚才生成的分类数据（这是我为你整理好的）
# ==========================================
data = [
    {"case_id": "(2024)粤0111民初687号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "原告未能提供充分证据证明其实际利润率，法院最终适用法定赔偿。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判决书中并未提及涉案商标对商品利润的具体贡献比例。"},
    {"case_id": "(2024)浙0109民初2077号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "法院认为原告主张的利润率缺乏充分证据支持，转而进行酌定。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未对涉案商标的贡献率进行任何事实审查与法律论述。"},
    {"case_id": "(2024)浙0603民初611号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "法院未采信具体的利润率数值，直接适用了法定赔偿进行整体考量。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "全文缺乏对商标品牌价值在商品溢价中占比的分析。"},
    {"case_id": "(2023)浙03民终5915-2号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "原告利润率主张未获支持，法院基于综合因素酌定赔偿数额。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "说理部分直接跳过了商标贡献率的独立剥离步骤。"},
    {"case_id": "(2024)辽10民终432号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "缺乏精确的财务审计结论，法院拒绝按照原告主张的比例计算。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "没有对侵权获利中属于商标贡献的部分进行单独界定。"},
    {"case_id": "(2023)浙0304民初6578号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "因证据链条不完整，法院未采纳特定利润率，适用法定赔偿原则。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未就商标侵权对销售利润的实际驱动力进行论证。"},
    {"case_id": "(2023)浙01民终12265号", "margin_category_code": "A2_行业同业参考", "margin_reasoning": "法院在说理中参考了白酒行业上市公司的平均毛利率作为酌定基础。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "虽参考了行业利润，但并未剥离出商标的单独贡献率。"},
    {"case_id": "(2024)浙07民终147号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "提供的利润数据不具有代表性，法院最终行使了自由裁量权。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判决书未讨论品牌效应对酒店服务行业利润的贡献度。"},
    {"case_id": "(2024)浙0603民初660号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "原告关于化妆品利润率的主张因仅为单方陈述而未被法院采信。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "完全省略了商标贡献率这一中间计算变量。"},
    {"case_id": "(2024)浙0302民初1970号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "法官认定现有证据无法精确计算利润率，进而采取法定赔偿。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未论述原告商标的知名度在被告获利中占据的具体比例。"},
    {"case_id": "(2024)粤0111民初4754号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "餐饮服务行业的实际利润率举证困难，法院未采纳原告主张。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未涉及商标在餐饮引流及营收中贡献率的专项分析。"},
    {"case_id": "(2023)浙1023民初5225号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "原告利润计算方式未获认可，法院综合全案事实进行法定赔偿估算。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未明确商标价值与商品其他价值（如外观、实用性）的比例分配。"},
    {"case_id": "(2024)浙07民终130号", "margin_category_code": "A1_完全采信", "margin_reasoning": "法院对原告提交的正规财务账册及审计说明中的利润率予以认可。", "contribution_category_code": "B2_多因素剥离", "contribution_reasoning": "法官指出日化产品的销量亦受到销售渠道和包装影响，故对商标贡献进行了打折处理。"},
    {"case_id": "(2024)皖1623民初1661号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "利润率证据不足以形成完整证据链，法院予以驳回并酌定赔偿。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "说理部分直接跨过了对商标贡献因素的评价。"},
    {"case_id": "(2024)辽10民终433号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "二审法院维持一审认定，认为利润率缺乏具有法律效力的财务凭证支撑。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "两审判决均未涉及贡献率这一精细化计算指标。"},
    {"case_id": "(2023)豫07知民终39号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "对于饲料行业的利润率，法院认为原告举证未能达到高度盖然性标准。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "完全未考虑商标对于此类产品销售的实质贡献比例。"},
    {"case_id": "(2023)浙0105民初8875号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "原告主张的装饰材料利润率不被采信，最终依照法定赔偿规则处理。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "缺失关于品牌溢价率或商标贡献度的事实查明。"},
    {"case_id": "(2024)浙0782民初1117号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "牙膏产品的利润率受到多重因素影响，法院认为原告证据不足以单独采信。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判决书没有探讨云南白药商标在产品整体利润中应占多少权重。"},
    {"case_id": "(2024)浙0302民初1869号之一", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "法院认为无法准确计算原告因侵权受到的实际损失或被告的违法所得。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判赔计算中彻底忽略了商标贡献率的考量。"},
    {"case_id": "(2024)浙0110民初846号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "服装行业的利润波动较大，法院认为原告未能提供涉案同类产品的精准利润率。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未就被告销售服装的利润中有多少源于攀附商标商誉进行论述。"},
    {"case_id": "(2023)浙06民终3823号", "margin_category_code": "A2_行业同业参考", "margin_reasoning": "法院参考了家电制造业相关的行业平均利润数据作为确认侵权获利的基准。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "虽确定了利润基数，但并未进一步按商标贡献率折算。"},
    {"case_id": "(2024)浙0302民初1825号之一", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "对原告提交的利润率未予确认，直接打包适用法定赔偿。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未对涉案商标在卫浴用品销售中发挥的作用大小进行量化评价。"},
    {"case_id": "(2024)浙0302民初1745号之一", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "未采信具体利润率，法官根据案情综合因素酌定判赔额。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未分析商标因素与其他因素在利润构成中的相对比例。"},
    {"case_id": "(2024)辽07民终255号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "因被告未到庭且无财务账册，但原告主张亦证据不足，法院驳回具体利润率计算法。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未提及餐饮服务类商标贡献率。"},
    {"case_id": "(2024)浙0302民初1975号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "法院不支持基于原告主观估算的利润率，转入法定赔偿模式。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未明确商标对于产品最终销售的独立贡献比例。"},
    {"case_id": "(2024)浙0302民初1754号之二", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "因无法查清被告实际利润率，法院拒绝采信原告单方提供的毛利参考值。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判决说理避开了商标贡献率这一裁量环节。"},
    {"case_id": "(2024)沪0104民初372号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "图书出版物的真实利润无法精确查明，法院直接适用法定规则予以判决。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未讨论图书内容与书名/商标分别占利润的比例。"},
    {"case_id": "(2023)浙03民终168号", "margin_category_code": "A2_行业同业参考", "margin_reasoning": "二审法院结合工业自动化设备行业的合理利润范围支持了部分主张。", "contribution_category_code": "B2_多因素剥离", "contribution_reasoning": "法院指出购买者在选择工业设备时更看重技术参数与性能，对商标贡献度进行了大幅限制。"},
    {"case_id": "(2024)沪0104民初2391号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "鉴于原告提供的利润证据不具有唯一指向性，法院未予采纳。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判决未提及照明设备中品牌效应所占的权重。"},
    {"case_id": "(2023)粤73民终1709号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "未能提供证明侵权获利的直接财务证据，最终归入法定赔偿适用范围。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "对于服装商品利润中商标究竟贡献几何，法院未置一词。"},
    {"case_id": "(2024)粤1971民初847号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "侵权造成的实际损失和侵权人获利均难以确定，未采信利润率数据。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "完全省略商标贡献率的相关探讨。"},
    {"case_id": "(2023)沪0104民初31629号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "法院认为难以依据现有证据剥离出侵权商品的具体利润率，故不予支持。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "判决书内容未将商标贡献率纳入裁量标准体系。"},
    {"case_id": "(2024)浙0402民初947号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "美容美发服务的利润率由于个体差异极大，法院未采信原告主张的行业通用标准。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "并未拆分品牌授权与实际服务在获利中的贡献比例。"},
    {"case_id": "(2023)沪0104民初26667号", "margin_category_code": "A4_证据不足驳回", "margin_reasoning": "原告未能完成关于实际利润率的举证责任，法院遂依职权确定赔偿金。", "contribution_category_code": "B3_避而不谈", "contribution_reasoning": "未讨论内衣商品中商标的贡献程度。"}
]

# ==========================================
# 3. 写入 CSV
# ==========================================
df = pd.DataFrame(data)
df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

print(f"🎉 修复完成！文件已生成在：{OUTPUT_CSV}")
print("现在你可以重新运行 step4_integrated_analysis.py 了！")