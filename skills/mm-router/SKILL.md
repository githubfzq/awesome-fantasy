---
name: mm-router
description: |
  思维模型路由器。当用户描述一个具体困境却说不清该用哪个模型时调用;或用户直接问"这种情况该用什么模型 / 有什么思维模型能解释这件事 / 帮我找个分析框架"时调用。触发词: 该用什么模型 / 有什么框架 / 怎么分析这件事 / which mental model / mental model for / 思维模型推荐 / 分析框架 / 这属于什么效应 / 有什么定律能解释 / 帮我找个模型。不适用于: 用户已点名某个具体模型(直接调用那个 skill)、纯信息查询、闲聊。
source_book: 《思维模型》加布里·温伯格 & 劳伦·麦肯 (蒸馏导航层)
tags: [meta, router, mental-models]
related_skills: []
---

# 思维模型路由器 (Mental Model Router)

> 《思维模型》全书 377 个已蒸馏模型的**导航层**。唯一职责: 从用户的具体困境,定位到应调用的那个(或那几个)`mm-*` skill。

## 使用场景

1. 用户描述了困境但没说是哪个模型 —— "我团队两个人一直在互相甩锅"
2. 用户直接要框架 —— "分析这件事有没有什么思维模型"
3. 用户已能识别现象、想交叉验证 —— "这算不算幸存者偏差"

## 路由步骤

1. **判断场景域** — 用户的问题落在九个域中的哪一个?

| 场景域 | 典型信号 | 首选模型 |
|---|---|---|
| 认知与推理 | 判断出错、被误导、归因争执、直觉不靠谱 | 逆向思维 / 第一性原理 / 奥卡姆的剃刀 / 汉隆的剃刀 / 证实偏差 |
| 风险与意外后果 | 政策出了反效果、好心办坏事、欠下长期债、过载 | 古德哈特定律 / 眼镜蛇效应 / 公地悲剧 / 技术负债 / 道德风险 |
| 时间与优先级 | 忙不过来、拖延、该做什么不该做什么 | 机会成本 / 帕累托法则 / 艾森豪威尔矩阵 / 深度工作 / 沉没成本谬误 |
| 增长与系统 | 扩散不起来、临界点、滚雪球、失控、熵增 | 临界量 / 网络效应 / 复利 / 飞轮 / 连锁故障 / 蝴蝶效应 |
| 数据与证据 | 数据可信吗、样本够吗、因果还是相关、p 值 | 大数定律 / 幸存者偏差 / 基础比率 / 贝叶斯定理 / 均值回归 |
| 决策 | 选哪个、值不值、不确定性、未知风险 | 期望值 / 决策树 / 成本收益分析 / 可逆与不可逆决策 / 未知的未知 |
| 冲突与博弈 | 谈判、对抗、合作破裂、威慑、被操纵 | 囚徒困境 / 纳什均衡 / BATNA / 互惠 / 承诺 / 威慑 |
| 团队与成长 | 招人、分工、带人、练技能、心理障碍、文化 | 比较优势 / 刻意练习 / 彼得原理 / 成长型思维 / 邓宁-克鲁格效应 |
| 竞争与战略 | 护城河、定位、被颠覆、增长停滞 | 护城河 / 颠覆性创新 / 产品市场匹配 / 转换成本 / 赢家通吃市场 |

2. **在该域清单里精确匹配** — 见下方按域分组的完整清单 (共 377 个)

3. **调用而非复述** — 定位到具体 `mm-*` skill 后,**加载该 skill 并按它的 E 段步骤执行**。不要在本 skill 里代替它们作答。

4. **多模型命中时** — 给 2–3 个候选并说明各自适用条件让用户选。书中本身存在模型冲突(如"保留可能性" vs "聚焦"),遇到时如实指出,不强行统一。

---

## 完整清单 (377 个,按场景域分组)

> 格式: `skill-id` — 中文名 (English) — 一句话定义


### 认知与推理 (41 个)

- `mm-5-whys` — 五问法 (5 Whys) — 反复追问"为什么会发生这种事"，直到挖出根本原因。
- `mm-anchoring` — 锚定 (anchoring) — 做决策时不自觉地过度依赖最先出现的信息（第一印象），后续判断围绕它展开。
- `mm-antifragile` — 反脆弱 (antifragile) — 暴露在波动、随机、混乱与压力下不仅不受损，反而能成长壮大的属性。
- `mm-arguing-from-first-principles` — 从第一性原理出发 (arguing from first principles) — 自下而上思考，从不言自明的基本事实出发重新推导结论，而非沿用类比或传统智慧。
- `mm-availability-bias` — 可得性偏差 (availability bias) — 依据最容易想起、最近可获得的信息判断现实，导致对客观认知的无意失真。
- `mm-backfire-effect` — 逆火效应 (backfire effect) — 面对驳斥自己观点的明确证据时，反而更加坚持原有观点。
- `mm-birth-lottery` — 出生彩票 (birth lottery) — 一个人出生在何种家庭、国家、身体条件，完全是随机的运气，而非应得。
- `mm-cognitive-dissonance` — 认知失调 (cognitive dissonance) — 同时持有两个相互矛盾的观念时产生心理压力，并本能地加以消解。
- `mm-confirmation-bias` — 证实偏差 (confirmation bias) — 收集与解释新信息时带有偏见，只用来佐证自己已有的观念。
- `mm-conjunction-fallacy` — 合取谬误 (conjunction fallacy) — 认为两个条件同时成立（合取）的概率大于其中单一条件成立的概率。
- `mm-de-risking` — 去风险化 (de-risking) — 在现实世界中用最低成本检验关键假设，以消除或降低假设不成立的风险。
- `mm-devil-s-advocate-position` — 魔鬼辩护人 (Devil's advocate position) — 刻意站在辩论反方，为既定决策寻找反对理由，即使你并不认同那个立场。
- `mm-disconfirmation-bias` — 不证实偏差 (disconfirmation bias) — 对自己不想相信的观点，要求比想相信的观点多得多的证据。
- `mm-filter-bubble` — 过滤气泡 (filter bubble) — 算法按你的点击偏好过滤掉相反观点，把你包裹在只显示既有喜好内容的"气泡"中。
- `mm-frame-of-reference` — 参照系 (frame of reference) — 观察与判断所依托的视角坐标；同一事物在不同参照系下呈现不同状态。
- `mm-framing` — 框架效应 (framing) — 同一事实的不同呈现或描述方式，会显著改变他人的理解、记忆与选择。
- `mm-fundamental-attribution-error` — 基本归因错误 (fundamental attribution error) — 把他人的行为归因于其内在品性或根本动机，而低估外部情境因素。
- `mm-hanlon-s-razor` — 汉隆的剃刀 (Hanlon's razor) — 永远不要把可以合理解释为粗心的行为，归咎为恶意。
- `mm-inversion` — 逆向思维 (inversion / inverse thinking) — 反过来思考问题，把"如何成功"换成"如何避免失败"，从而解锁新策略。
- `mm-just-world-hypothesis` — 公正世界假说 (just world hypothesis) — 相信世界公平有序、善有善报恶有恶报，不存在运气与随机性的倾向。
- `mm-keep-it-simple` — KISS原则 (Keep It Simple, Stupid!) — 解决问题时从能想到的最简单假设出发，用尽可能简单的方式检验。
- `mm-learned-helplessness` — 习得性无助 (learned helplessness) — 反复受挫后相信自己无力改变处境，于是放弃尝试，即使机会已经出现。
- `mm-minimum-viable-product` — 最简可行产品 (minimum viable product (MVP)) — 只保留够用功能、体量最小、可供真实用户测试的产品版本。
- `mm-most-respectful-interpretation` — 最善意的解释 (most respectful interpretation (MRI)) — 在多种可能的解释中，刻意选择对对方最善意的那一种，先做无罪推定。
- `mm-nudging` — 助推 (nudging) — 通过精心选择的措辞或环境提示，在不强制的前提下影响他人的判断与选择。
- `mm-ockham-s-razor` — 奥卡姆的剃刀 (Ockham's razor) — 面对多个都能解释同一组数据的假设时，最简单的解释最有可能是正确的。
- `mm-optimistic-probability-bias` — 乐观偏差概率 (optimistic probability bias) — 因为极度希望某事成真，而系统性地高估其成功概率、低估失败概率。
- `mm-overfitting` — 过拟合 (overfitting) — 用过分复杂、包含不必要假设的模型去解释数据，把噪声也当成了规律。
- `mm-paradigm-shift` — 范式转换 (paradigm shift) — 学科在旧理论的问题堆积到爆发危机后，整体转向新解释框架的过程。
- `mm-postmortem` — 事后分析 (postmortem) — 项目或事件结束后系统复盘：到底发生了什么，下次如何做得更好。
- `mm-premature-optimization` — 过早优化 (premature optimization) — 在假设尚未验证之前就提前调整、完善方案，导致假设被推翻时全部工作作废。
- `mm-proximate-cause` — 直接原因 (proximate cause) — 最直接、离结果最近的那层原因，即"是什么直接导致了这件事发生"。
- `mm-root-cause` — 根本原因 (root cause) — 事件发生的真正、深层原因；消除它才能防止同类问题复发。
- `mm-self-serving-bias` — 自利性偏差（行为者—观察者偏差） (self-serving bias / actor-observer bias) — 解释自己的行为时归功于情境、解释他人的行为时归咎于品性，两种标准随角色切换。
- `mm-semmelweis-reflex` — 塞麦尔维斯反射 (Semmelweis reflex) — 对不符合既有范式的新发现，不经检验就条件反射式地排斥与嘲笑。
- `mm-system-1` — 快思考与慢思考 (System 1 / System 2 (fast and slow thinking)) — 直觉式、自动化的快速思考，与放慢节奏、质疑直觉假设的审慎逻辑思考。
- `mm-thinking-gray` — 灰度思考（中性思考） (thinking gray / neutral thinking) — 在听完所有相关事实与论据前，不把事物简单二分为黑白对错，而是看清中间的灰色地带。
- `mm-third-story` — 第三方故事 (third story) — 冲突双方各自叙事之外，一个不偏不倚的旁观者会讲出的那个版本。
- `mm-unforced-error` — 主动失误 (unforced error) — 本可以避免却因自身判断失误或执行力差而犯的错，而非对手造成的失败。
- `mm-veil-of-ignorance` — 无知之幕 (veil of ignorance) — 思考社会与制度安排时，想象自己不知道将在其中处于何种位置。
- `mm-victim-blaming` — 指责受害者 (victim-blaming) — 把不幸的结果归咎于受害者自身的选择或品性，而非环境与随机因素。

### 风险与意外后果 (42 个)

- `mm-adverse-selection` — 逆向选择 (adverse selection) — 各方依据自己掌握的私有信息选择对自己有利的交易，导致市场里剩下的都是高风险者。
- `mm-aligning-incentives` — 激励一致（让自利支持目标） (aligning incentives) — 让想要的结果与提供的激励保持一致，使人们的自利行为恰好支持你的目标。
- `mm-analysis-paralysis` — 分析瘫痪 (analysis paralysis) — 因过度分析大量信息，决策工作陷入瘫痪、迟迟无法拍板。
- `mm-asymmetric-information` — 信息不对称 (asymmetric information) — 交易双方掌握的信息不同，可得信息分配不对等。
- `mm-boiling-frog` — 温水煮青蛙 (boiling frog) — 渐进式的变化难以感知、难以应对，等你察觉时已无法脱身。
- `mm-campbell-s-law` — 坎贝尔定律 (Campbell's law) — 越把量化社会指标当作决策目标，它越容易受腐化压力扭曲并破坏本该监控的进程。
- `mm-cap-and-trade` — 总量控制与交易 (cap-and-trade) — 政府设定排放许可总量并允许企业自由交易许可，用市场把污染负外部性内部化。
- `mm-chilling-effect` — 寒蝉效应 (chilling effect) — 因惧怕报复或惩罚，人们不敢自由行使自己的权利、不敢自由表达与搜索。
- `mm-coase-theorem` — 科斯定理 (Coase theorem) — 只要产权明确、行为者理性、交易成本低，外部性可通过当事方自行交易有效内部化，无须政府管制。
- `mm-cobra-effect` — 眼镜蛇效应 (cobra effect) — 尝试解决某个问题，反而让问题变得更糟。
- `mm-collateral-damage` — 附带损害 (collateral damage) — 并非故意地对附带目标造成的伤害、损害或打击。
- `mm-decision-fatigue` — 决策疲劳 (decision fatigue) — 随着做出的决定越来越多，人会疲惫，决策质量随之下降；短暂精神休憩后可恢复。
- `mm-externalities` — 外部性 (externalities) — 未经某实体同意、由外部事物强加给它的好或坏后果。
- `mm-free-rider-problem` — 搭便车现象 (free rider problem) — 某些人免费使用资源而不付成本，靠别人的付出来获益。
- `mm-goodhart-s-law` — 古德哈特定律 (Goodhart's law) — 当一项措施本身成为目标时，它就不再是一项好措施。
- `mm-government-failure` — 政府失灵 / 政治失灵 (government failure / political failure) — 为纠正市场失灵而采取的干预措施本身也失灵。
- `mm-herd-immunity` — 群体免疫效应 (herd immunity) — 当足够高比例的人获得免疫，病原体找不到合格宿主，整个人群（含未免疫者）都受到保护。
- `mm-hick-s-law` — 席克定律 (Hick's law) — 选项数量增加时，做出决定所需时间呈对数增加。
- `mm-hydra-effect` — 九头蛇效应 (hydra effect) — 每移除一个问题源头，就会冒出更多替代者，问题反而扩散。
- `mm-information-overload` — 信息超载 (information overload) — 信息过多超出系统处理能力，使决策过程复杂化、决策时间大幅拉长。
- `mm-internalizing` — 内部化 (internalizing (the externality)) — 要求制造负外部性的实体为其后果付代价，使外部成本回到决策者账上。
- `mm-management-debt` — 管理债务 / 设计债务 / 多样化债务 (management debt / design debt / diversity debt) — 把技术负债模型外推：长期管理团队与流程、统一设计语言、团队多样化上的欠账。
- `mm-market-failure` — 市场失灵 (market failure) — 没有外部干预时，开放市场自行产生次优结果。
- `mm-market-for-lemons` — 柠檬市场（柠檬与蜜桃） (market for lemons) — 质量信息不对称的二手市场中，优质品被劣质品逐出，最终市场只剩劣质品。
- `mm-moral-hazard` — 道德风险 (moral hazard) — 一旦相信自己受到保护，人就愿意承担更大的风险。
- `mm-murphy-s-law` — 墨菲定律 (Murphy's law) — 凡可能出错之事必出错，因此要提前为出错的情况准备预案。
- `mm-nothing-in-excess` — 过犹不及 / 好事过头成坏事 (Nothing in excess / too much of a good thing) — 好东西超过某个量之后反而变成坏事，最优点在中间而非极端。
- `mm-observer-effect` — 观察者效应 (observer effect) — 某物呈现出的结果取决于你的观察方式，甚至取决于观察者是谁。
- `mm-paradox-of-choice` — 选择的悖论 (paradox of choice) — 选项过多、害怕做出次优决策和错过机会的懊悔，会让人更不开心。
- `mm-path-dependence` — 路径依赖 (path dependence) — 你现在可用的决策或路径，取决于你过去的决策。
- `mm-perfect-is-the-enemy-of-good` — 完美乃优秀之敌 (perfect is the enemy of good) — 等待完美的决定或事物可能要等很久，反而不如先接受足够好的方案。
- `mm-perverse-incentives` — 不当诱因 (perverse incentives) — 激励制度诱导出的、与设计意图相反的有害行为。
- `mm-precautionary-principle` — 风险预防原则 (precautionary principle) — 当一项行动可能造成未知程度的危害时，执行前应格外谨慎。
- `mm-preserving-optionality` — 保留可能性 (preserving optionality) — 做出能保留未来选择权的决定，以对冲路径依赖带来的锁定。
- `mm-principal-agent-problem` — 委托代理问题 (principal-agent problem) — 代理人优先追求自身利益，导致委托人得不到最佳结果。
- `mm-public-goods` — 公共物品 (public goods) — 难以排除任何人使用、且一人使用不显著减少他人使用的物品，如国防、广播、空气。
- `mm-reversible-vs-irreversible-decisions` — 可逆决策与不可逆决策 (reversible vs. irreversible decisions) — 不可逆决策（单向门）须审慎缓慢，可逆决策（双向门）应快速试错，两者需要不同的决策流程。
- `mm-short-termism` — 短视主义 (short-termism) — 只关注短期业绩而牺牲长期业绩，最终被做长期投资的对手甩开。
- `mm-streisand-effect` — 史翠珊效应 (Streisand effect) — 试图隐藏某样东西，反而把注意力吸引到它上面。
- `mm-technical-debt` — 技术负债 (technical debt) — 为求短期快速推进而采用临时修补，累积成未来必须重写才能偿还的债务。
- `mm-tragedy-of-the-commons` — 公地悲剧 (tragedy of the commons) — 共享资源中每个个体理性地多占一点，最终集体耗尽资源，所有人受损。
- `mm-tyranny-of-small-decisions` — 小决定泛滥（暴政） (tyranny of small decisions) — 一系列各自理性的小决定叠加，最终给整个系统带来负面后果。

### 时间与优先级 (45 个)

- `mm-algorithms` — 算法 (algorithms) — 分步骤执行的过程，用来系统性解决某类问题。
- `mm-anti-pattern` — 反面模式 (anti-pattern) — 看似出于直觉、实则不管用的常见「解法」，而该问题本有更好的已知方案。
- `mm-automation` — 自动化 (automation) — 用更高效的处理方式替代人工重复劳动，以持续节省时间与金钱。
- `mm-batna` — 谈判协议的最佳替代方案 (BATNA (best alternative to a negotiated agreement)) — 谈判桌外你手上最好的替代选项，是不接受任何更差方案的底线。
- `mm-black-boxes` — 黑匣子 (black boxes) — 用户只需关心输入输出、不必了解内部运作的封装系统。
- `mm-brute-force` — 暴力解决方案 (brute force) — 不需要巧思、靠直接花力气完成的解法。
- `mm-compound-interest` — 复利 (compound interest) — 利息（或收益）滚入本金继续生息，使增长随时间加速累积。
- `mm-concorde-fallacy` — 协和谬误（承诺升级） (Concorde fallacy / escalation of commitment) — 沉没成本导致承诺不断升级、越陷越深的特有情形。
- `mm-deep-work` — 深度工作 (deep work) — 在无干扰的整块时间里专注思考最重要的问题，以取得突破性进展。
- `mm-default-effect` — 默认效应 (default effect) — 人们倾向于直接接受预设的默认选项，因此默认设置会显著改变行为结果。
- `mm-design-pattern` — 设计模式 (design pattern) — 对某个设计问题可重复使用的解决方案，是已验证有效的既有做法。
- `mm-discounted-cash-flow` — 现金流折现法 (discounted cash flow (DCF)) — 用折现率把未来各期现金流折算为今天的价值，从而给资产或报价估值。
- `mm-divide-and-conquer` — 分而治之，逐个击破 (divide and conquer) — 把问题分解成多个独立部分分别解决，从而更快完成更多任务。
- `mm-economies-of-scale` — 规模经济 (economies of scale) — 随着规模扩大，单位产品成本下降、运作效率提升。
- `mm-eisenhower-decision-matrix` — 艾森豪威尔决策矩阵 (Eisenhower Decision Matrix) — 按「紧急／重要」两个维度把事务分入四象限，据此决定立即做、优先做、委派或忽略。
- `mm-exhaustive-search` — 穷举搜索 (exhaustive search) — 逐一尝试所有可能的组合，直到找到正确答案。
- `mm-heuristic` — 启发式 (heuristic) — 通过反复试错、依靠经验规则求解的方法，不保证最优但通常管用。
- `mm-high-leverage-activities` — 高杠杆活动 (high-leverage activities) — 造成影响远大于其他活动、投入产出比最高的少数活动。
- `mm-hofstadter-s-law` — 侯世达定律 (Hofstadter's law) — 做事花费的时间总是比你预期的长，即使预期中已包含这一定律。
- `mm-hyperbolic-discounting` — 双曲折现 (hyperbolic discounting) — 人们对未来的高折扣率不会随时间修正，表现为偏好即时满足而非延迟满足。
- `mm-law-of-diminishing-returns` — 收益递减法则 (law of diminishing returns) — 成果达到一定程度后，继续增加投入，单位投入带来的产出不断降低。
- `mm-law-of-diminishing-utility` — 效用递减法则 (law of diminishing utility) — 超过某个限度后，每多消费一单位物品带来的价值或满足感低于前一单位。
- `mm-leverage` — 杠杆作用 (leverage) — 把力施加在特定位置能产生远超其他位置的效果，即小投入撬动大产出。
- `mm-loss-aversion` — 损失规避 (loss aversion) — 相比获得同等收益，人更强烈地想避免损失，这常导致更糟的决策。
- `mm-mid-mortems` — 中期分析 / 事前分析 (mid-mortems / pre-mortems) — 在项目进行中（甚至开始前）就分析何处可能出错，提前预判偏离轨道。
- `mm-multitasking` — 多任务处理 (multitasking) — 同时推进多项需集中注意力的任务，实际上只是快速来回切换。
- `mm-negative-returns` — 负收益 (negative returns) — 越过收益递减的临界点后继续投入，总体结果不升反降。
- `mm-net-present-value` — 净现值 (net present value (NPV)) — 未来所有年份折现后收益相加所得的当前价值总额。
- `mm-ninety-ninety-rule` — 九九定律 (ninety-ninety rule) — 前 90% 的代码花 90% 的开发时间，剩余 10% 的代码再花 90% 的时间。
- `mm-north-star` — 北极星 (north star) — 一家公司或个人的指导性长期愿景，用来为所有抉择定向。
- `mm-opportunity-cost` — 机会成本 (opportunity cost) — 做一个选择所放弃的最佳替代机会的价值，应据此在选项中取舍。
- `mm-opportunity-cost-of-capital` — 资本的机会成本 (opportunity cost of capital) — 把资本按次佳方案运用所能取得的回报，是投资决策的最低收益率门槛。
- `mm-parallel-processing` — 并行处理 (parallel processing) — 把一组问题拆开同时求解，而非依次串行处理。
- `mm-pareto-principle` — 帕累托法则（二八定律） (Pareto principle) — 多数情况下 80% 的结果来自 20% 的努力，应把那 20% 投入高杠杆活动。
- `mm-parkinson-s-law` — 帕金森定律 (Parkinson's law) — 工作会不断膨胀，占满一个人完成工作所需的全部时间。
- `mm-parkinson-s-law-of-triviality` — 帕金森琐碎定律 / 自行车棚效应 (Parkinson's law of triviality / bike shedding) — 组织会对琐碎小事给予不成比例的重视，讨论时间与涉及金额成反比。
- `mm-power-law-distribution` — 幂律分布 (power law distribution) — 呈「二八开」的结果分布：相对较少的结果占总量的很大一部分。
- `mm-present-bias` — 现时偏好 (present bias) — 高估当下可获得的即时回报、低估长远目标渐进进步的系统性倾向。
- `mm-reframe-the-problem` — 重新定义问题 (reframe the problem) — 换一种方式表述问题，使原本无解或昂贵的难题变得可解。
- `mm-sayre-s-law` — 塞尔定律 (Sayre's law) — 在任何争议中，情绪强度与所涉及问题的实际价值成反比。
- `mm-social-engineering` — 社会工程 (social engineering) — 通过巧妙操纵社交情境，让人自愿透露本应保密的信息（如密码）。
- `mm-sunk-cost-fallacy` — 沉没成本谬误 (sunk-cost fallacy) — 让已经无法收回的投入影响当前决策，从而继续投入更多。
- `mm-the-top-idea-in-your-mind` — 你脑海中的首要念头 (the top idea in your mind) — 某一时刻占据你胡思乱想时默认浮现位置的那一个问题。
- `mm-the-vital-few` — 关键的少数 (the vital few) — 朱兰对高杠杆活动的称呼：投入最小、效果最好的那部分工作。
- `mm-two-front-wars` — 两线作战 (two-front wars) — 同时在两条战线上分散兵力与注意力，往往导致全线失败。

### 增长与系统 (38 个)

- `mm-2-2-matrices` — 2×2矩阵 (2 × 2 matrices) — 用两个二元维度交叉成四象限，把复杂想法提炼成简单图表并获得洞察。
- `mm-activation-energy` — 活化能 (activation energy) — 启动两种或多种反应物之间化学反应所需的最小能量。
- `mm-black-and-white-fallacy` — 黑白谬误 (black-and-white fallacy) — 误以为事物只能分为黑白两类，而实际上存在中间地带与更多选项。
- `mm-butterfly-effect` — 蝴蝶效应 (Butterfly Effect) — 混沌系统对微小扰动或初始条件的微小改变极为敏感，小因可致大果。
- `mm-cascading-failure` — 连锁故障 (cascading failure) — 系统中某一部分的故障引发波及整个系统的连锁反应。
- `mm-catalyst` — 催化剂 (catalyst) — 能够降低启动反应所需活化能、但自身不被消耗的事物。
- `mm-center-of-gravity` — 重心 (center of gravity) — 物体或系统中质量达到平衡的中心点；军事上指一次行动的核心。
- `mm-chain-reaction` — 链式反应 (chain reaction) — 一个反应的副产物成为下一个反应的原料，各反应以自给自足的方式链接下去。
- `mm-chaotic-systems` — 混沌系统 (chaotic systems) — 可以猜测趋势、但无法精确预测长期整体状态的系统。
- `mm-critical-mass` — 临界量 (critical mass) — 产生自持链式反应所需的最小物质的量；泛指累积量达到阈值引发剧变的点。
- `mm-culture-eats-strategy-for-breakfast` — 文化吃掉战略 (culture eats strategy for breakfast) — 文化的惯性大于战略，与组织文化背道而驰的战略几乎不可能成功。
- `mm-entropy` — 熵 (entropy) — 衡量一个系统无序程度的量；规定越松，可能达到的最大熵越高。
- `mm-experimental-mindset` — 实验思维 (experimental mindset) — 把科学方法简化为日常可执行的持续试验态度，而非正式实验流程。
- `mm-flywheel` — 飞轮 (flywheel) — 起步需要巨大努力、一旦转起来后只需少量投入即可持续积累动能的储能转盘。
- `mm-forcing-function` — 强制函数 (forcing function) — 预先安排好的事件或机制，能促使甚至迫使你采取所需行动。
- `mm-homeostasis` — 动态平衡 (homeostasis) — 机体（或系统）围绕某个目标值持续自我调节，竭力避免偏离现状。
- `mm-in-group-favoritism` — 群内偏爱 (in-group favoritism) — 哪怕分组依据微乎其微甚至完全随机，人们也会更喜欢自己所在的群体。
- `mm-inertia` — 惯性 (inertia) — 物体或观念拒绝改变当前运动状态；质量越大，扭转方向的阻力越大。
- `mm-inflection-point` — 拐点 (inflection point) — 增长曲线出现弯曲或转折的地方；数学上指曲线由凹变凸（或凸变凹）的分界点。
- `mm-lindy-effect` — 林迪效应 (Lindy effect) — 不易腐朽的事物每多存活一年，其预期剩余寿命就增加，存在越久越可能继续存在。
- `mm-luck-surface-area` — 幸运表面积 (luck surface area) — 你在更多情况下与更多人互动，就拥有更大的「表面积」被机会撞上。
- `mm-metcalfe-s-law` — 梅特卡夫定律 (Metcalfe's law) — 网络的价值与节点数平方成正比，即节点相连时网络价值呈非线性增长。
- `mm-momentum` — 动量 (momentum) — 动量等于质量与速度的乘积；惯性只与质量成正比，动量还取决于是否在动、动得多快。
- `mm-natural-selection` — 自然选择 (natural selection) — 拥有生殖优势的性状经若干代筛选后越来越常见，推动物种适应环境。
- `mm-network-effects` — 网络效应 (network effects) — 用户增多使产品价值提升（网络效应），或投入与产出相互强化的正反馈循环（飞轮）。
- `mm-peak` — 峰值 (peak) — 事物流行程度或产出达到最高点、此后开始滑坡的转折点。
- `mm-polarity` — 极性 (polarity) — 一个只有两个可能值的属性，如磁铁的南北极、电荷的正负。
- `mm-potential-energy` — 势能 (potential energy) — 物体储存的、具备被释放潜能的能量（重力、弹性、化学等形式）。
- `mm-s-curves` — S形曲线 (S curves) — 采纳率随时间呈 S 形：起初缓慢、中段陡增、接近饱和时再度放缓。
- `mm-scientific-method` — 科学方法 (scientific method) — 观察—提出假设—检验假设—分析数据—提出新理论的严密循环。
- `mm-second-law-of-thermodynamics` — 热力学第二定律 (second law of thermodynamics) — 在封闭系统中，熵随时间推移自然增加，不会自行减少。
- `mm-shirky-principle` — 舍基原则 (Shirky Principle) — 能提供某个问题解决方案的组织，会努力让这个问题保留下来。
- `mm-strategy-tax` — 战略税 (strategy tax) — 长期锁定某项战略后，为维护该战略而被迫付出的、明知非最优的代价。
- `mm-technology-adoption-life-cycle` — 技术采纳生命周期 (technology adoption life cycle) — 按采纳新事物的时间与方式，把人群分为创新者、早期采纳者、早期大多数、后期大多数、落后者。
- `mm-tipping-point` — 临界点 (tipping point) — 系统开始急剧变化并迅速获得动量的那个点。
- `mm-us-versus-them` — 我们VS他人 (us versus them) — 天生把世界分成「我们」与「他人」、且认为两者得失必然对立的思维框架。
- `mm-win-win` — 双赢 (win-win) — 双方最后都能获益的结局，是大多数谈判与交易的常规而非例外。
- `mm-zero-sum` — 零和 (zero-sum) — 认为一方所得必等于另一方所失、双方损益之和为零的误判。

### 数据与证据 (51 个)

- `mm-a-b-testing` — A/B测试 (A/B testing) — 比较产品 A 版（实验组）与 B 版（对照组）用户行为的随机对照实验，是其在互联网中的流行形式。
- `mm-alternative-hypothesis` — 对立假设 (alternative hypothesis) — 研究者认为两组之间可能出现的最细微的、有意义的改变，是希望被研究证实的真实结果。
- `mm-anecdotal-evidence` — 轶事证据 (anecdotal evidence) — 以非正式手段收集的、源于私下传闻的证据，不能用来替代系统性科学证据。
- `mm-base-rate` — 基础比率 (base rate) — 某事件在总体中的先验发生率，是一切条件概率推算的分母。
- `mm-base-rate-fallacy` — 基础比率谬误 (base rate fallacy) — 计算概率时忽略基础比率，直接把检测准确率当作结论概率。
- `mm-bayes-theorem` — 贝叶斯定理 (Bayes' theorem) — 描述P(A | B)与P(B | A)之间关系的公式，把基础比率纳入概率更新。
- `mm-bernoulli-distribution` — 伯努利分布 (Bernoulli distribution) — 描述"是/否"型单次实验结果（两个值二选一）的概率分布。
- `mm-blinded-experiment` — 盲测 (blinded experiment) — 让参与者（单盲）乃至实验管理与分析者（双盲）不知道分组归属，以阻断偏好对结果的影响。
- `mm-central-limit-theorem` — 中心极限定理 (central limit theorem) — 从同一（乃至不同）分布中取数值求平均，得到的平均值基本遵循正态分布。
- `mm-clustering-illusion` — 聚集性幻觉 (clustering illusion) — 在随机数据中"看出"规律或抱团，并误以为这证明现象不是随机的。
- `mm-conditional-probability` — 条件概率 (conditional probability) — 在另一件事也发生的情况下，某件事发生的概率，记作P(A | B)。
- `mm-confidence-interval` — 置信区间 (confidence interval) — 估算出的一个数值范围，你认为所研究参数的真实值可能落在其中。
- `mm-confounding-factor` — 混淆因素 (confounding factor) — 某个不易察觉的第三方因素，同时影响假定的原因与观察到的效应，从而伪造出因果关联。
- `mm-correlation-does-not-imply-causation` — 相关性不代表因果性 (correlation does not imply causation) — 两件事相继发生或统计上相关，并不能推出前者导致了后者。
- `mm-data-dredging` — 数据捕捞（P值篡改） (data dredging / p-hacking) — 反复做多次检验、筛选子群体，直到挖出一个P值足够小的"显著"结果。
- `mm-false-positive` — 假阳性与假阴性 (false positive / false negative) — 假阳性（误报）是错误地得出阳性结果；假阴性（漏报）是错误地得出阴性结果。
- `mm-frequentist-vs-bayesian` — 频率学派与贝叶斯学派 (Frequentist vs Bayesian) — 统计学两大流派：前者只从多次观测的频率推断，后者允许把先验知识代入推断。
- `mm-gambler-s-fallacy` — 赌徒谬误 (gambler's fallacy) — 误以为独立随机事件会"自我纠正"，前几次偏了则下一次会反向补偿。
- `mm-inverse-fallacy` — 逆谬误 (inverse fallacy) — 把P(A | B)与P(B | A)混为一谈，以为两者概率应该相近。
- `mm-law-of-large-numbers` — 大数定律 (law of large numbers) — 样本量越大，你得出的平均结果就越接近真实的平均值。
- `mm-law-of-small-numbers` — 小数定律 (law of small numbers) — 夸大根据小样本得出的结论，误以为小样本能代表总体规律的谬误。
- `mm-margin-of-error` — 误差范围 (margin of error) — 民调等估计值附带的正负区间（如±3%），表示估计值的不确定幅度。
- `mm-mean` — 均值 (mean) — 平均值/期望值，衡量集中趋势，即数值趋于集中的位置。
- `mm-meta-analysis` — 荟萃分析 (meta-analysis) — 用统计技巧把多项研究的数据合并进一次分析，以提升预测准确性。
- `mm-nocebo-effect` — 反安慰剂效应 (nocebo effect) — 预期会出现副作用，就会真的产生负面效果，即使接受的是假手术也一样。
- `mm-nonresponse-bias` — 无反应偏差 (nonresponse bias) — 被选中的一部分人不参加调查，且不回应的原因与调查主题相关，从而污染结果。
- `mm-normal-distribution` — 正态分布（钟形曲线） (normal distribution) — 呈钟形曲线的概率分布，可解释许多自然现象的发生频率，罕见事件落在其尾部。
- `mm-null-hypothesis` — 原假设 (null hypothesis) — 假设检验的默认起点：测试组与对照组之间没有任何区别。
- `mm-observer-expectancy-bias` — 观察者期望偏差 (observer expectancy bias) — 研究者或观察者的认知偏差会无意中影响实验结果，使其朝期望的方向发展，又称实验者偏差。
- `mm-outliers` — 离群值 (outliers) — 看起来与其他数值格格不入的数据点，需在确定区间之前先被识别和处理。
- `mm-p-value` — P值 (p-value) — 假设原假设为真，得出等于或大于观测结果的概率，是衡量统计显著性的最终标准。
- `mm-placebo-effect` — 安慰剂效应 (placebo effect) — 仅仅"收到你期望能带来积极效果的东西"这一行为本身，就能带来真实的积极效果。
- `mm-power` — 统计功效 (power) — 在设定的假阳性率下，能成功检出真实结果（若其存在）的概率，通常定为80%–90%。
- `mm-prior` — 先验 (prior) — 贝叶斯推断的出发点，即获得新数据之前对该话题已有的了解。
- `mm-publication-bias` — 发表偏倚 (publication bias) — 得出统计显著结果的研究更容易被发表，阴性结果被系统性埋没。
- `mm-randomized-controlled-experiment` — 随机对照实验 (randomized controlled experiment) — 将参与者随机分为实验组与对照组进行比较，是实验设计的"黄金标准"。
- `mm-regression-to-the-mean` — 均值回归 (regression to the mean) — 极端事件之后出现的通常是比较普通的事件，结果会回归接近预期的均值。
- `mm-replication-crisis` — 可重复性危机 (replication crisis) — 大量已发表阳性结果无法被重复实验复现的现象，心理学等领域重现率不足50%。
- `mm-response-bias` — 反应偏差 (response bias) — 回应者因各类认知偏差而无法做出准确或真实的回答，导致答案偏离事实。
- `mm-sample-distribution` — 抽样分布 (sample distribution) — 样本均值本身的分布，描述从样本中得出每种可能估计值的概率。
- `mm-sample-size` — 样本量权衡 (sample size) — 收集的数据点总量，其选择是准确性与成本、时间、受试者风险之间的取舍。
- `mm-selection-bias` — 选择性偏差 (selection bias) — 样本或分组不是随机形成的，导致组间差异无法归因于所研究的那个因素。
- `mm-spurious-correlation` — 虚假相关 (spurious correlation) — 两组变量在统计上呈现相关，但只是随机巧合，没有任何机制上的联系。
- `mm-standard-deviation` — 标准差 (standard deviation) — 衡量数据集中数字与均值相差多少的常用离散度指标，记作希腊字母σ。
- `mm-standard-error` — 标准误差 (standard error) — 抽样分布的标准差，等于样本标准差除以样本量的平方根。
- `mm-statistical-significance` — 统计显著性 (statistical significance) — 观测到的差异大到"若原假设为真则不太可能出现"，从而可以否定原假设的阈值标准。
- `mm-surrogate-endpoint` — 代理指标（替代终点） (surrogate endpoint / proxy measure) — 当真正关心的终点无法直接观测时，用一个与之极为接近的间接指标来代替它。
- `mm-survivorship-bias` — 幸存者偏差 (survivorship bias) — 只统计"幸存"下来的个体，导致样本缺失了失败者，结论系统性偏向乐观。
- `mm-systematic-review` — 系统综述 (systematic review) — 按详细而全面的计划，有组织地评估某一领域全部相关研究成果，以消除评估中的认知偏差。
- `mm-texas-sharpshooter-fallacy` — 得州神枪手谬误 (Texas sharpshooter fallacy) — 先射出数据（乱射一通），再围绕聚集处画靶子，反过来宣称自己精准命中。
- `mm-type-i` — 第一类错误与第二类错误 (type I / type II error) — 统计学对假阳性（第一类，记作α）与假阴性（第二类，记作β）的正式称谓。

### 决策 (30 个)

- `mm-bandwagon-effect` — 从众效应 (bandwagon effect) — 某个观点流行起来后，其他人跟风接受，使共识迅速占据上风；人倾向于接受社交暗示、遵从他人决定。
- `mm-black-swan-events` — 黑天鹅事件 (black swan events) — 后果极端严重、但其发生概率远高于你最初预期的事件。
- `mm-business-case` — 商业案例 (business case) — 概括你决策背后原因的文档，是从第一性原理出发摆出前提、再推出结论的表达形式。
- `mm-cost-benefit-analysis` — 成本收益分析 (cost-benefit analysis) — 把每个选项的成本与收益量化成同一单位（美元）并加总，以净收益高低做决策的分析框架。
- `mm-counterfactual-thinking` — 反事实思维 (counterfactual thinking) — 想象过去发生的事与实际发生的相反，即针对过去提出"如果……会怎么样"。
- `mm-crowdsourcing` — 众包 (crowdsourcing) — 从任何想参与的群众那里寻求（外包）创意或信息，借助互联网很容易实现。
- `mm-decision-tree` — 决策树 (decision tree) — 用倒树状图列出决策点、每个选项的可能结果、各结果概率与后果，以分析不确定情境下的决策。
- `mm-discount-rate` — 折现率 (discount rate) — 把未来的收益与成本折算成今天价值的比率，反映通胀、不确定性与资本机会成本三重影响。
- `mm-divergent-thinking` — 发散思维 (divergent thinking) — 积极让思维发散开来，以找出多种可能解决方案的思维方式。
- `mm-expected-value` — 期望值 (expected value) — 每个可能结果的数值乘以其发生概率后的加总，即长期重复下的平均结果。
- `mm-fat-tailed-distributions` — 肥尾分布 (fat-tailed distributions) — 尾部比正态分布更肥厚的概率分布，即远离均值的极端事件发生概率远高于正态预期。
- `mm-groupthink` — 群体思维 (groupthink) — 由于群体倾向于协同思考而产生的认知偏差：成员寻求共识、回避冲突与争议问题。
- `mm-hysteresis` — 磁滞现象 (hysteresis) — 系统的当前状态取决于它的历史，即系统会"记住"自己先前的状态。
- `mm-lateral-thinking` — 横向思维 (lateral thinking) — 从一个想法横向跳跃至另一个想法的思维方式，即"跳出固有框架"，与批判性思维相反。
- `mm-le-chatelier-s-principle` — 勒夏特列原理 (Le Chatelier's principle) — 已达平衡的系统在外部条件被改变后，会自行调整进入新平衡，通常能部分抵消该变化。
- `mm-local-optimum` — 局部最优与全局最优 (local optimum / global optimum) — 局部最优是公认还不错但并非最佳的解；全局最优是所有可能中最好的那个解。
- `mm-maslow-s-hammer` — 马斯洛之锤 (Maslow's hammer) — 如果你手里只有锤子，那么一切看起来都像钉子——人倾向于用自己仅有的工具处理所有问题。
- `mm-monte-carlo-simulation` — 蒙特卡洛模拟 (Monte Carlo simulation) — 用随机初始条件或随机数值多次独立运行同一系统模拟，以逼近实际结果的概率分布。
- `mm-prediction-market` — 预测市场 (prediction market) — 类似股票市场的机制：股票价格在0到1美元间波动，直接代表市场对某事件发生概率的共识估计。
- `mm-pro-con-list` — 利弊清单 (pro-con list) — 列出某决定的好处与弊端再两相权衡的最简决策框架，是多数人的首选思考工具。
- `mm-scenario-analysis` — 情景分析 (scenario analysis / scenario planning) — 构想若干合理但彼此不同的未来情景，用来发现未知的未知数并更深入地思考可能的未来。
- `mm-sensitivity-analysis` — 敏感性分析 (sensitivity analysis) — 改变模型中的一个输入参数、观察结果如何变化，以判断结果对该参数的敏感程度的方法。
- `mm-simulation` — 仿真模拟 (simulation) — 在电脑上把系统画成示意图并转成可运行模型，设定初始条件后观察系统随时间如何演化。
- `mm-superforecasters` — 超级预测家 (superforecasters) — 反复做出准确预测的人；在预测世界大事上持续击败顶尖情报机构，且缺少机密信息。
- `mm-systems-thinking` — 系统思考 (systems thinking) — 后退一步、把整个系统及其各部分互动纳入考量再做决策的思考方式。
- `mm-thought-experiment` — 思维实验 (thought experiment) — 只在思维中进行、现实世界里并不实际发生的实验。
- `mm-unknown-unknowns` — 未知的未知数（四象限） (unknown unknowns) — 用2×2矩阵把你知道/不知道与知道/不知道交叉，分出已知已知、已知未知、未知已知、未知未知四类。
- `mm-utilitarianism` — 功利主义 (utilitarianism) — 能为所有相关人士带来最大总效用的决策，就是最符合道义的决策。
- `mm-utility-values` — 效用值 (utility values) — 把有形与无形成本收益合并成的一个数，反映你在该情境下的总体相对偏好。
- `mm-wisdom-of-crowds` — 群体的智慧 (wisdom of crowds) — 在满足多样性、独立性、聚合性三条件时，一群人的平均判断能胜过几乎所有个体。

### 冲突与博弈 (59 个)

- `mm-ad-hominem` — 人身攻击 (ad hominem) — 攻击提出观点的人（其身份、资质、标签），而非其观点本身。
- `mm-appeal-to-emotion` — 诉诸情感 (appeal to emotion) — 通过激起恐惧、希望、内疚、自豪、愤怒、悲伤、厌恶等情绪，使人抛开理性决策。
- `mm-appeasement` — 绥靖 (appeasement) — 向对手让步以避免直接冲突或进一步冲突，是地位不足以威慑或遏制时的无奈选项。
- `mm-arms-race` — 军备竞赛 (arms race) — 双方为争夺相对优势不断加码投入，消耗本可用于他处的资源，且没有明确终点。
- `mm-authority` — 权威 (authority) — 人倾向于追随被公认为权威的人，即使对方并非相关领域的专家。
- `mm-bait-and-switch` — 诱购／偷梁换柱 (bait and switch) — 以诱人的低价或条件吸引你（诱饵），实际提供的却是另一件更贵或不同的东西（调包）。
- `mm-broken-windows-theory` — 破窗理论 (broken windows theory) — 可见的轻罪痕迹（如破窗）会营造纵容违法的氛围，进而鼓励重罪。
- `mm-burn-the-boats` — 破釜沉舟／越过卢比孔河 (burn the boats / crossing the Rubicon) — 主动毁掉撤退选项、自绝退路，使团队别无选择只能向前取胜。
- `mm-burning-bridges` — 过河拆桥 (burning bridges) — 退出时破坏与他人或组织的关系，导致事后无法回头。
- `mm-call-your-bluff` — 叫你摊牌 (call your bluff) — 对方通过挑衅逼你把威胁、主张或政策真正付诸实践，以检验你是否虚张声势。
- `mm-carrot-and-stick` — 胡萝卜加大棒 (carrot and stick) — 同时承诺奖励（胡萝卜）与威胁惩罚（大棒），以制止某种行为。
- `mm-commitment` — 承诺 (commitment) — 一旦同意或承诺了某件（哪怕很小的）事，未来就更可能继续同意后续请求。
- `mm-containment` — 遏制 (containment) — 威慑的姊妹模型：在无法撤销既成事实的情况下，阻止其进一步扩散或再次发生。
- `mm-dark-patterns` — 黑暗模式 (dark patterns) — 用伪装、隐藏与制造障碍等方式操纵和迷惑用户的界面与做法。
- `mm-deterrence` — 威慑 (deterrence) — 靠威胁后果来阻止对方采取某种行动；可信的相互确保毁灭即是一种强威慑。
- `mm-distributive-justice` — 分配正义 (distributive justice) — 围绕"东西怎么分"来定义公平，认为平等分配才是公平。
- `mm-domino-effect` — 多米诺骨牌效应 (domino effect) — 一系列连锁反应像多米诺骨牌连续倒下，带来不断放大的负面后果。
- `mm-endgame` — 终局 (endgame) — 国际象棋中大部分棋子被吃掉的收官阶段，引申为任何事件过程的最终阶段。
- `mm-exit-strategy` — 退出策略 (exit strategy) — 预先设计好的、从某种局势中体面撤出的可靠方案，用来锁定收益或减少损失。
- `mm-fair-share-versus-fair-play` — 公平分配与公平竞争之争 (fair share versus fair play) — 关于公平的两套对立表述：结果上的"应有份额"与起点上的"规则公平"。
- `mm-fear` — 惧、惑、疑 (fear, uncertainty, doubt (FUD)) — 靠散布恐惧、不确定性与怀疑来影响他人决策的传播策略。
- `mm-flypaper-theory` — 粘蝇纸理论 (flypaper theory) — 刻意把敌人吸引到其更容易受伤的地方，同时引导他们远离你的宝贵资源。
- `mm-foot-in-the-door-technique` — 得寸进尺技巧 (foot-in-the-door technique) — 先请求一个微不足道的承诺，再逐步提出更大的请求，利用一致性压力达成目标。
- `mm-game-theory` — 博弈论 (game theory) — 研究在冲突情境下如何制定策略、做出决策的学科；把冲突简化为规则明确、结果可量化的博弈。
- `mm-gateway-drug-theory` — 入门毒品理论 (gateway drug theory) — 主张一种较温和的毒品（如大麻）是通往更危险毒品滥用的大门。
- `mm-generals-always-fight-the-last-war` — 将军总在打上一场仗 (generals always fight the last war) — 人们默认沿用过去或上一场战争中奏效的策略、战术与技巧，而它未必适合下一场战争。
- `mm-guerrilla-marketing` — 游击营销 (guerrilla marketing) — 初创企业以极低预算使用非常规营销技巧推广产品，直接瞄准较大的竞争对手。
- `mm-guerrilla-warfare` — 游击战 (guerrilla warfare) — 弱势一方集中小规模部队、用灵活战术骚扰笨重的大部队，使其难以有效回应。
- `mm-hail-mary-pass` — 孤注一掷 (Hail Mary pass) — 在没有可靠退出策略时，为求成功而铤而走险做最后一次努力。
- `mm-honeypot` — 蜜罐 (honeypot) — 设置看起来有价值、实为隔离环境的目标，用来吸引并诱捕恶意行为者。
- `mm-iterated-game` — 重复博弈 (iterated game / repeated game) — 同一批玩家反复进行的博弈；因为存在"未来报复"，合作比单次博弈更容易维持。
- `mm-liking` — 喜好 (liking) — 人更倾向于喜欢与自己有共同点的人，也更愿意接受自己喜欢的人的建议。
- `mm-loss-leader-strategy` — 亏本销售策略 (loss leader strategy) — 以低价"入门产品"吸引客户，再从利润更高的配套产品中赚钱。
- `mm-mirroring` — 镜映 (mirroring) — 交谈中有意识地模仿对方的小动作和口头禅，以赢得信任、被视为同类。
- `mm-mutually-assured-destruction` — 相互确保毁灭 (mutually assured destruction (MAD)) — 双方都拥有摧毁对方的能力，因此任何冲突都会升级为同归于尽，反而形成稳定威慑。
- `mm-nash-equilibrium` — 纳什均衡 (Nash equilibrium) — 一种策略组合：任何一方单方面改变策略，都会使自己的（书中表述为双方的）结果恶化。
- `mm-nuclear-option` — 核选项 (nuclear option) — 最严重的威胁：表示你将被迫采取某种极端、玉石俱焚的行为。
- `mm-payoff-matrix` — 收益矩阵 (payoff matrix) — 以矩阵形式列出各方所有可能选项组合及其对应收益，用来可视化一次博弈的结构。
- `mm-potemkin-village` — 波将金村／面子工程 (Potemkin village) — 专门打造出来、使别人相信情况比实际更好的虚假展示。
- `mm-prisoner-s-dilemma` — 囚徒困境 (prisoner's dilemma) — 双方各自理性地选择背叛，结果比双方合作更糟，形成个体理性与集体最优的冲突。
- `mm-procedural-justice` — 程序正义 (procedural justice) — 围绕"是否遵守透明客观的程序"来定义公平，认为程序公平才是公平。
- `mm-punching-above-your-weight` — 挑战重量级 (punching above your weight) — 主动越级参与高于自身量级的竞争或任务，以弱对强博取超常收益。
- `mm-pyrrhic-victory` — 皮洛士式的胜利 (Pyrrhic victory / hollow victory) — 代价惨重、得不偿失的胜利，虽赢下战斗却损害了赢得整场战争的能力。
- `mm-quarantine` — 隔离 (quarantine) — 通过限制人员或货物的流动来防止有害事物传播的一种遏制策略。
- `mm-reciprocity` — 互惠 (reciprocity) — 人会感到有义务回报别人的好意，即使这份好意原本并非自己所需。
- `mm-red-line` — 红线／底线 (red line / line in the sand) — 公开划出一条对方不可逾越的界线，越过即遭报复，以此改变对方收益矩阵。
- `mm-scarcity` — 稀缺 (scarcity) — 机会越少，人就越感兴趣；稀缺会引发"唯恐错过"的恐惧。
- `mm-scorched-earth` — 焦土战术 (scorched earth) — 撤退时销毁一切（如烧毁土地、销毁记录），使任何人包括自己都无法再使用。
- `mm-slippery-slope-argument` — 滑坡论 (slippery slope argument) — 主张一件小事会不可避免地引发连锁反应并导致糟糕结果。
- `mm-social-norms-vs-market-norms` — 社会规范与市场规范 (social norms vs. market norms) — 同一件事从"社交／人情"还是"金钱／交易"角度描述，会引发完全不同的行为与动机。
- `mm-social-proof` — 社会认同 (social proof) — 人会把"别人正在这么做"当作正确与否的社会暗示，从而跟随多数人的行为。
- `mm-stop-the-bleeding` — 止血 (stop the bleeding) — 局势可能迅速失控时，先迅速果断地控制损害，再寻找根本原因与长期方案。
- `mm-straw-man` — 稻草人 (straw man) — 不直接驳斥对方观点，而是把它歪曲成另一个易于攻击的说法再加以反驳。
- `mm-tit-for-tat` — 以牙还牙 (tit-for-tat) — 重复博弈中的策略：开局先合作，此后照搬对方上一轮的做法。
- `mm-trojan-horse` — 特洛伊木马 (Trojan horse) — 任何看似无害甚至诱人、诱使你放下戒备的东西（典型是"礼物"）。
- `mm-ultimatum-game` — 最后通牒博弈 (ultimatum game) — 一方提出分钱方案、另一方只能接受或拒绝；拒绝则双方一无所获的博弈。
- `mm-vaporware` — 雾件 (vaporware) — 对外宣布一款实际上尚未完成的产品，用于试探需求、评估反应或阻吓竞争对手。
- `mm-war-of-attrition` — 消耗战 (war of attrition) — 一长串耗时良久的战斗持续消耗双方资源，最终资源较少或消耗更快的一方先垮掉。
- `mm-zero-tolerance-policy` — 零容忍政策 (zero-tolerance policy) — 即使是很小的违规行为也立即招致严厉惩罚，而非逐级升级的处罚。

### 团队与成长 (38 个)

- `mm-10000-hour-rule` — 一万小时定律 (10000-Hour Rule) — 格拉德威尔提出，世界一流专家通常需一万小时刻意练习才能达到顶尖水平。
- `mm-10x-engineer` — 十倍工程师与十倍团队 (10x engineer / 10x team) — 效率数倍于常人的个体叫「十倍人才」；让多名成员同时成为十倍贡献者的团队叫「十倍团队」。
- `mm-big-five-personality-traits` — 大五人格（五大关键因素） (Big Five personality traits) — 刘易斯·戈德堡提出的人格五维度：外向性、经验开放性、尽责性、亲和性、神经质。
- `mm-boots-on-the-ground` — 脚踏实地 (boots on the ground) — 要让战靴踏在地面上——只靠远距离作战无法实现最终目标，必须亲自到场互动。
- `mm-commandos` — 突击队员、步兵与警察 (commandos, infantry, and police) — 组织/项目生命周期不同阶段需要三类人：靠速度和奇袭打天下的突击队员、负责规模化执行的步兵、守住并发展成果的警察。
- `mm-consequence-conviction-matrix` — 后果-信心矩阵 (consequence-conviction matrix) — 按「决策后果严重性」与「你对决策的信心程度」两个维度，决定亲自拍板还是委派。
- `mm-cultural-dimensions` — 文化维度谱系（严密/松散、等级/平等、集体/个人、客观/主观） (cultural dimensions (tight-loose, hierarchical-egalitarian, collectivist-individualist, objective-subjective)) — 除高/低语境外，社会学家描述文化的四组常用维度：严密vs松散、等级制vs平等主义、集体主义vs个人主义、客观vs主观。
- `mm-deliberate-practice` — 刻意练习 (deliberate practice) — 让人持续处于能力极限，练习越来越难的技能，并获得实时反馈。
- `mm-diffusion-of-responsibility` — 责任分散（旁观者效应） (diffusion of responsibility / bystander effect) — 身处群体中时，人们因认为责任该由他人承担而不负责任，表现得就像旁观者。
- `mm-directly-responsible-individual` — 直接负责人 (directly responsible individual (DRI)) — 为每项行动明确指定一名负全责的个人，以消除责任分散。
- `mm-dunbar-s-number` — 邓巴数 (Dunbar's number) — 150 是人类能维持稳定、团结的社交群体的人数上限。
- `mm-dunning-kruger-effect` — 邓宁-克鲁格效应 (Dunning-Kruger effect) — 从新手到专家的过程中，信心先因快速进步冲高、再因见识到复杂度骤降、最后随真实经验回升。
- `mm-eq-versus-iq` — 情商与智商 (EQ versus IQ) — 智商衡量智力，情商衡量情绪智力——感知、管理与运用情绪的能力。
- `mm-fixed-mindset-versus-growth-mindset` — 固定型思维 vs. 成长型思维 (fixed mindset versus growth mindset) — 固定型思维相信能力天生固定不可改变；成长型思维相信能力可随时间成长变化。
- `mm-foxes-versus-hedgehogs` — 狐狸与刺猬 (foxes versus hedgehogs) — 刺猬从宏大愿景与单一理念看世界，纵览全局；狐狸关注复杂与微妙之处，重视细节。
- `mm-generalists-versus-specialists` — 通才与专家 (generalists versus specialists) — 通才对很多事都稍有涉猎，专家在单一领域深入钻研，组织应按自身规模与问题分布选用。
- `mm-golem-effect` — 魔像效应 (golem effect) — 期待值降低导致表现变差，是皮格马利翁效应的镜像。
- `mm-group-size-thresholds` — 群体规模阈值（10~15 / 30~50 / 150） (group size thresholds) — 团队规模每到约10~15人、30~50人、150人，原本运转的组织方式就会崩溃，需要新架构。
- `mm-high-context-versus-low-context-communication` — 高语境与低语境沟通 (high-context versus low-context communication) — 低语境沟通直接明了、绝大部分信息已明说；高语境沟通含蓄，需大量上下文与非语言线索才能理解。
- `mm-hindsight-bias` — 后见之明偏差 (hindsight bias) — 事件发生后，你在事后看来会认为它原本可以预测，尽管并无客观依据。
- `mm-impostor-syndrome` — 冒名顶替综合征 (impostor syndrome) — 明明并非骗子，却深信自己是冒名顶替者，生怕被人识破。
- `mm-introverts-versus-extroverts` — 内向型与外向型 (introverts versus extroverts) — 内向者从独处与小群体中获取能量，外向者从大群体互动中获取能量，二者适配的团队角色不同。
- `mm-joy-s-law` — 乔伊法则 (Joy's Law) — 无论你是谁，大多数最聪明的人总是在为别人工作，伟人不会集中在同一组织内。
- `mm-learning-curve` — 学习曲线 (learning curve) — 技能随练习与经验积累而提升的曲线，初期上升最快，越往后越平缓。
- `mm-loyalists-versus-mercenaries` — 效忠者 vs. 雇佣兵 (loyalists versus mercenaries) — 效忠者即使面对逆境也致力于组织发展；雇佣兵主要为赚钱，更可能为更高回报离开。
- `mm-manager-s-schedule-versus-maker-s-schedule` — 管理者日程 vs. 匠人日程 (manager's schedule versus maker's schedule) — 管理者以「小时」为单位切分时间，匠人（程序员、作家等）需要以「半天」为单位的整块时间。
- `mm-managing-to-the-person` — 以人为本的管理 (managing to the person) — 根据每个人独特的个性和具体情况调整管理方式，而不是按岗位、或用同一套方法管理所有人。
- `mm-maslow-s-hierarchy-of-needs` — 马斯洛需求层次 (Maslow's hierarchy of needs) — 从生理、安全、爱与归属、自尊到自我实现的层级结构，底层需求满足后才能专注顶层的自我实现。
- `mm-peter-principle` — 彼得原理 (Peter principle) — 人们依据过往表现被不断晋升，最终会到达其无法胜任的层级并在那里备受煎熬。
- `mm-power-vacuum` — 权力真空 (power vacuum) — 掌权者突然离开留下空缺，其他人会迅速涌入填补；组织可刻意创造它来识别人选。
- `mm-pygmalion-effect` — 皮格马利翁效应 (Pygmalion effect) — 他人对你的期待越高，你为符合期待而表现提升越明显。
- `mm-radical-candor` — 坦诚相待（2×2 反馈矩阵） (Radical Candor) — 金·斯科特提出：有效反馈 =「直接挑战」×「个人关怀」两轴都高，即右上象限的坦诚相待。
- `mm-rumsfeld-s-rule` — 拉姆斯菲尔德法则 (Rumsfeld's Rule) — 你是带着现有的部队参战，而不是带着你想要或希望拥有的部队参战。
- `mm-spacing-effect` — 间隔效应 (spacing effect) — 学习之间留出时间间隔，比把等量内容压缩在短时间内（填鸭）效果更好。
- `mm-strategy-versus-tactics` — 策略与战术 (strategy versus tactics) — 策略是大局、长期、界定最终成功的样子；战术是细节、短期、界定下一步的目标。
- `mm-the-mythical-man-month` — 人月神话 (the mythical man-month) — 「人/月」作为工期单位的前提——投入更多人就能更快完成——是错误的。
- `mm-unicorn-candidate` — 独角兽候选人 (unicorn candidate) — 组织设置了不切实际的岗位，只有像独角兽一样几乎不存在的候选人才能填补。
- `mm-winning-hearts-and-minds` — 赢得人心 (winning hearts and minds) — 通过沟通直击人心、动之以情来赢得支持，而非靠命令或利益收买。

### 竞争与战略 (33 个)

- `mm-arbitrage` — 套利 (arbitrage) — 利用同一物品在不同市场或情境下的价格差，低买高卖赚取差价。
- `mm-back-of-the-envelope-calculation` — 粗略计算 (back-of-the-envelope calculation) — 在信封背面就能完成的快速数量级估算，用于迅速检验假设。
- `mm-barriers-to-entry` — 进入壁垒与退出壁垒 (barriers to entry / barriers to exit) — 阻止个人或企业进入、退出某个市场或局面的障碍，是护城河的两面。
- `mm-beachhead` — 滩头堡 (beachhead) — 军事上先占领并保卫一小片海滩、供后续兵力登陆的立足点，引申为切入市场的起点。
- `mm-bright-spots` — 亮点 (bright spots) — 众多消极迹象中的积极迹象，是判断是否值得坚持、从哪里突破的线索。
- `mm-consensus-contrarian-matrix` — 顺势-逆势矩阵 (consensus-contrarian matrix) — 用"对/错"与"顺势/逆势"两个维度构成的 2×2 矩阵，判断下注的回报潜力。
- `mm-crossing-the-chasm` — 跨越鸿沟 (crossing the chasm) — 杰弗里·摩尔提出：创意与技术常卡在早期采纳者与早期大多数之间的鸿沟里，无法进入主流。
- `mm-customer-development` — 客户开发 (customer development) — 史蒂夫·布兰克提出的以客户为中心的产品开发模型，用快速试验找出可持续商业模式。
- `mm-disruptive-innovations` — 颠覆性创新 (disruptive innovations) — 克里斯坦森提出：起初在主流指标上逊于现有技术、但因便利性等新属性逐渐蚕食市场并改朝换代的技术。
- `mm-first-mover-advantage` — 先发优势与先发劣势 (first-mover advantage / first-mover disadvantage) — 率先把产品推向市场可获竞争优势，但若犯下过多错误，反而让后来者占便宜。
- `mm-heat-seeking-missiles` — 热源追踪导弹 (heat-seeking missiles) — 把成功创业者比作发射后持续修正轨迹、最终锁定目标的导弹。
- `mm-idea-maze` — 创意迷宫 (idea maze) — 把实现创意比作穿越迷宫：入口是畅想，出口是大获成功，途中布满死路。
- `mm-jobs-to-be-done` — 待办任务 (jobs to be done) — 弄清客户实际"雇用"你的产品去完成什么任务，而不是产品自称做什么。
- `mm-lock-in` — 锁定效应 (lock-in) — 因转换成本过高而被现有服务、关系或局面绑住，难以脱离的状态。
- `mm-market-power` — 市场支配力 (market power) — 在市场上提高价格仍能保住客户、从中获利的能力，是持续竞争优势的标志。
- `mm-moat` — 护城河 (moat) — 巴菲特推广的比喻：环绕城堡的深水渠，指抵御竞争对手、维持持续竞争优势的结构性屏障。
- `mm-monopoly` — 垄断 (monopoly) — 缺乏竞争者的市场结构，是市场支配力的极端表现。
- `mm-only-the-paranoid-survive` — 只有偏执狂才能生存 (Only the paranoid survive) — 安迪·葛洛夫的原则：即使身处鼎盛，也必须持续警惕并加固护城河。
- `mm-ooda-loop` — 包以德循环 (OODA Loop) — 由观察、调整、决策、行动四步构成的快速决策循环，循环越快越占优势。
- `mm-perfect-competition` — 完全竞争／商品化 (perfect competition / commodities) — 众多竞争者提供完全相同的完全替代品，任何供给者都不具备市场支配力。
- `mm-personas` — 用户角色模型 (personas) — 代表理想客户的虚拟角色，用于从客户视角评估创意与决策。
- `mm-pivot` — 转型 (pivot) — 在大量客户开发后仍无法达成产品/市场匹配时，转变战略方向。
- `mm-product` — 产品/市场匹配 (product/market fit) — 产品与市场高度契合，客户主动要求增加供应，公司由此难以被逐出市场。
- `mm-regulatory-capture` — 管制俘获 (regulatory capture) — 监管机构或立法者被本该监管的特殊利益集团俘获，反过来在竞争中保护它们。
- `mm-resonant-frequency` — 共振频率 (resonant frequency) — 每个物体都有自然振动频率，外界激励与之吻合时振幅急剧放大，甚至震碎玻璃。
- `mm-secret` — 秘密 (secret) — 关于世界运作方式、公开但尚未被普遍察觉的重要真相，是伟大企业的地基。
- `mm-simultaneous-invention` — 同步发明／多重发现 (simultaneous invention / multiple discovery) — 相互独立的人在同一时期做出相似发现或创办相似企业的现象。
- `mm-supply-and-demand` — 供求关系 (supply and demand) — 市场价格由供给量与需求量的相对关系决定，稀缺则价高、过剩则价低。
- `mm-sustainable-competitive-advantage` — 持续竞争优势 (sustainable competitive advantage) — 一系列能让你在竞争中长期保持优势、从而持续获利的因素。
- `mm-switching-costs` — 转换成本 (switching costs) — 客户改用其他供应商所需付出的代价，代价越高越难被抢走。
- `mm-what-type-of-customer-are-you-hunting` — 你搜寻的是哪种类型的客户 (What type of customer are you hunting?) — 按客户付费量级（苍蝇到鲸鱼）测算，弄清需要多少客户才能达成目标。
- `mm-why-now` — 为什么是现在 (why now) — 追问"为何此刻才是做这件事的时机"，用时机成熟度检验创意的可行性。
- `mm-winner-take-most-markets` — 赢家通吃市场 (winner-take-most markets) — 一家公司一旦取得关键规模或支配力，就迅速吸走大部分用户与市场的格局。

---

## 边界

- **不要在本 skill 内直接回答**模型内容 —— 它只是索引。定位后必须加载目标 skill。
- 用户已点名具体模型时(如"用第一性原理分析一下"),直接调用那个 skill,不要经过本路由。
- A/B 分级只代表书中讲解完整度,不代表重要性;部分 B 级模型(如大数定律)实用性极高。
- 书中未收录的模型不要硬套。

---

## 审计信息

- 覆盖: 377 个已蒸馏 skill (另 79 个 C 级模型仅入 GLOSSARY)
- 生成: cangjie-skill 流水线自动生成
- 蒸馏日期: 2026-09-09