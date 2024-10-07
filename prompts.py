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

USER_PROMPT_TEMPLATE = """以下のような臨床学的な問いに関連する臨床試験を探しています
なおそれぞれのタグの意味は以下の通りです
<patient>にはどのような患者を対象としているかを示しています
<intervention>にはどのような投与などを治療をした際に、という条件が示されています
<comparison>には何と比較した結果を調べるか、を示しています
<outcome>にはどのような結果になるか、を示しています
<patient>{p}</patient>
<intervention>{i}</intervention>
<comparison>{c}</comparison>
<outcome>{o}</outcome>
<additional_condition>{additional}</additional_condition>
<tips>
- 2種の医薬品の結果を比較するような臨床試験を検索する場合は、Interventionの項目に2種の医薬品を入れた条件で検索する必要があります
- "fields"を利用する必要はありません
- クエリ文字列でスペースをバックスラッシュなどでエスケープする必要はありません
</tips>"""

SUMMARY_PROMPT_TEMPLATE = """
以下は{num_studies}件の臨床試験データの要約です：

対象患者: {p}

主な介入 (上位5件):
{interventions}

主な適格基準 (上位5件):
{eligibility}

主要評価項目 (上位5件):
{primary_outcomes}

副次評価項目 (上位5件):
{secondary_outcomes}

これらの情報を基に、臨床試験の全体的な傾向を簡潔に要約してください。
特に、どのような患者を対象に、どのような介入を行い、主にどのような結果を評価しているかをまとめてください。
回答は日本語で、3-4文程度でお願いします。
"""

CROSS_STUDY_PROMPT = """
以下の臨床試験の要約を分析し、以下の点について横断的な分析を行ってください：
1. 共通の介入方法
2. 主要評価項目の傾向
3. 試験デザインの特徴
4. 対象患者の特徴

{summaries}

回答は箇条書きで、日本語でお願いします。
"""

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

PUBLICATION_PROMPT = """
以下の臨床試験関連文献を要約し、以下の点について分析してください：
1. 主な研究テーマ
2. 重要な結果や発見
3. 臨床的意義

{summaries}

回答は箇条書きで、日本語でお願いします。
"""

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