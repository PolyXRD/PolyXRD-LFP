"""简体中文文案表。

约定
----
- 键用点分命名，前缀即归属模块（``menu.`` / ``panel.`` / ``row.`` / ``csv.``…）。
- ``row.*`` 是**结果行标签**（界面卡片与报告共用），与 ``csv.*``（导出列名）
  分开放，两者措辞可以不同：前者求短（卡片窄），后者求准（表格可宽）。
- 正文里需要插值的用 ``{name}`` 占位，由 :func:`lfp.i18n.tr` 的 ``**kw`` 填充；
  含字面花括号时写成 ``{{`` / ``}}``。
- 单位一律半角、与数值间留一个空格（``10.329 Å`` / ``21.43 %``）。
"""

from __future__ import annotations

TRANSLATIONS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # 通用
    # ------------------------------------------------------------------ #
    "app.title": "LiFePO4 物相判定与 Rietveld 精修",
    "btn.ok": "确定",
    "btn.cancel": "取消",
    "btn.close": "关闭",
    "btn.browse": "浏览…",
    "state.on": "开",
    "state.off": "关",

    # ------------------------------------------------------------------ #
    # 菜单
    # ------------------------------------------------------------------ #
    "menu.file": "文件(&F)",
    "menu.file.open": "导入 XRD 谱图…",
    "menu.file.export_html": "导出分析报告（HTML）…",
    "menu.file.export_csv": "导出结果汇总（CSV）…",
    "menu.file.export_pattern": "导出拟合谱（CSV）…",
    "menu.file.export_bragg": "导出布拉格反射表（CSV）…",
    "menu.file.export_peaks": "导出寻峰结果（CSV）…",
    "menu.file.export_png": "导出谱图（PNG）…",
    "menu.file.exit": "退出",

    "menu.process": "谱图处理(&P)",
    "menu.process.smooth": "平滑（Savitzky–Golay）…",
    "menu.process.background": "扣背景…",
    "menu.process.ka2": "去除 Kα2…",
    "menu.process.peaks": "寻峰",
    "menu.process.reset": "恢复原始谱图",
    "menu.process.export_peaks": "导出寻峰结果（CSV）…",

    "menu.language": "语言(&L)",

    "menu.view": "视图(&V)",
    "menu.view.fit": "显示拟合结果图",
    "menu.view.spectrum": "显示处理后的谱图",

    "menu.help": "帮助(&H)",
    "menu.help.about": "关于 PolyXRD LFP",
    "menu.help.copyright": "版权与许可",

    # ------------------------------------------------------------------ #
    # 工具条
    # ------------------------------------------------------------------ #
    "toolbar.open": "导入谱图",
    "toolbar.smooth": "平滑",
    "toolbar.bg": "扣背景",
    "toolbar.ka2": "去 Kα2",
    "toolbar.peaks": "寻峰",
    "toolbar.reset": "原始谱",
    "toolbar.export": "导出",

    # ------------------------------------------------------------------ #
    # 面板标题
    # ------------------------------------------------------------------ #
    "panel.sample": "样品与测量条件",
    "panel.conditions": "测量条件",
    "panel.structure": "结构模型（CIF）",
    "panel.verdict": "LiFePO4 物相判定",
    "panel.refine": "Rietveld 精修",
    "panel.result": "精修结果",

    "sample.name": "样品名",
    "sample.placeholder": "可不填，缺省用文件名",

    # 测量条件（row.meta.* 由 SamplePanel 按 row.<key> 取标签）
    "meta.file": "数据文件",
    "meta.anode": "阳极靶",
    "meta.wavelength": "波长 λ",
    "meta.range": "2θ 范围",
    "meta.step": "步长",
    "meta.points": "数据点数",
    "row.meta.file": "数据文件",
    "row.meta.anode": "阳极靶",
    "row.meta.wavelength": "波长 λ",
    "row.meta.range": "2θ 范围",
    "row.meta.step": "步长",
    "row.meta.points": "点数",

    # ------------------------------------------------------------------ #
    # 结构模型
    # ------------------------------------------------------------------ #
    "struct.import": "导入 CIF…",
    "struct.builtin": "内置 · {name}",
    "struct.imported": "自定义 · {name}",
    "struct.atoms.value": "{asym} 位 / {sym} 操作 / {total} 原子",
    "struct.not_lfp_warn": (
        "当前结构不含 Li–Fe–P–O 四种元素，不是磷酸铁锂模型。"
        "精修结果将失去物理意义，请导入 LiFePO4 的 CIF。"),
    "row.struct.formula": "化学式",
    "row.struct.sg": "空间群",
    "row.struct.system": "晶系",
    "row.struct.point": "点群",
    "row.struct.laue": "劳厄群",
    "row.struct.bravais": "布拉维格子",
    "row.struct.atoms": "不对称单元",

    # ------------------------------------------------------------------ #
    # 判定
    # ------------------------------------------------------------------ #
    "ident.rerun": "重新判定",
    "ident.running": "正在判定…",
    "ident.top3.value": "{n} / 3 条",
    "ident.note": (
        "判据：实测峰被 LFP 参考峰解释的强度占比（覆盖率）≥ 70 %、"
        "前三强线全部命中、未被解释的强度 ≤ 35 %。三条同时满足才判为 LiFePO4。"),
    "ident.note.pass": (
        "全部判据通过，谱图与 LiFePO4（Pnma）参考峰一致，可以进行结构精修。"),
    "ident.note.partial": (
        "部分判据未通过：该谱图尚不足以认定为 LiFePO4，按软件纪律不进入精修。"
        "未通过的具体判据列于下方，请先解决对应问题再重新判定。"),
    "ident.note.fail": (
        "判据明显不通过：该谱图与 LiFePO4 参考峰不匹配，判定为非 LiFePO4，"
        "已终止后续精修。"),
    "row.ident.verdict": "结论",
    "row.ident.coverage": "覆盖率",
    "row.ident.top3": "前三强线",
    "row.ident.unexplained": "未解释强度",
    "row.ident.shift": "零点偏移",
    "row.ident.resid": "峰位残差",
    "row.ident.cell": "预拟合 a / b / c",
    "ident.verdict.pass": "是 LiFePO4",
    "ident.verdict.partial": "疑似含第二相",
    "ident.verdict.fail": "非 LiFePO4",
    "ident.resid.value": "{rms:.3f}° （容差 {tol:.3f}°）",
    "ident.reason.head": "未通过判据：",
    "ident.reason.coverage": "覆盖率 {cov:.1f} % < 70 %",
    "ident.reason.top3": "前三强线仅命中 {n} / 3 条",
    "ident.reason.unexplained": "未解释强度 {unexp:.1f} % > 35 %",
    "ident.reason.model": (
        "峰位残差 {rms:.3f}° 达容差 {tol:.3f}° 的 {ratio:.0%}（上限 45 %）："
        "峰位无法用「零点 + 各向同性胀缩」解释，"
        "样品存在各向异性形变或杂相叠加"),
    "dlg.notlfp.resid": "\n\n峰位残差 RMS = {rms:.4f}°（容差的 {ratio:.0%}）",
    "ident.note.gate": (
        "判据全部基于峰位与强度，对峰位系统性错位不敏感；"
        "因此另设一道闸门：扣掉零点与整体胀缩后，配对峰的峰位残差必须小于"
        "位置容差的 45 %。超出说明这两参数解释不了实测峰位"
        "（如晶胞各向异性形变），按纪律不进入精修。"),

    # ------------------------------------------------------------------ #
    # 精修进度（内核 progress_cb 直接显示在忙窗与状态栏）
    # ------------------------------------------------------------------ #
    "stage.identify": "正在判定是否为 LiFePO4…",
    "stage.progress": "精修阶段 {i}/{n}：{label}",
    "stage.linear": "线性层（标度 + 背景）",
    "stage.shape": "峰形（零点 + 尺寸/应变 + 不对称）",
    "stage.cell": "晶胞（a / b / c）",
    "stage.full": "完整模型",
    "stage.build": "正在构建精修模型…",
    "stage.eval": "已评估 {n} 次 · 当前 Rwp = {rwp:.2f}%",
    "stage.final": "正在合成最终计算谱…",
    "stage.rbragg": "正在计算 R_Bragg…",
    "stage.done": "完成",

    # ------------------------------------------------------------------ #
    # 精修面板
    # ------------------------------------------------------------------ #
    "refine.bg": "背景",
    "refine.bg.cheb": "Chebyshev 多项式",
    "refine.bg.tent": "线性插值（tent）",
    "refine.nbg": "项数",
    "refine.range": "2θ 范围",
    "refine.run": "开始精修",
    "refine.cancel": "取消精修",

    "opt.cell": "晶胞 a / b / c",
    "opt.cell.tip": "正交晶系三条边长同时放开；由判定阶段的预拟合值出发。",
    "opt.zero": "零点偏移",
    "opt.zero.tip": "样品位移/仪器零位造成的整体 2θ 平移（°）。",
    "opt.size": "晶粒尺寸",
    "opt.size.tip": "Scherrer 尺寸（Lorentzian 宽化），单位 nm。",
    "opt.strain": "微应变",
    "opt.strain.tip": "Wilson 微应变（β = 4ε·tanθ），无量纲。",
    "opt.asym": "不对称",
    "opt.asym.tip": "低角峰的不对称拖尾（轴向发散/样品穿透）。",
    "opt.po": "择优取向",
    "opt.po.tip": "March–Dollase 择优取向（020 方向），压片样品常有。",
    "opt.uvw": "仪器宽化 U V W",
    "opt.uvw.tip": "Caglioti 仪器半高宽参数；有标样时建议放开。",
    "opt.bfactor": "温度因子 B",
    "opt.bfactor.tip": "整体各向同性 B 因子（Å²），与晶粒尺寸强相关，易发散。",

    # ------------------------------------------------------------------ #
    # 结果
    # ------------------------------------------------------------------ #
    "res.group.cell": "晶胞参数",
    "res.group.sym": "对称性",
    "res.group.micro": "微结构",
    "res.group.fit": "拟合优度",
    "res.note": (
        "Rwp 的绝对值受计数统计限制：快扫低计数谱的 Rexp 本身就高，"
        "Rwp 不可能做到很低。因此同时看 GOF = Rwp/Rexp（1 附近最佳；"
        "小于 1 表示 σ 偏大而非拟合更好）。R_B 判读：{rb_verdict}。"),
    "row.res.a": "a",
    "row.res.b": "b",
    "row.res.c": "c",
    "row.res.alpha": "α",
    "row.res.beta": "β",
    "row.res.gamma": "γ",
    "row.res.volume": "晶胞体积 V",
    "row.res.system": "晶系",
    "row.res.sg": "空间群",
    "row.res.point": "点群",
    "row.res.laue": "劳厄群",
    "row.res.bravais": "布拉维格子",
    "row.res.size": "晶粒尺寸 D",
    "row.res.strain": "微应变 ε",
    "row.res.fwhm": "FWHM (35.6°)",
    "row.res.eta": "η (35.6°)",
    "row.res.rwp": "Rwp",
    "row.res.rp": "Rp",
    "row.res.rexp": "Rexp",
    "row.res.chi2": "χ²",
    "row.res.gof": "GOF",
    "row.res.rb": "R_Bragg",
    "row.res.verdict": "判读",

    "verdict.rwp.excellent": "优秀",
    "verdict.rwp.good": "良好",
    "verdict.rwp.consistent": "拟合已充分",
    "verdict.rwp.acceptable": "可接受",
    "verdict.rwp.poor": "偏低，建议检查模型",
    "verdict.gof.good": "接近 1",
    "verdict.gof.fair": "略高",
    "verdict.gof.poor": "明显偏高",
    "verdict.gof.low": "小于 1（σ 偏大）",
    "verdict.rb.good": "结构模型与实测强度吻合良好",
    "verdict.rb.fair": "可接受，弱峰区可能欠准",
    "verdict.rb.poor": "偏低，结构模型需复核",
    "verdict.rb.unknown": "未计算",

    # ------------------------------------------------------------------ #
    # 画布
    # ------------------------------------------------------------------ #
    "canvas.x_label": "2θ (°)",
    "canvas.y_label": "强度 (counts)",
    "canvas.y_diff": "差值",
    "canvas.empty": "导入 XRD 谱图后在此显示",
    "canvas.bragg": "布拉格位置",
    "canvas.legend.obs": "实测",
    "canvas.legend.calc": "计算",
    "canvas.legend.bg": "背景",
    "canvas.legend.err": "实测 − 计算",
    "canvas.legend.peaks": "寻峰",

    # ------------------------------------------------------------------ #
    # 对话框
    # ------------------------------------------------------------------ #
    "dialog.about.title": "关于 PolyXRD LFP",
    "dialog.copyright.title": "版权与许可",
    "about.features": (
        "面向磷酸铁锂（LiFePO4，橄榄石型，Pnma）正极材料的专用工具："
        "导入谱图后先做物相判定，确认是 LiFePO4 才进入 Rietveld 全谱精修；"
        "精修给出晶胞参数、晶系/点群/空间群/劳厄群、晶粒尺寸与微应变，"
        "以及 Rwp / Rp / Rexp / χ² / GOF / R_Bragg 等拟合优度因子。"),
    "about.contact": "联系方式",
    "about.rights": "版权所有",
    "copyright.head": "PolyXRD LFP · 版权与许可",

    "dlg.smooth.title": "平滑（Savitzky–Golay）",
    "dlg.smooth.window": "窗口点数",
    "dlg.smooth.order": "多项式阶数",
    "dlg.smooth.hint": (
        "窗口取得越大越平滑，但会压低峰高、展宽峰形；阶数越高保形越好。"
        "建议：窗口 9–21（奇数）、阶数 2–4。平滑只影响显示与寻峰，"
        "精修始终使用原始谱。"),
    "dlg.bg.title": "扣背景",
    "dlg.bg.method": "方法",
    "dlg.bg.iter": "SNIP 迭代次数",
    "dlg.bg.order": "多项式阶数",
    "dlg.bg.hint": (
        "SNIP 适合有台阶状背景的谱（迭代次数越大背景越低）；多项式适合平缓"
        "背景；端点线性只连两端点。扣除结果仅影响显示与寻峰，精修使用模型背景。"),
    "bg.snip": "SNIP 迭代削峰",
    "bg.poly": "多项式拟合",
    "bg.linear": "端点线性",
    "dlg.ka2.title": "去除 Kα2",
    "dlg.ka2.anode": "阳极靶",
    "dlg.ka2.ratio": "I(Kα2)/I(Kα1)",
    "dlg.ka2.hint": (
        "Rachinger 递推剥离，自高角向低角逐点扣除 Kα2 分量。"
        "常规 Cu 靶取 0.50；剥离后的谱仅用于显示与寻峰，"
        "精修时 Kα1/Kα2 双线由前向模型显式处理。"),
    "busy.title": "请稍候",
    "busy.starting": "正在准备…",
    "busy.canceling": "正在取消…",
    "dlg.notlfp.title": "判定结果：非 LiFePO4",
    "dlg.notlfp.text": "该谱图未被判定为 LiFePO4，已终止后续精修。",
    "dlg.notlfp.info": (
        "覆盖率 {cov:.1f} %，前三强线命中 {top} / 3，"
        "未解释强度 {unexp:.1f} %。"),
    "dlg.notlfp.detail": (
        "实测峰 {n} 条；LFP 参考峰 {refs} 条，匹配 {matched} 条，"
        "匹配容差 ±{tol:.3f}°；反解零点偏移 {dz:+.3f}°，"
        "应变尺度 {e:+.2f} %。"),

    # ------------------------------------------------------------------ #
    # 文件对话框
    # ------------------------------------------------------------------ #
    "filter.pattern": "XRD 谱图 (*.txt *.xy *.xye *.dat *.csv *.asc *.prn);;所有文件 (*)",
    "filter.cif": "CIF 结构文件 (*.cif);;所有文件 (*)",
    "filter.html": "HTML 报告 (*.html)",
    "filter.csv": "CSV 表格 (*.csv)",
    "filter.png": "PNG 图片 (*.png)",
    "dlg.open.title": "导入 XRD 谱图",
    "dlg.save.report": "保存分析报告",
    "dlg.save.csv": "保存 CSV",
    "dlg.save.png": "保存谱图",
    "dlg.import_cif.title": "导入 CIF 结构文件",

    # ------------------------------------------------------------------ #
    # 状态栏与提示
    # ------------------------------------------------------------------ #
    "status.ready": "就绪 · 请导入 XRD 谱图",
    "status.loading": "正在读取谱图…",
    "status.loaded": "已导入 {name}（{n} 点，{lo:.2f}–{hi:.2f}°）",
    "status.identifying": "正在判定是否为 LiFePO4…",
    "status.non_lfp": "判定为非 LiFePO4，已终止后续操作",
    "status.lfp": "判定为 LiFePO4，可进行结构精修",
    "status.refining": "正在精修…",
    "status.refined": "精修完成：Rwp = {rwp:.2f} %，GOF = {gof:.3f}，用时 {sec:.1f} s",
    "status.canceled": "已取消",
    "status.processed": "已应用：{what}",
    "status.reset": "已恢复原始谱图",
    "status.exported": "已导出 {path}",
    "status.struct_loaded": "已载入结构模型：{name}",

    "err.open.title": "无法读取谱图",
    "err.open.text": "文件读取失败：\n{msg}",
    "err.open.hint": (
        "支持两列文本（2θ 强度）或三列（2θ 强度 权重/σ）。"
        "若为仪器专有二进制格式，请先导出为文本。"),
    "err.cif.title": "无法读取 CIF",
    "err.cif.text": "CIF 解析失败：\n{msg}",
    "err.refine.title": "精修失败",
    "err.refine.text": "精修过程中出现异常：\n{msg}",
    "err.no_data.title": "尚无数据",
    "err.no_data.text": "请先导入 XRD 谱图。",
    "err.no_result.text": "请先完成精修，再导出结果。",
    "err.peaks_empty": "未检出显著峰（可降低阈值或先平滑）。",
    "confirm.cancel_refine": "精修已取消。",

    # ------------------------------------------------------------------ #
    # 报告
    # ------------------------------------------------------------------ #
    "report.title": "磷酸铁锂 XRD 物相判定与 Rietveld 精修报告",
    "report.generated": "生成时间 {ts}",
    "report.sample": "样品与数据",
    "report.sample_name": "样品名",
    "report.file": "数据文件",
    "report.identify": "物相判定",
    "report.cell": "晶胞与对称性",
    "report.micro": "微结构",
    "report.fit": "拟合优度",
    "report.params": "精修参数",
    "report.figure": "观测 / 计算 / 差值图",
    "report.bragg": "布拉格反射（按计算强度取前 40 条）",
    "report.col.2th": "2θ (°)",
    "report.col.hkl": "h k l",
    "report.col.icalc": "I_calc",
    "report.col.iobs": "I_obs",
    "report.rwp_note": (
        "Rwp 与数据计数统计强相关：快扫、低计数的谱图 Rexp 本身就高，"
        "Rwp 无法做到很低。请结合 GOF = Rwp/Rexp 判读（1 附近最佳）。"),
    "report.limit": (
        "方法说明：本报告为单相 Rietveld 全谱拟合结果，峰形采用 "
        "pseudo-Voigt（Thompson–Cox–Hastings 合成），晶粒尺寸按 Scherrer "
        "公式（K = 0.9）、微应变按 Wilson 公式给出，未扣除仪器宽化。"
        "R_Bragg 采用 profile-partitioned 口径：重叠峰按计算峰形振幅分摊"
        "观测强度，未建模的第二相不计入，因此强重叠样品的 R_B 会偏低。"
        "晶体结构与对称性信息来自内置 CIF（Yamada et al., J. Electrochem. "
        "Soc. 148 (2001) A224）。若样品含碳包覆层或无定形相，其散射只进入"
        "背景，不参与结构因子计算。"),
    "report.footer": "本报告由 PolyXRD LFP 自动生成，数值可追溯至同名 CSV 导出文件。",

    # ------------------------------------------------------------------ #
    # 版次与注册
    # ------------------------------------------------------------------ #
    "about.edition": "版次",
    "about.edition.internal": "内部评估版",
    "about.edition.registered": "注册版",
    "about.registered_to": "注册单位：{unit}",
    "about.unregistered": "未注册（试用可用，商业用途需注册）",
    "status.registered": "注册成功：{unit}",

    # ------------------------------------------------------------------ #
    # CSV 列名
    # ------------------------------------------------------------------ #
    "csv.col.item": "项目",
    "csv.col.value": "数值",
    "csv.col.2th": "2θ(°)",
    "csv.col.obs": "实测",
    "csv.col.calc": "计算",
    "csv.col.diff": "差值",
    "csv.col.bg": "背景",
    "csv.col.hkl": "hkl",
    "csv.col.iobs": "I_obs",
    "csv.col.icalc": "I_calc",
    "csv.col.height": "净峰高",
    "csv.col.fwhm": "FWHM(°)",
    "csv.col.eta": "η",
    "csv.col.area": "净面积",
    "csv.col.snr": "SNR",
    "csv.col.r2": "拟合R²",
    "csv.sample": "样品名",
    "csv.file": "数据文件",
    "csv.anode": "阳极靶",
    "csv.wavelength": "波长(Å)",
    "csv.range": "2θ范围(°)",
    "csv.step": "步长(°)",
    "csv.ident": "物相判定",
    "csv.coverage": "覆盖率",
    "csv.unexplained": "未解释强度",
    "csv.resid": "峰位残差RMS(°)",
    "csv.resid_ratio": "峰位残差/容差",
    "csv.reason": "未通过判据",
    "csv.a": "a(Å)",
    "csv.b": "b(Å)",
    "csv.c": "c(Å)",
    "csv.alpha": "α(°)",
    "csv.beta": "β(°)",
    "csv.gamma": "γ(°)",
    "csv.volume": "V(Å³)",
    "csv.system": "晶系",
    "csv.spacegroup": "空间群",
    "csv.sg_number": "空间群编号",
    "csv.pointgroup": "点群",
    "csv.laue": "劳厄群",
    "csv.bravais": "布拉维格子",
    "csv.size": "晶粒尺寸(nm)",
    "csv.strain": "微应变(%)",
    "csv.zero": "零点偏移(°)",
    "csv.rwp": "Rwp(%)",
    "csv.rp": "Rp(%)",
    "csv.rexp": "Rexp(%)",
    "csv.chi2": "chi2",
    "csv.gof": "GOF",
    "csv.rb": "R_Bragg(%)",
    "csv.nparams": "参数个数",
    "csv.points": "数据点数",
    "csv.elapsed": "用时(s)",
}
