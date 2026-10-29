"""日本語文案表。

約束
----
- キーはドット区切り（``menu.`` / ``panel.`` / ``row.`` / ``csv.``…）。
  キー集合は zh_CN / en_US と**完全に一致**させる（欠けると画面に ``⟪key⟫``
  が出る。``tests`` の i18n 検査で担保）。
- ``row.*`` は結果行ラベル（カードとレポートで共用）、``csv.*`` は書き出し列名。
  前者は短く、後者は正確に。
- 数値の差し込みは ``{name}``。:func:`lfp.i18n.tr` の ``**kw`` で埋める。
- 単位は半角、数値との間に半角スペース（``10.329 Å`` / ``21.43 %``）。
- 学術用語は日本結晶学会の慣用表記に合わせる：
  格子定数 / 結晶系 / 点群 / 空間群 / ラウエ群 / ブラベー格子 /
  結晶子径 / 微小歪み / リートベルト精密化 / 当てはめ因子。
"""

from __future__ import annotations

TRANSLATIONS: dict[str, str] = {
    # ------------------------------------------------------------------ #
    # 共通
    # ------------------------------------------------------------------ #
    "app.title": "LiFePO4 相同定とリートベルト精密化",
    "btn.ok": "OK",
    "btn.cancel": "キャンセル",
    "btn.close": "閉じる",
    "btn.browse": "参照…",
    "state.on": "オン",
    "state.off": "オフ",

    # ------------------------------------------------------------------ #
    # メニュー
    # ------------------------------------------------------------------ #
    "menu.file": "ファイル(&F)",
    "menu.file.open": "XRD パターンを読み込み…",
    "menu.file.export_html": "解析レポートを書き出す（HTML）…",
    "menu.file.export_csv": "結果サマリを書き出す（CSV）…",
    "menu.file.export_pattern": "フィッティングパターンを書き出す（CSV）…",
    "menu.file.export_bragg": "ブラッグ反射表を書き出す（CSV）…",
    "menu.file.export_peaks": "ピーク探索結果を書き出す（CSV）…",
    "menu.file.export_png": "パターン画像を書き出す（PNG）…",
    "menu.file.exit": "終了",

    "menu.process": "パターン処理(&P)",
    "menu.process.smooth": "スムージング（Savitzky–Golay）…",
    "menu.process.background": "バックグラウンド除去…",
    "menu.process.ka2": "Kα2 除去…",
    "menu.process.peaks": "ピーク探索",
    "menu.process.reset": "元のパターンに戻す",
    "menu.process.export_peaks": "ピーク探索結果を書き出す（CSV）…",

    "menu.language": "言語(&L)",

    "menu.view": "表示(&V)",
    "menu.view.fit": "フィッティング結果を表示",
    "menu.view.spectrum": "処理後のパターンを表示",

    "menu.help": "ヘルプ(&H)",
    "menu.help.about": "PolyXRD LFP について",
    "menu.help.copyright": "著作権とライセンス",

    # ------------------------------------------------------------------ #
    # ツールバー
    # ------------------------------------------------------------------ #
    "toolbar.open": "読み込み",
    "toolbar.smooth": "スムージング",
    "toolbar.bg": "BG 除去",
    "toolbar.ka2": "Kα2 除去",
    "toolbar.peaks": "ピーク探索",
    "toolbar.reset": "元パターン",
    "toolbar.export": "書き出し",

    # ------------------------------------------------------------------ #
    # パネル見出し
    # ------------------------------------------------------------------ #
    "panel.sample": "試料と測定条件",
    "panel.conditions": "測定条件",
    "panel.structure": "構造モデル（CIF）",
    "panel.verdict": "LiFePO4 相同定",
    "panel.refine": "リートベルト精密化",
    "panel.result": "精密化結果",

    "sample.name": "試料名",
    "sample.placeholder": "任意。未入力ならファイル名を使用",

    # 測定条件（row.meta.* は SamplePanel が row.<key> で参照）
    "meta.file": "データファイル",
    "meta.anode": "対陰極",
    "meta.wavelength": "波長 λ",
    "meta.range": "2θ 範囲",
    "meta.step": "ステップ",
    "meta.points": "データ点数",
    "row.meta.file": "データファイル",
    "row.meta.anode": "対陰極",
    "row.meta.wavelength": "波長 λ",
    "row.meta.range": "2θ 範囲",
    "row.meta.step": "ステップ",
    "row.meta.points": "点数",

    # ------------------------------------------------------------------ #
    # 構造モデル
    # ------------------------------------------------------------------ #
    "struct.import": "CIF を読み込み…",
    "struct.builtin": "内蔵 · {name}",
    "struct.imported": "カスタム · {name}",
    "struct.atoms.value": "{asym} サイト / {sym} 操作 / {total} 原子",
    "struct.not_lfp_warn": (
        "この構造には Li–Fe–P–O の 4 元素が含まれず、リン酸鉄リチウムの"
        "モデルではありません。精密化結果は物理的意味を失います。"
        "LiFePO4 の CIF を読み込んでください。"),
    "row.struct.formula": "化学式",
    "row.struct.sg": "空間群",
    "row.struct.system": "結晶系",
    "row.struct.point": "点群",
    "row.struct.laue": "ラウエ群",
    "row.struct.bravais": "ブラベー格子",
    "row.struct.atoms": "非対称単位",

    # ------------------------------------------------------------------ #
    # 相同定
    # ------------------------------------------------------------------ #
    "ident.rerun": "再判定",
    "ident.running": "判定中…",
    "ident.top3.value": "{n} / 3 本",
    "ident.note": (
        "判定基準：実測ピークのうち LFP 参照ピークで説明できる強度の割合"
        "（カバレッジ）≥ 70 %、最強 3 本すべてが対応、未説明強度 ≤ 35 %。"
        "3 条件を同時に満たした場合のみ LiFePO4 と判定します。"),
    "ident.note.pass": (
        "すべての判定基準を満たしました。パターンは LiFePO4（Pnma）の"
        "参照ピークと一致しており、構造精密化を実行できます。"),
    "ident.note.partial": (
        "一部の判定基準を満たしていません。LiFePO4 と断定できないため、"
        "ソフトウェアの方針により精密化へ進みません。"
        "満たさなかった基準を下に示します。解決後に再判定してください。"),
    "ident.note.fail": (
        "判定基準を明らかに満たしていません。パターンは LiFePO4 の参照"
        "ピークと一致しないため、非 LiFePO4 と判定し精密化を中止しました。"),
    "row.ident.verdict": "判定",
    "row.ident.coverage": "カバレッジ",
    "row.ident.top3": "最強 3 本",
    "row.ident.unexplained": "未説明強度",
    "row.ident.shift": "ゼロ点シフト",
    "row.ident.resid": "ピーク位置残差",
    "row.ident.cell": "予備精密化 a / b / c",
    "ident.verdict.pass": "LiFePO4 である",
    "ident.verdict.partial": "第二相の可能性",
    "ident.verdict.fail": "LiFePO4 ではない",
    "ident.resid.value": "{rms:.3f}° （許容 {tol:.3f}°）",
    "ident.reason.head": "満たさなかった基準：",
    "ident.reason.coverage": "カバレッジ {cov:.1f} % < 70 %",
    "ident.reason.top3": "最強 3 本のうち {n} / 3 本のみ一致",
    "ident.reason.unexplained": "未説明強度 {unexp:.1f} % > 35 %",
    "ident.reason.model": (
        "ピーク位置残差 {rms:.3f}° が許容値 {tol:.3f}° の {ratio:.0%}"
        "（上限 45 %）に達しています：ピーク位置を「ゼロ点 + 等方膨張収縮」"
        "では説明できず、異方的な歪みまたは第二相の重なりが考えられます"),
    "dlg.notlfp.resid": "\n\nピーク位置残差 RMS = {rms:.4f}°（許容値の {ratio:.0%}）",
    "ident.note.gate": (
        "上記の基準はピークの有無と強度のみを数えるため、ピーク位置の"
        "系統的なずれには鈍感です。そこで別途ゲートを設けています："
        "ゼロ点と等方膨張収縮を差し引いた後のピーク位置残差が、位置許容値の"
        "45 % 未満であること。超える場合はこの 2 パラメータでは実測位置を"
        "説明できない（例：格子の異方歪み）ため、方針により精密化へ進みません。"),

    # ------------------------------------------------------------------ #
    # 精密化の進捗（カーネルの progress_cb がダイアログと状態欄に直接出る）
    # ------------------------------------------------------------------ #
    "stage.identify": "LiFePO4 かどうかを判定中…",
    "stage.progress": "精密化ステージ {i}/{n}：{label}",
    "stage.linear": "線形層（スケール + バックグラウンド）",
    "stage.shape": "ピーク形状（ゼロ点 + 結晶子径/歪み + 非対称）",
    "stage.cell": "格子定数（a / b / c）",
    "stage.full": "フルモデル",
    "stage.build": "精密化モデルを構築中…",
    "stage.eval": "{n} 回評価済み · 現在の Rwp = {rwp:.2f}%",
    "stage.final": "最終計算パターンを合成中…",
    "stage.rbragg": "R_Bragg を計算中…",
    "stage.done": "完了",

    # ------------------------------------------------------------------ #
    # 精密化パネル
    # ------------------------------------------------------------------ #
    "refine.bg": "バックグラウンド",
    "refine.bg.cheb": "Chebyshev 多項式",
    "refine.bg.tent": "線形補間（tent）",
    "refine.nbg": "項数",
    "refine.range": "2θ 範囲",
    "refine.run": "精密化を開始",
    "refine.cancel": "精密化を中止",

    "opt.cell": "格子定数 a / b / c",
    "opt.cell.tip": "斜方晶の 3 辺を同時に解放。判定段階の予備精密化値を初期値とします。",
    "opt.zero": "ゼロ点シフト",
    "opt.zero.tip": "試料変位・装置ゼロ点による 2θ の全体シフト（°）。",
    "opt.size": "結晶子径",
    "opt.size.tip": "Scherrer 径（Lorentzian 広がり）。単位 nm。",
    "opt.strain": "微小歪み",
    "opt.strain.tip": "Wilson の微小歪み（β = 4ε·tanθ）。無次元。",
    "opt.asym": "非対称",
    "opt.asym.tip": "低角ピークの非対称な裾（軸発散・試料透過）。",
    "opt.po": "配向性",
    "opt.po.tip": "March–Dollase の配向（020 方向）。加圧成型試料でよく見られます。",
    "opt.uvw": "装置広がり U V W",
    "opt.uvw.tip": "Caglioti の装置半値幅パラメータ。標準試料がある場合に解放します。",
    "opt.bfactor": "温度因子 B",
    "opt.bfactor.tip": "全体の等方 B 因子（Å²）。結晶子径と強く相関し発散しやすい。",

    # ------------------------------------------------------------------ #
    # 結果
    # ------------------------------------------------------------------ #
    "res.group.cell": "格子定数",
    "res.group.sym": "対称性",
    "res.group.micro": "微細構造",
    "res.group.fit": "当てはめ因子",
    "res.note": (
        "Rwp の絶対値は計数統計に強く依存します：高速・低計数のパターンは"
        "Rexp 自体が高く、Rwp を低くすることは不可能です。そこで "
        "GOF = Rwp/Rexp も併記します（1 付近が最良。1 未満は σ が過大な"
        "のであって当てはめが良いわけではありません）。R_B の目安：{rb_verdict}。"),
    "row.res.a": "a",
    "row.res.b": "b",
    "row.res.c": "c",
    "row.res.alpha": "α",
    "row.res.beta": "β",
    "row.res.gamma": "γ",
    "row.res.volume": "格子体積 V",
    "row.res.system": "結晶系",
    "row.res.sg": "空間群",
    "row.res.point": "点群",
    "row.res.laue": "ラウエ群",
    "row.res.bravais": "ブラベー格子",
    "row.res.size": "結晶子径 D",
    "row.res.strain": "微小歪み ε",
    "row.res.fwhm": "FWHM (35.6°)",
    "row.res.eta": "η (35.6°)",
    "row.res.rwp": "Rwp",
    "row.res.rp": "Rp",
    "row.res.rexp": "Rexp",
    "row.res.chi2": "χ²",
    "row.res.gof": "GOF",
    "row.res.rb": "R_Bragg",
    "row.res.verdict": "判定",

    "verdict.rwp.excellent": "優秀",
    "verdict.rwp.good": "良好",
    "verdict.rwp.consistent": "当てはめ十分",
    "verdict.rwp.acceptable": "許容範囲",
    "verdict.rwp.poor": "不良。モデルの確認を",
    "verdict.gof.good": "1 に近い",
    "verdict.gof.fair": "やや高い",
    "verdict.gof.poor": "明らかに高い",
    "verdict.gof.low": "1 未満（σ 過大）",
    "verdict.rb.good": "構造モデルは実測強度と良く一致",
    "verdict.rb.fair": "許容範囲。弱ピーク域はやや不正確の可能性",
    "verdict.rb.poor": "不良。構造モデルの再検討が必要",
    "verdict.rb.unknown": "未計算",

    # ------------------------------------------------------------------ #
    # キャンバス
    # ------------------------------------------------------------------ #
    "canvas.x_label": "2θ (°)",
    "canvas.y_label": "強度 (counts)",
    "canvas.y_diff": "差",
    "canvas.empty": "XRD パターンを読み込むとここに表示されます",
    "canvas.bragg": "ブラッグ位置",
    "canvas.legend.obs": "実測",
    "canvas.legend.calc": "計算",
    "canvas.legend.bg": "バックグラウンド",
    "canvas.legend.err": "実測 − 計算",
    "canvas.legend.peaks": "ピーク",

    # ------------------------------------------------------------------ #
    # ダイアログ
    # ------------------------------------------------------------------ #
    "dialog.about.title": "PolyXRD LFP について",
    "dialog.copyright.title": "著作権とライセンス",
    "about.features": (
        "リン酸鉄リチウム（LiFePO4、オリビン型、Pnma）正極材料の専用ツール："
        "パターンを読み込むとまず相同定を行い、LiFePO4 と確認できた場合のみ"
        "リートベルト全パターン精密化へ進みます。精密化では格子定数、"
        "結晶系／点群／空間群／ラウエ群、結晶子径と微小歪み、"
        "さらに Rwp / Rp / Rexp / χ² / GOF / R_Bragg などの当てはめ因子を"
        "出力します。"),
    "about.contact": "連絡先",
    "about.rights": "著作権",
    "copyright.head": "PolyXRD LFP · 著作権とライセンス",

    "dlg.smooth.title": "スムージング（Savitzky–Golay）",
    "dlg.smooth.window": "窓点数",
    "dlg.smooth.order": "多項式の次数",
    "dlg.smooth.hint": (
        "窓を大きくするほど滑らかになりますが、ピーク高さが下がり形状が"
        "広がります。次数が高いほど形状を保ちます。推奨：窓 9–21（奇数）、"
        "次数 2–4。スムージングは表示とピーク探索にのみ影響し、精密化は"
        "常に元のパターンを使用します。"),
    "dlg.bg.title": "バックグラウンド除去",
    "dlg.bg.method": "手法",
    "dlg.bg.iter": "SNIP 反復回数",
    "dlg.bg.order": "多項式の次数",
    "dlg.bg.hint": (
        "SNIP は階段状のバックグラウンドに適します（反復回数が多いほど"
        "低くなります）。多項式はなだらかなバックグラウンドに、端点線形は"
        "両端を結ぶだけです。除去結果は表示とピーク探索にのみ影響し、"
        "精密化ではモデルのバックグラウンドを使用します。"),
    "bg.snip": "SNIP クリッピング",
    "bg.poly": "多項式フィット",
    "bg.linear": "端点線形",
    "dlg.ka2.title": "Kα2 除去",
    "dlg.ka2.anode": "対陰極",
    "dlg.ka2.ratio": "I(Kα2)/I(Kα1)",
    "dlg.ka2.hint": (
        "Rachinger の逐次除去により、高角から低角へ Kα2 成分を差し引きます。"
        "Cu 靶では通常 0.50 です。除去後のパターンは表示とピーク探索にのみ"
        "使用し、精密化では Kα1/Kα2 二重線を前方向モデルで陽に扱います。"),
    "busy.title": "しばらくお待ちください",
    "busy.starting": "準備中…",
    "busy.canceling": "中止しています…",
    "dlg.notlfp.title": "判定結果：LiFePO4 ではない",
    "dlg.notlfp.text": "このパターンは LiFePO4 と判定されなかったため、精密化を中止しました。",
    "dlg.notlfp.info": (
        "カバレッジ {cov:.1f} %、最強 3 本の一致 {top} / 3、"
        "未説明強度 {unexp:.1f} %。"),
    "dlg.notlfp.detail": (
        "実測ピーク {n} 本；LFP 参照ピーク {refs} 本、一致 {matched} 本、"
        "一致許容 ±{tol:.3f}°；逆算ゼロ点シフト {dz:+.3f}°、"
        "歪みスケール {e:+.2f} %。"),

    # ------------------------------------------------------------------ #
    # ファイルダイアログ
    # ------------------------------------------------------------------ #
    "filter.pattern": "XRD パターン (*.txt *.xy *.xye *.dat *.csv *.asc *.prn);;すべてのファイル (*)",
    "filter.cif": "CIF 構造ファイル (*.cif);;すべてのファイル (*)",
    "filter.html": "HTML レポート (*.html)",
    "filter.csv": "CSV テーブル (*.csv)",
    "filter.png": "PNG 画像 (*.png)",
    "dlg.open.title": "XRD パターンを読み込み",
    "dlg.save.report": "解析レポートを保存",
    "dlg.save.csv": "CSV を保存",
    "dlg.save.png": "パターン画像を保存",
    "dlg.import_cif.title": "CIF 構造ファイルを読み込み",

    # ------------------------------------------------------------------ #
    # 状態欄とメッセージ
    # ------------------------------------------------------------------ #
    "status.ready": "準備完了 · XRD パターンを読み込んでください",
    "status.loading": "パターンを読み込み中…",
    "status.loaded": "{name} を読み込みました（{n} 点、{lo:.2f}–{hi:.2f}°）",
    "status.identifying": "LiFePO4 かどうかを判定中…",
    "status.non_lfp": "非 LiFePO4 と判定したため、以降の処理を中止しました",
    "status.lfp": "LiFePO4 と判定されました。構造精密化を実行できます",
    "status.refining": "精密化中…",
    "status.refined": "精密化完了：Rwp = {rwp:.2f} %、GOF = {gof:.3f}、{sec:.1f} s",
    "status.canceled": "中止しました",
    "status.processed": "適用しました：{what}",
    "status.reset": "元のパターンに戻しました",
    "status.exported": "{path} を書き出しました",
    "status.struct_loaded": "構造モデルを読み込みました：{name}",

    "err.open.title": "パターンを読み込めません",
    "err.open.text": "ファイルの読み込みに失敗しました：\n{msg}",
    "err.open.hint": (
        "2 列テキスト（2θ 強度）または 3 列（2θ 強度 重み/σ）に対応しています。"
        "装置固有のバイナリ形式の場合は、まずテキストに書き出してください。"),
    "err.cif.title": "CIF を読み込めません",
    "err.cif.text": "CIF の解析に失敗しました：\n{msg}",
    "err.refine.title": "精密化に失敗しました",
    "err.refine.text": "精密化中に例外が発生しました：\n{msg}",
    "err.no_data.title": "データがありません",
    "err.no_data.text": "先に XRD パターンを読み込んでください。",
    "err.no_result.text": "結果を書き出す前に精密化を完了してください。",
    "err.peaks_empty": "有意なピークが検出されませんでした（閾値を下げるか、先にスムージングしてください）。",
    "confirm.cancel_refine": "精密化を中止しました。",

    # ------------------------------------------------------------------ #
    # レポート
    # ------------------------------------------------------------------ #
    "report.title": "リン酸鉄リチウム XRD 相同定・リートベルト精密化レポート",
    "report.generated": "作成日時 {ts}",
    "report.sample": "試料とデータ",
    "report.sample_name": "試料名",
    "report.file": "データファイル",
    "report.identify": "相同定",
    "report.cell": "格子定数と対称性",
    "report.micro": "微細構造",
    "report.fit": "当てはめ因子",
    "report.params": "精密化パラメータ",
    "report.figure": "実測 / 計算 / 差 の図",
    "report.bragg": "ブラッグ反射（計算強度の上位 40 本）",
    "report.col.2th": "2θ (°)",
    "report.col.hkl": "h k l",
    "report.col.icalc": "I_calc",
    "report.col.iobs": "I_obs",
    "report.rwp_note": (
        "Rwp は計数統計と強く相関します：高速・低計数のパターンは Rexp 自体が"
        "高いため、Rwp を低くすることはできません。GOF = Rwp/Rexp と併せて"
        "判断してください（1 付近が最良）。"),
    "report.limit": (
        "方法の注記：本レポートは単相リートベルト全パターン精密化の結果です。"
        "ピーク形状は pseudo-Voigt（Thompson–Cox–Hastings 合成）、結晶子径は "
        "Scherrer の式（K = 0.9）、微小歪みは Wilson の式によります。"
        "装置広がりは差し引いていません。R_Bragg は profile-partitioned の"
        "定義で、重なりピークは計算形状の振幅で実測強度を配分し、"
        "モデル化していない第二相は計上しないため、重なりの強い試料では "
        "R_B が低めになります。構造と対称性の情報は内蔵 CIF"
        "（Yamada et al., J. Electrochem. Soc. 148 (2001) A224）に拠ります。"
        "炭素被覆層や非晶質相の散乱はバックグラウンドにのみ入り、"
        "構造因子の計算には含まれません。"),
    "report.footer": "本レポートは PolyXRD LFP が自動生成したものです。数値は同名の CSV 書き出しと一致します。",

    # ------------------------------------------------------------------ #
    # 版と登録
    # ------------------------------------------------------------------ #
    "about.edition": "版",
    "about.edition.internal": "社内評価版",
    "about.edition.registered": "登録版",
    "about.registered_to": "登録機関：{unit}",
    "about.unregistered": "未登録（試用可。商用には登録が必要）",
    "status.registered": "登録しました：{unit}",

    # ------------------------------------------------------------------ #
    # CSV 列名
    # ------------------------------------------------------------------ #
    "csv.col.item": "項目",
    "csv.col.value": "値",
    "csv.col.2th": "2θ(°)",
    "csv.col.obs": "実測",
    "csv.col.calc": "計算",
    "csv.col.diff": "差",
    "csv.col.bg": "バックグラウンド",
    "csv.col.hkl": "hkl",
    "csv.col.iobs": "I_obs",
    "csv.col.icalc": "I_calc",
    "csv.col.height": "正味ピーク高",
    "csv.col.fwhm": "FWHM(°)",
    "csv.col.eta": "η",
    "csv.col.area": "正味面積",
    "csv.col.snr": "SNR",
    "csv.col.r2": "フィット R²",
    "csv.sample": "試料名",
    "csv.file": "データファイル",
    "csv.anode": "対陰極",
    "csv.wavelength": "波長(Å)",
    "csv.range": "2θ範囲(°)",
    "csv.step": "ステップ(°)",
    "csv.ident": "相同定",
    "csv.coverage": "カバレッジ",
    "csv.unexplained": "未説明強度",
    "csv.resid": "ピーク位置残差RMS(°)",
    "csv.resid_ratio": "残差/許容値",
    "csv.reason": "満たさなかった基準",
    "csv.a": "a(Å)",
    "csv.b": "b(Å)",
    "csv.c": "c(Å)",
    "csv.alpha": "α(°)",
    "csv.beta": "β(°)",
    "csv.gamma": "γ(°)",
    "csv.volume": "V(Å³)",
    "csv.system": "結晶系",
    "csv.spacegroup": "空間群",
    "csv.sg_number": "空間群番号",
    "csv.pointgroup": "点群",
    "csv.laue": "ラウエ群",
    "csv.bravais": "ブラベー格子",
    "csv.size": "結晶子径(nm)",
    "csv.strain": "微小歪み(%)",
    "csv.zero": "ゼロ点シフト(°)",
    "csv.rwp": "Rwp(%)",
    "csv.rp": "Rp(%)",
    "csv.rexp": "Rexp(%)",
    "csv.chi2": "chi2",
    "csv.gof": "GOF",
    "csv.rb": "R_Bragg(%)",
    "csv.nparams": "パラメータ数",
    "csv.points": "データ点数",
    "csv.elapsed": "所要時間(s)",
}
