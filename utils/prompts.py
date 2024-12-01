# utils/prompts.py
"""
このモジュールは、臨床試験データの検索と分析に使用される各種プロンプトテンプレートを定義します。
APIクエリの生成から、試験データの分析、要約生成まで、様々な目的に特化したプロンプトを提供します。

主なコンポーネント：
- API仕様のドキュメント
- システムプロンプト
- 各種分析用プロンプトテンプレート
"""

# APIの仕様を定義するドキュメント
# クエリパラメータ、フィルター、ソートオプションなどの詳細な説明を含む
API_DOCUMENT = '''
### Query Parameters:
- **query.cond**: "Conditions or disease" query in Essie expression syntax. Searches in the `ConditionSearch` area.
  *例*: `lung cancer`、`(head OR neck) AND pain`
- **query.term**: "Other terms" query in Essie expression syntax. Searches in the `BasicSearch` area.
  *例*: `AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]`
- **query.locn**: "Location terms" query in Essie expression syntax. Searches in the `LocationSearch` area.
- **query.titles**: "Title / acronym" query in Essie expression syntax. Searches in the `TitleSearch` area.
- **query.intr**: "Intervention / treatment" query in Essie expression syntax. Searches in the `InterventionSearch` area.
- **query.outc**: "Outcome measure" query in Essie expression syntax. Searches in the `OutcomeSearch` area.
- **query.spons**: "Sponsor / collaborator" query in Essie expression syntax. Searches in the `SponsorSearch` area.
- **query.lead**: Searches in the `LeadSponsorName` field.
- **query.id**: "Study IDs" query in Essie expression syntax. Searches in the `IdSearch` area.
- **query.patient**: Searches in the `PatientSearch` area.

### Filter Parameters:
- **filter.overallStatus**: filter.overallStatus values must be encoded as comma-separated list.
  *Allowed values*:
  ACTIVE_NOT_RECRUITING
COMPLETED
ENROLLING_BY_INVITATION
NOT_YET_RECRUITING
RECRUITING
SUSPENDED
TERMINATED
WITHDRAWN
AVAILABLE
NO_LONGER_AVAILABLE
TEMPORARILY_NOT_AVAILABLE
APPROVED_FOR_MARKETING
WITHHELD
UNKNOWN

*Examples*:
- `[ NOT_YET_RECRUITING, RECRUITING ]`
- `[ COMPLETED ]`
- **filter.geo**: Filter by geographic location using the `distance` function.
*Format*: `distance(latitude,longitude,distance)`
*Examples*:
- `distance(39.0035707,-77.1013313,50mi)`
- **filter.ids**: Filter by a list of NCT IDs.
*Examples*:
- `[ NCT04852770, NCT01728545, NCT02109302 ]`
- **filter.advanced**: Filter by a query in Essie expression syntax.
*Examples*:
- `AREA[StartDate]2022`
- `AREA[MinimumAge]RANGE[MIN, 16 years] AND AREA[MaximumAge]RANGE[16 years, MAX]`
- **filter.synonyms**: Filter by a list of area:synonym_id pairs.
*Examples*:
- `[ ConditionSearch:1651367, BasicSearch:2013558 ]`
### Sort Parameters:
- **sort**: Comma- or pipe-separated list of sorting options.
*Examples*:
- `[ @relevance ]`
- `[ LastUpdatePostDate ]`
- `[ EnrollmentCount:desc, NumArmGroups ]`
**Note**: Sorting by `@relevance`, date fields, or numeric fields is supported. Default sort direction is descending for date fields and `@relevance`, ascending for numeric fields.
### Other Parameters:
- **format**: Response format.
*Allowed values*: `json`, `csv`
*Default*: `json`
- **markupFormat**: Format of markup type fields (applicable only to `json` format).
*Allowed values*: `markdown`, `legacy`
*Default*: `markdown`
- **fields**: List of fields to include in the response.
*Examples*:
- `[ NCTId, BriefTitle, OverallStatus, HasResults ]`
- `[ ProtocolSection ]`
- **countTotal**: Whether to include the total count of studies.
*Allowed values*: `true`, `false`
*Default*: `false`
- **pageSize**: Number of studies per page.
*Default*: `10`
*Maximum*: `1000`
*Examples*: `2`, `100`
- **pageToken**: Token to get the next page. Use the `nextPageToken` value returned in the previous response.
### Important Notes:
- **filter.lastUpdatePostDate** is not a valid parameter in the updated API. Instead, you should use **filter.advanced** with the appropriate Essie expression.
*For example*, to filter by last update post date:
```plaintext
filter.advanced: AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]
The Essie expression syntax allows for advanced querying and filtering within specified areas.
'''

# システムプロンプト：APIクエリ生成の基本設定
# ライフサイエンス分野の専門家としての役割と出力形式を定義
SYSTEM_PROMPT = f"""あなたはライフサイエンス分野の学術的なプロフェッショナルです。
APIリクエストのクエリを<output_example>を参考にJSON形式で出力してください。JSON形式で用いるので、不要な情報は述べないでください。
<api-document>
{API_DOCUMENT}
</api-document>

<output_example>
{{
  "query.cond": "(type 2 diabetes)",
  "query.intr": "(DPP4 inhibitor) AND (SGLT2 inhibitor)",
  "filter.overallStatus": "COMPLETED",
  "filter.advanced": "AREA[CompletionDate]RANGE[1/1/2017, 1/1/2024] AND AREA[Phase]PHASE3",
  "sort": ["LastUpdatePostDate:desc"]
}}
</output_example>
"""

# 臨床試験検索用のプロンプトテンプレート
# PICO形式（Patient, Intervention, Comparison, Outcome）に基づく検索条件の定義
USER_PROMPT_TEMPLATE = """
# 臨床試験検索条件

以下の臨床学的な問いに関連する臨床試験を探しています。

## 検索パラメータ
各XMLタグの意味は以下の通りです：

- `<patient>`: 対象となる患者の特徴(英語)
- `<intervention>`: 実施する治療や投与の内容(英語)
- `<comparison>`: 比較対象(英語)
- `<outcome>`: 評価する結果や指標(英語)
- `<additional_condition>`: その他の条件（日付範囲は除く）

## 検索条件
<patient>{p}</patient>
<intervention>{i}</intervention>
<comparison>{c}</comparison>
<outcome>{o}</outcome>
<additional_condition>{additional}</additional_condition>

## 重要な注意事項
* ユーザーが日本語で入力しても、あなたは英語でクエリを生成してください
* 2種の医薬品の結果を比較するような臨床試験を検索する場合は、`Intervention`に両方の医薬品を含めてください
* `fields`パラメータは使用しません
* クエリ文字列内のスペースはエスケープ不要です
* 日付範囲は別途システムで制御するため、ここでは指定しないでください
"""


# 臨床試験データの要約生成用プロンプト
# 試験の主要な特徴（対象患者、介入、評価項目など）をまとめる
SUMMARY_PROMPT_TEMPLATE = """
# 臨床試験データの要約分析
対象試験数: {num_studies}件

## 試験の基本情報
### 対象患者
{p}

### 主な介入方法
*上位5件*
{interventions}

### 主な適格基準
*上位5件*
{eligibility}

## 評価項目
### 主要評価項目
*上位5件*
{primary_outcomes}

### 副次評価項目
*上位5件*
{secondary_outcomes}

## 分析指示
これらの情報を基に、臨床試験の全体的な傾向について以下の観点から要約を作成してください：
1. 対象患者の特徴
2. 実施された介入の特徴
3. 主な評価指標の傾向

**要件**:
- 言語: 日本語
- 長さ: 3-4文程度
- 焦点: 患者、介入、評価の関連性
"""

# 複数の臨床試験の横断的分析用プロンプト
# 共通点や傾向を分析するための指示を含む
CROSS_STUDY_PROMPT = """
以下の臨床試験の要約を分析し、以下の点について横断的な分析を行ってください：
1. 共通の介入方法
2. 主要評価項目の傾向
3. 試験デザインの特徴
4. 対象患者の特徴

{summaries}

回答は箇条書きで、日本語でお願いします。
"""

# 適格基準の分析用プロンプト
# 包含/除外基準の傾向を分析
CRITERIA_PROMPT = """
以下の適格基準を分析し、以下の点について要約してください：
1. 最も一般的な包含基準
2. 最も一般的な除外基準
3. 特徴的または珍しい基準
4. 年齢や性別に関する傾向

適格基準:
{criteria}

回答は箇条書きで、日本語でお願いします。
"""

# 関連文献の分析用プロンプト
# 研究成果や臨床的意義の要約
PUBLICATION_PROMPT = """
以下の臨床試験関連文献を要約し、以下の点について分析してください：
1. 主な研究テーマ
2. 重要な結果や発見
3. 臨床的意義

{summaries}

回答は箇条書きで、日本語でお願いします。
"""

# 臨床試験の比較分析用プロンプト
# 試験間の類似点と相違点を分析
COMPARISON_PROMPT = """
以下の臨床試験を比較分析し、以下の点について要約してください：
1. 試験デザインの類似点と相違点
2. 介入方法の比較
3. 評価項目の違い
4. 対象患者の選択基準の違い
5. 各試験の強みと弱み

{comparison_data}

回答は箇条書きで、日本語でお願いします。
"""

# 新規プロトコル生成用プロンプト
# 既存データを基に新しい試験プロトコルを作成
PROTOCOL_PROMPT = """
以下の情報を基に、新しい臨床試験のプロトコルドラフトを生成してください：

対象疾患: {target_condition}
介入方法: {intervention}
主要評価項目: {primary_outcome}

既存の臨床試験データ:
{existing_studies}

プロトコルドラフトには以下の項目を含めてください：
1. 試験の背景と目的
2. 試験デザイン
3. 対象患者の選択基準（包含基準と除外基準）
4. 介入方法の詳細
5. 評価項目（主要評価項目と副次評価項目）
6. 統計学的考慮事項

回答は日本語で、各項目を簡潔にまとめてください。
"""

COMPREHENSIVE_SUMMARY_PROMPT = """
# 臨床試験データの総合分析
対象試験数: {num_studies}件

## 分析データ
### 対象患者
{p}

### 主な介入方法（上位5件）
{interventions}

### 主要評価項目（上位5件）
{primary_outcomes}

### 副次評価項目（上位5件）
{secondary_outcomes}

### 適格基準の特徴
【統計情報】
{criteria_analysis}

## 分析指示
上記の情報を統合し、以下の観点から包括的な要約を作成してください：
1. 試験デザインの全体的な特徴
2. 対象患者と適格基準の関係性
   - 特に年齢・性別の分布傾向
   - 適格基準の例から見られる特徴的な包含/除外基準
3. 介入方法と評価項目の整合性
4. 特筆すべき傾向や特徴

要件:
- 日本語で記述
- 前半は構造的に記述する。その後、最後に文章形式で一連の分析を述べる。
- わかりやすく。ただし長くなりすぎないように。
- 各要素の関連性に注目
- 適格基準の例から具体的な特徴を抽出
"""