from typing import Any, Dict

from core.brevio.enums.category import CategoryType
from core.brevio.enums.language import LanguageType
from core.brevio.enums.output_format_type import OutputFormatType
from core.brevio.enums.source_type import SourceType
from core.brevio.enums.style import StyleType


class ChinesePrompts:
    INSTRUCTIONS_TITLE: str = "**说明:**"
    SPECIFIC_LANGUAGE_TITLE: str = "**指定语言:** 中文"
    SPECIFIC_LANGUAGE: str = "从现在开始，所有回答必须仅使用中文。"
    EXAMPLE_TITLE: str = "**示例**:"

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "simple_summary": {
            "structures": {"default": ["无需额外标题的直接摘要"]},
            "styles": {
                "default": {
                    "tone": "中性，适应上下文",
                    "elements": [],
                    "source_types": [
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                }
            },
            "rules": [
                "简明扼要地总结，去除冗余内容",
                "保留原始标题（如有），完全保持其原始措辞和格式（如：# 标题，## 子标题）",
                "完全适应源内容的语气、意图和隐含结构",
                "除非原文明确存在，否则不添加标题、子标题或小标题",
                "保持关键示例或概念的原始格式（如：列表、代码、斜体）",
                "避免主观解读或不必要的修改",
                "生成单个连续文本块（除非原始内容另有规定）",
            ],
            "needs": "简洁性和对原始内容的忠实度",
        },
        "journalism": {
            "structures": {
                "chronicle": [
                    "# [事件] 直播",
                    "- **[MM:SS]** 关键声明或事实",
                    "- **[MM:SS]** 关键时刻或进展描述",
                    "- **[MM:SS]** 事件反应或分析",
                ],
                "news_wire": [
                    "[日期] - [地点] - 简明直接的摘要",
                    "### 关键细节",
                    "- [关键事实1]",
                    "- [关键事实2]",
                    "### 背景",
                    "- [背景信息]",
                    "### 统计数据（如适用）",
                    "- [统计1]",
                    "- [统计2]",
                    "### 影响",
                    "- [短期影响]",
                    "- [长期影响]",
                ],
                "analysis": [
                    "## [主题] 深度分析",
                    "### 概述",
                    "- [主题简要总结]",
                    "### 关键方面",
                    "- [方面1]: [详细分析]",
                    "- [方面2]: [详细分析]",
                    "### 影响",
                    "- [短期影响]",
                    "- [长期影响]",
                    "### 专家观点",
                    "- [专家引述或观点]",
                    "### 结论",
                    "- [关键发现和未来展望总结]",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "叙述性，紧迫感",
                    "elements": ["时间线", "关键时刻", "反应"],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
                "news_wire": {
                    "tone": "直接，信息性强",
                    "elements": ["关键细节", "背景", "统计数据", "影响"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "analysis": {
                    "tone": "反思性，注重背景",
                    "elements": [
                        "概述",
                        "关键方面",
                        "影响",
                        "专家观点",
                        "结论",
                    ],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "纪实报道需包含精确时间戳",
                "如适用需注明来源",
                "简讯中避免主观意见",
                "简讯中使用项目符号列出关键细节",
                "简讯中至少包含一个统计数据或数据点",
                "简讯中需同时强调短期和长期影响",
                "纪实报道应聚焦实时关键瞬间和反应",
                "分析类内容需深入探讨主题，包括成因、影响和专家视角",
            ],
            "needs": ["简讯的速度，纪实的细节，分析的背景"],
        },
        "marketing": {
            "structures": {
                "highlights": ["# ✨ [活动] - 亮点", "🎯 **关键:** 价值"],
                "storytelling": [
                    "## [品牌] - 故事: [标题]",
                    "### 引言",
                    "- [情感切入点或背景设定]",
                    "### 主要叙述",
                    "- [关键事件或转折点]",
                    "- [挑战或冲突]",
                    "- [解决方案或结果]",
                    "### 情感影响",
                    "- [故事如何引发受众共鸣]",
                    "### 行动号召",
                    "- [鼓励与品牌/产品互动的语句]",
                ],
                "report": [
                    "## [活动] - 结果",
                    "### 概述",
                    "- [活动目标及内容简要总结]",
                    "### 关键指标",
                    "| **指标** | **目标** | **实际** | **差异** |",
                    "|------------|----------|------------|--------------|",
                    "| [指标1] | [目标1] | [实际1] | [差异1] |",
                    "| [指标2] | [目标2] | [实际2] | [差异2] |",
                    "### 分析",
                    "- [结果详细分析，包括成功与挑战]",
                    "### 建议",
                    "- [基于数据的可执行建议]",
                    "### 结论",
                    "- [核心发现和后续步骤总结]",
                ],
            },
            "styles": {
                "highlights": {
                    "tone": "吸引眼球，视觉化",
                    "elements": ["表情符号", "项目符号"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "storytelling": {
                    "tone": "情感丰富，沉浸式",
                    "elements": ["叙述", "情感切入点", "行动号召"],
                    "source_types": [SourceType.TEXT],
                },
                "report": {
                    "tone": "分析性，清晰",
                    "elements": ["表格", "分析", "建议"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "亮点和故事叙述使用吸引性语言",
                "报告中需包含KPI指标",
                "避免过度使用专业术语",
                "故事叙述需注重情感连接和叙事流畅性",
            ],
            "needs": "视觉冲击力，情感连接，可执行数据",
        },
        "health": {
            "structures": {
                "report": [
                    "**[研究/治疗] - 临床报告:**",
                    "基于数据的技术性段落，聚焦结果和有效性",
                ],
                "summary": [
                    "# 🩺 [主题] - 摘要",
                    "📈 **指标:** 结果",
                    "| 周数 | 进展 |",
                ],
                "case": ["**[患者] - 临床案例:**", "详细叙述"],
            },
            "styles": {
                "report": {
                    "tone": "正式，精确，循证",
                    "elements": ["量化数据", "临床结果"],
                    "source_types": [SourceType.TEXT],
                },
                "summary": {
                    "tone": "可视化，易理解",
                    "elements": ["项目符号", "表格"],
                    "source_types": [SourceType.TEXT, SourceType.VIDEO],
                },
                "case": {
                    "tone": "叙述性，临床",
                    "elements": ["叙述"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.AUDIO,
                        SourceType.VIDEO,
                    ],
                },
            },
            "rules": [
                "当有量化数据时必须包含",
                "保持科学严谨性，避免主观语言",
                "根据受众调整语言复杂度（医生用专业术语，患者用简单语言）",
                "确保医疗信息的清晰性、准确性和可及性",
            ],
            "needs": {
                "doctors": "清晰精确的临床数据以支持决策",
                "patients": "易于理解的病情和治疗说明",
                "researchers": "基于数据的可靠研究信息",
            },
        },
        "technology": {
            "structures": {
                "changelog": [
                    "# [版本] - 更新",
                    "✨ **新功能:**",
                    "- 功能",
                    "🐛 **修复:**",
                    "- 修复项",
                ],
                "proposal": [
                    "# [项目] - 技术提案",
                    "## 简介",
                    "简要描述项目目标及拟解决问题",
                    "## 目标",
                    "- 目标1: 描述首要目标",
                    "- 目标2: 描述次要目标",
                    "## 技术方案",
                    "说明技术解决方案，包括工具、框架和方法论",
                    "### 核心功能",
                    "- 功能1: 描述核心功能",
                    "- 功能2: 描述核心功能",
                    "## 优势",
                    "强调方案优势如效率、可扩展性或成本节约",
                    "## 实施计划",
                    "提供高层次时间表或实施步骤",
                    "## 风险与应对",
                    "识别潜在风险并提出缓解策略",
                    "## 结论",
                    "总结提案价值主张",
                ],
                "diagram": [
                    "# [流程] - 流程图",
                    "```mermaid",
                    "graph TD",
                    "  A[开始] --> B{决策点?}",
                    "  B -->|是| C[流程1]",
                    "  B -->|否| D[流程2]",
                    "  C --> E[结束]",
                    "  D --> E",
                    "```",
                    "**注释:**",
                    "- **A**: 流程起点",
                    "- **B**: 决策节点",
                    "- **C/D**: 替代路径",
                    "- **E**: 流程终点",
                    "**颜色标识:**",
                    "- **绿色**: 成功路径（如用户已登录）",
                    "- **红色**: 替代路径（如用户未登录）",
                    "**图例说明:**",
                    "- **矩形**: 流程步骤",
                    "- **菱形**: 决策点",
                    "- **圆形**: 开始/结束点",
                ],
            },
            "styles": {
                "changelog": {
                    "tone": "技术性，简洁",
                    "elements": ["项目符号"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "proposal": {
                    "tone": "说服力强，结构清晰",
                    "elements": ["标题", "项目符号", "表格"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "diagram": {
                    "tone": "可视化，描述性，模块化",
                    "elements": ["mermaid图", "颜色编码", "注释", "图例"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
            },
            "rules": [
                "使用与项目相关的特定技术术语",
                "突出解决方案优势以说服利益相关者",
                "包含清晰的结构化实施计划",
                "识别潜在风险并提出缓解策略",
                "使用项目符号和标题提高可读性",
                "提供具体案例或研究支持提案",
                "确保提案模块化便于更新",
                "结论部分需总结提案核心价值",
            ],
            "needs": "说服利益相关者，技术方案清晰度，结构化文档，可执行洞察",
        },
        "education": {
            "structures": {
                "guide": [
                    "# 📚 [主题] - 指南",
                    "## [章节]",
                    "- **概念:** 结合实例和应用场景的说明",
                ],
                "quick_ref": [
                    "**[主题] - 速查表:**",
                    "- [要点]: 简明可操作的总结，附带实用场景说明",
                ],
                "timeline": [
                    "# 🎥 [课程] - 时间轴",
                    "- **[MM:SS]** [关键概念或操作]: [简明解释及实际应用价值]",
                ],
            },
            "styles": {
                "guide": {
                    "tone": "教育性，结构化，包含实例辅助理解",
                    "elements": [
                        "子章节",
                        "项目符号",
                        "实例",
                        "实际应用",
                    ],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "quick_ref": {
                    "tone": "简明，实用，便于快速学习",
                    "elements": ["项目符号", "清晰摘要"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "timeline": {
                    "tone": "时间顺序，操作导向，突出实际应用",
                    "elements": [
                        "时间标记",
                        "分步操作",
                        "视觉提示",
                        "真实场景",
                    ],
                    "source_types": [SourceType.VIDEO, SourceType.AUDIO],
                },
            },
            "rules": [
                "提供结合实例的清晰操作说明",
                "保持信息简明全面，聚焦实用场景",
                "确保与学习目标和场景匹配",
                "强调易用性和真实场景适用性",
            ],
            "needs": "便于学习，快速参考，视频追踪与实用洞察",
        },
        "architecture": {
            "structures": {
                "chronicle": [
                    "# 🏛️ [项目] - 纪实",
                    "- **[MM:SS]** 突出元素",
                ],
                "report": [
                    "**[项目] - 技术报告:**",
                    "包含关键细节的段落",
                ],
                "list": ["# [项目] - 详情", "- **方面:** 描述"],
            },
            "styles": {
                "chronicle": {
                    "tone": "叙述性，视觉化",
                    "elements": ["时间线"],
                    "source_types": [SourceType.VIDEO],
                },
                "report": {
                    "tone": "技术性，详细",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "描述性，组织有序",
                    "elements": ["项目符号"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "突出创新或可持续性特点",
                "如适用应包含技术数据",
                "保持视觉吸引力",
            ],
            "needs": "技术文档，吸引人的呈现方式，视频追踪",
        },
        "finance": {
            "structures": {
                "report": [
                    "# 💰 [期间] - 财务报告",
                    "- **指标:** [数值]",
                ],
                "table": [
                    "## [期间] - 财务摘要",
                    "| **指标** | **数值** |",
                ],
                "executive": [
                    "**[期间] - 执行摘要:**",
                    "突出重点见解的简明段落",
                ],
            },
            "styles": {
                "report": {
                    "tone": "分析性，正式",
                    "elements": ["项目符号"],
                    "source_types": [
                        SourceType.TEXT,
                        SourceType.PDF,
                        SourceType.DOCX,
                        SourceType.VIDEO,
                        SourceType.AUDIO,
                    ],
                },
                "table": {
                    "tone": "可视化，简洁",
                    "elements": ["表格"],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
                "executive": {
                    "tone": "直接，决策层视角",
                    "elements": [],
                    "source_types": [SourceType.TEXT, SourceType.PDF, SourceType.DOCX],
                },
            },
            "rules": [
                "关键数据呈现需清晰简明",
                "避免数据呈现的模糊性",
                "提供支持决策的可执行见解",
                "表格标题格式需规范（双星号前后无多余空格）",
            ],
            "needs": "可执行数据，清晰的视觉化呈现，聚焦影响的执行摘要",
        },
        "tourism": {
            "structures": {
                "chronicle": [
                    "# 🌍 [目的地] - 纪实",
                    "- **[MM:SS]** 倡议",
                    "- **[MM:SS]** 重要里程碑",
                ],
                "report": [
                    "**[目的地] - 政策:**",
                    "强调目的地目标和旅游影响的正式段落",
                ],
                "list": [
                    "# [目的地] - 倡议",
                    "- **领域:** 详情（可加入当地文化或景点）",
                ],
            },
            "styles": {
                "chronicle": {
                    "tone": "叙述性，引人入胜",
                    "elements": ["时间线", "故事叙述"],
                    "source_types": [SourceType.AUDIO, SourceType.VIDEO],
                },
                "report": {
                    "tone": "正式，信息性，客观",
                    "elements": [],
                    "source_types": [SourceType.TEXT],
                },
                "list": {
                    "tone": "描述性，清晰，信息丰富",
                    "elements": ["项目符号", "简明事实"],
                    "source_types": [SourceType.TEXT],
                },
            },
            "rules": [
                "突出可持续性、文化意义和旅游吸引力",
                "包含实用旅行信息（如最佳游览时间、当地景点、紧急联系）",
                "政策描述需清晰准确",
                "避免夸张，保持真实性和信息性",
            ],
            "needs": "吸引人的推广内容，清晰的政策呈现，游客导向的实用细节",
        },
    }

    EXAMPLES = {
        "simple_summary": {"default": "内容描述了2025年3月8日宣布的经济措施，包括减税和信贷额度"},
        "journalism": {
            "chronicle": (
                "# 苹果发布会直播\n"
                "- **[00:03:00]** 蒂姆·库克登台介绍Apple Intelligence，集成在苹果设备中的新AI系统\n"
                "- **[00:05:11]** 展示Apple Watch Series 10，强调其更大显示屏和更薄设计\n"
                "- **[00:07:03]** 演示新款OLED显示屏，斜视角亮度提升40%\n"
                "- **[00:09:06]** 宣布Series 10比Series 9薄10%，厚度仅9.7毫米\n"
                "- **[00:10:19]** 快速充电功能：30分钟充电80%\n"
                "- **[00:11:03]** 抛光钛金属外观，比不锈钢轻20%\n"
                "- **[00:12:00]** 强调可持续性：95%再生钛和100%可再生能源制造\n"
                "- **[00:13:50]** 新健康功能：睡眠呼吸暂停检测和排卵期体温追踪\n"
                "- **[00:15:19]** 讨论睡眠呼吸暂停检测重要性，全球80%病例未确诊"
            ),
            "news_wire": (
                "[2025年3月8日] - 首都 - 总统宣布经济措施\n"
                "### 关键细节\n"
                "- 中产阶级家庭减税\n"
                "- 基础设施项目支出增加\n"
                "### 背景\n"
                "- 措施旨在通胀上升背景下刺激经济增长\n"
                "### 统计数据\n"
                "- 2025年GDP增长预测：2.5%\n"
                "- 失业率：5.8%（去年为6.3%）\n"
                "### 影响\n"
                "- 短期：中产阶级家庭立即受益\n"
                "- 长期：预计刺激经济增长并创造就业"
            ),
            "analysis": (
                "## 税改深度分析\n"
                "### 概述\n"
                "- 近期税改旨在减轻中产阶级家庭税负并通过基建支出刺激经济\n"
                "### 关键方面\n"
                "- **减税**：中产阶级家庭税负减少10%，可支配收入增加\n"
                "- **基建投资**：创造就业并改善公共服务\n"
                "### 影响\n"
                "- **短期**：提升消费能力和经济活动\n"
                "- **长期**：强化经济基础和公共设施\n"
                "### 专家观点\n"
                "- 哈佛经济学家简·多伊博士认为：'这是减少不平等的重要一步'\n"
                "### 结论\n"
                "- 税改平衡了各方需求，但长期成效取决于实施效果"
            ),
        },
        "marketing": {
            "highlights": "# ✨ EcoLife上市 - 亮点\n🎯 **目标:** 年轻群体\n📈 **销售:** +15%",
            "storytelling": (
                "## EcoLife - 故事: 可持续发展之旅\n"
                "### 引言\n"
                "- 繁忙都市中，年轻女性玛丽亚对环境问题感到焦虑\n"
                "### 主要叙述\n"
                "- 她发现专注可持续发展的品牌EcoLife并改变生活方式\n"
                "- 尽管朋友最初质疑，她的坚持最终感染他人\n"
                "### 情感影响\n"
                "- 展现小改变如何产生个人和环境的重大影响\n"
                "### 行动号召\n"
                "- 加入玛丽亚的可持续发展之旅，立即体验EcoLife产品!"
            ),
            "report": (
                "## EcoLife - 结果\n"
                "### 概述\n"
                "- 活动旨在通过推广可持续生活提升年轻群体品牌认知和销售\n"
                "### 关键指标\n"
                "| **指标**       | **目标** | **实际** | **差异** |\n"
                "|------------------|----------|------------|--------------|\n"
                "| 销售增长   | +15%     | +18%       | +3%          |\n"
                "| 社交媒体覆盖 | 1M      | 1.2M       | +200K        |\n"
                "### 分析\n"
                "- 社交媒体互动和KOL合作推动目标超额完成\n"
                "### 建议\n"
                "- 延续KOL合作策略\n"
                "- 增加可持续发展教育内容\n"
                "### 结论\n"
                "- 活动为未来计划奠定了坚实基础"
            ),
        },
        "health": {
            "report": "**治疗X - 临床报告:** 临床试验显示持续治疗8周后症状减少70%",
            "summary": "# 🩺 治疗X - 摘要\n📈 **有效性:** 70%\n| 周数 | 进展 |\n| 8    | 70%  |",
            "case": "**患者A - 临床案例:** 62岁男性治疗两周后改善明显",
        },
        "technology": {
            "changelog": "# v3.0 - 更新\n✨ **新功能:**\n- 文字识别\n🐛 **修复:**\n- 导出功能",
            "proposal": """
                    # 项目X - 技术提案

                    ## 简介
                    自动化API集成系统以提高数据处理效率

                    ## 目标
                    - 目标1：减少50%人工数据录入
                    - 目标2：提升30%处理速度

                    ## 技术方案
                    使用Python Flask开发API，Docker容器化，Kubernetes编排

                    ### 核心功能
                    - 功能1：多源数据自动采集
                    - 功能2：实时数据验证

                    ## 优势
                    - **效率**：降低人工处理时间
                    - **扩展性**：适应数据量增长
                    - **成本**：减少重复任务支出

                    ## 实施计划
                    1. **阶段1**：API开发测试（2周）
                    2. **阶段2**：部署集成（3周）
                    3. **阶段3**：监控优化（1周）

                    ## 风险应对
                    - **风险1**：部署期间API停机
                    - **对策**：滚动更新策略
                    - **风险2**：数据验证错误
                    - **对策**：自动化测试机制

                    ## 结论
                    本方案可显著提升效率并降低成本
            """,
            "diagram": "# 用户认证流程\n```mermaid\ngraph TD\n  A[开始] --> B{已登录?}\n  B -->|是| C[显示面板]\n  B -->|否| D[跳转登录]\n  C --> E[结束]\n  D --> E\n```\n**注释:**\n- **A**: 流程起点\n- **B**: 判断节点\n- **C/D**: 分支路径\n- **E**: 流程终点\n**颜色标识:**\n- **绿**: 成功路径\n- **红**: 备选路径\n**图例:**\n- **矩形**: 处理步骤\n- **菱形**: 判断点\n- **圆形**: 起止点",
        },
        "education": {
            "guide": "# 📚 [主题] - 指南\n## [章节]\n- **概念:** 含实用案例的说明",
            "quick_ref": "**[主题] - 速查:**\n- [要点]: 简明操作指南",
            "timeline": "# 🎥 [课程] - 时间轴\n- **[MM:SS]** [操作]: [简明说明]",
        },
        "architecture": {
            "chronicle": "# 🏛️ 绿色大厦 - 纪实\n- **[01:15]** 可持续材料应用",
            "report": "**绿色大厦 - 技术报告:** 设计采用可再生能源",
            "list": "# 绿色大厦 - 详情\n- **材料:** 可再生\n- **能源:** 太阳能",
        },
        "finance": {
            "report": "# 💰 2025一季度 - 财务报告\n- **收入:** 技术升级推动5%增长",
            "table": "## 2025一季度 - 摘要\n| **指标** | **数值** |\n|---------------|-----------|\n| 收入       | +5%       |",
            "executive": "**2025一季度 - 执行摘要:** 技术升级和战略扩张推动5%增长，财务前景增强",
        },
        "tourism": {
            "chronicle": "# 🌍 蓝湾 - 纪实\n- **[01:00]** 生态旅游减少废弃物\n- **[05:00]** 环保酒店开发",
            "report": "**蓝湾 - 政策:** 通过废弃物管理和生态旅游促进可持续发展，目标2030年碳中和",
            "list": "# 蓝湾 - 倡议\n- **生态:** 减少塑料使用\n- **景点:** 全年开放，旺季5-9月",
        },
    }

    def get_prompt_base(
        self,
        category: CategoryType,
        style: StyleType,
        output_format: OutputFormatType,
        spec: Any,
        style_info: Any,
    ) -> list[str]:
        return [
            f"# 提示用于 {category.value.title()} - {style.value.title()}",
            f"**目标:** 创建以 {output_format.value.upper()} 格式的内容，优化用于 {category.value.title()}",
            f"**风格:** {style.value.title()} ({style_info['tone']})",
            f"**基本需求:** {spec.get('needs', '适应上下文')}",
            "",
        ]

    def get_mandatory_rules_prompt(self, generator: Any) -> list[str]:
        return [
            "避免使用诸如“文本现在已无重复并保持清晰和连贯”这样的通用短语。专注于提供具体且明确的反馈。",
            "不要包含诸如“这是修改后的文本，删除了冗余和重复，但保留了所有细节和原始结构”这样的短语。",
            "在任何情况下都不要包含 ```markdown 标签。如果使用代码块，必须未指定语言或使用非 Markdown 语言。",
            f"从现在开始，请仅用中文回答，无论原始问题使用何种语言。",
        ]

    def get_summary_level_prompt(self, generator: Any, word_limit: str) -> str:
        return f"- 对文档进行全面总结，突出主要主题、关键点和整体目的，控制在大约 {word_limit} 个字。"

    async def get_summary_chunk_prompt(
        self, generator: Any, previous_context: str
    ) -> str:
        prompt = f"""
            上一段文本的上下文: {previous_context}\n
            说明: 请对以下文本提供详细摘要，并将新信息与先前的上下文连贯地整合。
            包括示例、解释以及任何有助于学习该主题的细节。
            将摘要组织成部分或关键点，以便于理解。"""
        return prompt

    async def get_postprocess_prompt(self, generator: Any) -> str:
        prompt = f"""你是一位擅长通过删除冗余来改进文本的编辑专家。
            请检查以下摘要，仅删除重复或冗余的信息，
            例如重复的文本、短语或思想。
            不要简化、缩减或以任何方式概括内容；保留所有细节、数据和重要元素。
            确保最终文本清晰、连贯且结构合理，而不改变其结构或原始含义。"""
        return prompt
