import streamlit as st
import os
import json
import boto3
import requests
import re
import matplotlib.pyplot as plt
from collections import Counter
import pandas as pd
from datetime import datetime
import urllib.parse

from langchain_community.chat_models import BedrockChat

# AWSの認証情報を環境変数から取得
os.environ['AWS_ACCESS_KEY_ID'] = st.secrets["AWS_ACCESS_KEY_ID"]
os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets["AWS_SECRET_ACCESS_KEY"]
os.environ['AWS_DEFAULT_REGION'] = st.secrets["AWS_DEFAULT_REGION"]

# Bedrockクライアントの設定
bedrock = boto3.client('bedrock-runtime')

# BedrockChatモデルの初期化
llm = BedrockChat(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", client=bedrock)

# Streamlit app starts here
st.title("Clinical Trials Search and Analysis App")

st.write("このアプリでは、PICO形式で入力された情報に基づいてclinicaltrials.govから臨床試験を検索し、結果を要約・可視化します。")

# APIドキュメント（clinicaltrials.gov公式）
api_document = '''
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

# システムプロンプトの設定
system_prompt = f"""あなたはライフサイエンス分野の学術的なプロフェッショナルです。
APIリクエストのクエリを<output_example>を参考にJSON形式で出力してください。JSON形式で用いるので、不要な情報は述べないでください。
<api-document>
{api_document}
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

# StreamlitでのPICO入力フォーム
st.header("PICO情報の入力")

with st.form(key='pico_form'):
    p = st.text_input("Patient (対象患者):")
    i = st.text_input("Intervention (介入):")
    c = st.text_input("Comparison (比較対象):")
    o = st.text_input("Outcome (結果):")
    additional = st.text_input("Additional conditions (追加条件):")
    submit_button = st.form_submit_button(label='検索')

if submit_button:
    # ユーザー入力をもとに指示を生成
    user_prompt = f"""以下のような臨床学的な問いに関連する臨床試験を探しています
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

    # LLMにプロンプトを入力し、クエリを生成
    with st.spinner("クエリを生成中..."):
        response = llm.invoke(system_prompt + "\n" + user_prompt)

    # 生成されたクエリを表示
    st.subheader("生成されたクエリ:")
    st.code(response.content, language='json')

    # JSONとして解析できるか確認
    try:
        query = json.loads(response.content)
        st.success("クエリのパースに成功しました。")
    except json.JSONDecodeError:
        st.error("生成されたクエリが正しいJSON形式ではありません。")
        st.stop()

    # クエリパラメータをURLエンコード
    query_params = {}
    for key, value in query.items():
        if isinstance(value, list):
            query_params[key] = value
        else:
            query_params[key] = [value]

    encoded_params = urllib.parse.urlencode(query_params, doseq=True)

    # clinicaltrials.govの検索URLを作成
    search_url = f"https://clinicaltrials.gov/ct2/results?{encoded_params}"

    # ボタンを作成
    if st.button('clinicaltrials.govで検索'):
        st.markdown(f"[生成されたクエリでclinicaltrials.govを検索する]({search_url})", unsafe_allow_html=True)

    # APIエンドポイント
    api_url = "https://clinicaltrials.gov/api/v2/studies"

    # リクエストパラメータの設定
    params = {
        'format': 'json',
        'pageSize': 100,  # 1ページあたりの結果数
        'countTotal': 'true',  # 総結果数を取得
    }

    # クエリパラメータを追加
    for key, value in query.items():
        if isinstance(value, list):
            params[key] = ','.join(value)
        else:
            params[key] = value

    # デバッグ用にリクエストパラメータを表示（オプション）
    st.write("Request Parameters:")
    st.write(params)

    def fetch_studies(params):
        all_studies = []
        total_count = 0

        while True:
            response = requests.get(api_url, params=params)

            if response.status_code != 200:
                st.error(f"Error: {response.status_code}")
                st.write(response.text)
                break

            data = response.json()

            if 'studies' in data:
                all_studies.extend(data['studies'])

            if 'totalCount' in data:
                total_count = data['totalCount']

            if 'nextPageToken' in data:
                params['pageToken'] = data['nextPageToken']
            else:
                break  # 最後のページに到達

        return all_studies, total_count

    # 臨床試験データの取得
    with st.spinner("臨床試験データを取得中..."):
        studies, total_count = fetch_studies(params)

    # 結果の表示
    st.subheader(f"Total studies found: {total_count}")
    st.write(f"Studies retrieved: {len(studies)}")

    # 臨床試験データの構造化
    def clean_html(raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def parse_date(date_string):
        if date_string:
            try:
                return datetime.strptime(date_string, "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                return date_string
        return None

    def structure_clinical_trial(study):
        if not isinstance(study, dict):
            print(f"Warning: Unexpected study data type: {type(study)}")
            return None

        protocol_section = study.get('protocolSection', {})
        derived_section = study.get('derivedSection', {})

        if not isinstance(protocol_section, dict) or not isinstance(derived_section, dict):
            print(f"Warning: Unexpected data structure in study")
            return None

        structured_data = {
            "nct_id": protocol_section.get('identificationModule', {}).get('nctId'),
            "title": protocol_section.get('identificationModule', {}).get('officialTitle'),
            "brief_summary": clean_html(protocol_section.get('descriptionModule', {}).get('briefSummary', '')),
            "detailed_description": clean_html(protocol_section.get('descriptionModule', {}).get('detailedDescription', '')),
            "status": protocol_section.get('statusModule', {}).get('overallStatus'),
            "start_date": parse_date(protocol_section.get('statusModule', {}).get('startDateStruct', {}).get('date')),
            "end_date": parse_date(protocol_section.get('statusModule', {}).get('completionDateStruct', {}).get('date')),
            "eligibility": {
                "inclusion_criteria": protocol_section.get('eligibilityModule', {}).get('inclusionCriteria', '').split('\n'),
                "exclusion_criteria": protocol_section.get('eligibilityModule', {}).get('exclusionCriteria', '').split('\n')
            },
            "interventions": [
                {
                    "type": intervention.get('type'),
                    "name": intervention.get('name'),
                    "description": intervention.get('description')
                }
                for intervention in protocol_section.get('armsInterventionsModule', {}).get('interventions', [])
            ],
            "outcomes": {
                "primary": [
                    outcome.get('measure')
                    for outcome in protocol_section.get('outcomesModule', {}).get('primaryOutcomes', [])
                ],
                "secondary": [
                    outcome.get('measure')
                    for outcome in protocol_section.get('outcomesModule', {}).get('secondaryOutcomes', [])
                ]
            },
            "sponsor": {
                "name": protocol_section.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name'),
                "type": protocol_section.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('class')
            },
            "locations": [],
            "publications": [
                {
                    "title": reference.get('title'),
                    "citation": reference.get('citation'),
                    "pmid": reference.get('pmid')
                }
                for reference in derived_section.get('publicationModule', {}).get('references', [])
            ]
        }

        locations_module = protocol_section.get('contactsLocationsModule', {})
        locations = locations_module.get('locations', [])

        if isinstance(locations, list):
            structured_data["locations"] = [
                {
                    "facility": location.get('facility', {}).get('name') if isinstance(location.get('facility'), dict) else location.get('facility'),
                    "city": location.get('facility', {}).get('city') if isinstance(location.get('facility'), dict) else None,
                    "country": location.get('facility', {}).get('country') if isinstance(location.get('facility'), dict) else None
                }
                for location in locations if isinstance(location, dict)
            ]
        elif isinstance(locations, str):
            structured_data["locations"] = [{"facility": locations, "city": None, "country": None}]

        return structured_data

    with st.spinner("データを構造化中..."):
        # 臨床試験データの構造化
        structured_studies = [structure_clinical_trial(study) for study in studies if study is not None]
        structured_studies = [study for study in structured_studies if study is not None]

    st.success(f"Structured data for {len(structured_studies)} studies has been prepared.")

    # データフレームへの変換
    df = pd.DataFrame(structured_studies)

    # データフレームの表示
    st.subheader("構造化データの表示")
    st.dataframe(df)

    # データのダウンロード
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(df)

    st.download_button(
        label="CSVとしてダウンロード",
        data=csv,
        file_name='structured_clinical_trials.csv',
        mime='text/csv',
    )

    # 検索結果の表示
    st.header("検索結果一覧")

    # 試験のタイトルとNCT IDを表示
    study_options = [f"{study['nct_id']}: {study['title']}" for study in structured_studies if study['title']]
    selected_studies = st.multiselect("詳細を確認したい試験を選択してください:", study_options)

    # 選択された試験の詳細表示
    for study_option in selected_studies:
        nct_id = study_option.split(":")[0]
        study = next((s for s in structured_studies if s['nct_id'] == nct_id), None)
        if study:
            st.subheader(f"{study['nct_id']}: {study['title']}")
            st.write(f"**ステータス:** {study['status']}")
            st.write(f"**開始日:** {study['start_date']}")
            st.write(f"**終了日:** {study['end_date']}")
            st.write("**概要:**")
            st.write(study['brief_summary'])
            st.write("**介入内容:**")
            st.write(', '.join([intervention['name'] for intervention in study['interventions']]))
            st.write("**主要評価項目:**")
            st.write(', '.join(study['outcomes']['primary']))
            st.write("**副次評価項目:**")
            st.write(', '.join(study['outcomes']['secondary']))
            st.write("---")

    # 選択された試験の横断的な要約
    if selected_studies:
        selected_study_data = [study for study in structured_studies if f"{study['nct_id']}: {study['title']}" in selected_studies]
        summary_prompt = f"""
以下の臨床試験の情報を基に、共通点や相違点を要約してください。

"""
        for study in selected_study_data:
            summary_prompt += f"""
### 試験ID: {study['nct_id']}
- タイトル: {study['title']}
- ステータス: {study['status']}
- 開始日: {study['start_date']}
- 終了日: {study['end_date']}
- 介入内容: {', '.join([intervention['name'] for intervention in study['interventions']])}
- 主要評価項目: {', '.join(study['outcomes']['primary'])}
- 副次評価項目: {', '.join(study['outcomes']['secondary'])}

"""

        summary_prompt += "これらの試験の共通点と相違点をまとめてください。回答は日本語でお願いします。"

        with st.spinner("選択された試験の横断的な要約を生成中..."):
            response = llm.invoke(summary_prompt)
            cross_study_summary = response.content

        st.subheader("選択された試験の横断的な要約")
        st.write(cross_study_summary)

    # データの分析と可視化
    st.header("結果の要約と可視化")

    num_studies = len(structured_studies)

    # 介入、適格基準、アウトカムの集計
    interventions = []
    eligibility_criteria = []
    outcomes = {'primary': [], 'secondary': []}

    for study in structured_studies:
        for intervention in study['interventions']:
            interventions.append(intervention['name'])
        eligibility_criteria.extend(study['eligibility']['inclusion_criteria'])
        eligibility_criteria.extend(study['eligibility']['exclusion_criteria'])
        outcomes['primary'].extend(study['outcomes']['primary'])
        outcomes['secondary'].extend(study['outcomes']['secondary'])

    # 集計
    intervention_counter = Counter(interventions)
    eligibility_counter = Counter(eligibility_criteria)
    primary_outcome_counter = Counter(outcomes['primary'])
    secondary_outcome_counter = Counter(outcomes['secondary'])

    # 上位5項目を抽出
    top_interventions = intervention_counter.most_common(5)
    top_eligibility = eligibility_counter.most_common(5)
    top_primary_outcomes = primary_outcome_counter.most_common(5)
    top_secondary_outcomes = secondary_outcome_counter.most_common(5)

    # LLMを使用して要約文を生成するためのプロンプト
    summary_prompt = f"""
以下は{num_studies}件の臨床試験データの要約です：

対象患者: {p}

主な介入 (上位5件):
{', '.join([f"{i[0]} ({i[1]}件)" for i in top_interventions])}

主な適格基準 (上位5件):
{', '.join([f"{e[0]} ({e[1]}件)" for e in top_eligibility])}

主要評価項目 (上位5件):
{', '.join([f"{o[0]} ({o[1]}件)" for o in top_primary_outcomes])}

副次評価項目 (上位5件):
{', '.join([f"{o[0]} ({o[1]}件)" for o in top_secondary_outcomes])}

これらの情報を基に、臨床試験の全体的な傾向を簡潔に要約してください。
特に、どのような患者を対象に、どのような介入を行い、主にどのような結果を評価しているかをまとめてください。
回答は日本語で、3-4文程度でお願いします。
"""

    with st.spinner("結果を要約中..."):
        response = llm.invoke(summary_prompt)
        summary = response.content

    # 評価対象医薬品の集計用データフレーム作成
    drug_df = pd.DataFrame(top_interventions, columns=['Drug', 'Count']).sort_values('Count', ascending=False)

    # 主要評価項目の集計用データフレーム作成
    outcome_df = pd.DataFrame(top_primary_outcomes, columns=['Outcome', 'Count']).sort_values('Count', ascending=False)

    # 可視化
    st.subheader("評価対象医薬品の分布")
    fig1, ax1 = plt.subplots()
    ax1.pie(drug_df['Count'], labels=drug_df['Drug'], autopct='%1.1f%%')
    ax1.axis('equal')
    st.pyplot(fig1)

    st.subheader("主要評価項目の分布")
    fig2, ax2 = plt.subplots()
    ax2.pie(outcome_df['Count'], labels=outcome_df['Outcome'], autopct='%1.1f%%')
    ax2.axis('equal')
    st.pyplot(fig2)

    # 結果の出力
    st.subheader("全体の要約")
    st.write(summary)

    st.subheader("Top 5 Evaluated Drugs:")
    st.table(drug_df)

    st.subheader("Top 5 Primary Outcomes:")
    st.table(outcome_df)

    # 先行研究の横断的分析
st.header("先行研究の横断的分析")

if structured_studies:
    study_summaries = []
    for study in structured_studies[:5]:  # 最初の5つの研究を分析
        summary = f"""
        NCT ID: {study['nct_id']}
        タイトル: {study['title']}
        状態: {study['status']}
        介入: {', '.join([i['name'] for i in study['interventions']])}
        主要評価項目: {', '.join(study['outcomes']['primary'])}
        """
        study_summaries.append(summary)

    cross_study_prompt = f"""
    以下の臨床試験の要約を分析し、以下の点について横断的な分析を行ってください：
    1. 共通の介入方法
    2. 主要評価項目の傾向
    3. 試験デザインの特徴
    4. 対象患者の特徴

    {' '.join(study_summaries)}

    回答は箇条書きで、日本語でお願いします。
    """

    with st.spinner("先行研究の横断的分析を生成中..."):
        response = llm.invoke(cross_study_prompt)
        cross_study_analysis = response.content

    st.write(cross_study_analysis)

# Inclusion/Exclusion基準の詳細分析
st.header("Inclusion/Exclusion基準の詳細分析")

if structured_studies:
    inclusion_criteria = []
    exclusion_criteria = []
    for study in structured_studies:
        inclusion_criteria.extend(study['eligibility']['inclusion_criteria'])
        exclusion_criteria.extend(study['eligibility']['exclusion_criteria'])

    criteria_prompt = f"""
    以下の包含基準と除外基準を分析し、以下の点について要約してください：
    1. 最も一般的な包含基準
    2. 最も一般的な除外基準
    3. 特徴的または珍しい基準
    4. 年齢や性別に関する傾向

    包含基準:
    {' '.join(inclusion_criteria)}

    除外基準:
    {' '.join(exclusion_criteria)}

    回答は箇条書きで、日本語でお願いします。
    """

    with st.spinner("Inclusion/Exclusion基準の分析を生成中..."):
        response = llm.invoke(criteria_prompt)
        criteria_analysis = response.content

    st.write(criteria_analysis)

# 関連文献の要約
st.header("関連文献の要約")

if structured_studies:
    publications = []
    for study in structured_studies:
        publications.extend(study['publications'])

    if publications:
        publication_summaries = []
        for pub in publications[:5]:  # 最初の5つの文献を要約
            summary = f"""
            タイトル: {pub['title']}
            引用: {pub['citation']}
            PMID: {pub['pmid']}
            """
            publication_summaries.append(summary)

        publication_prompt = f"""
        以下の臨床試験関連文献を要約し、以下の点について分析してください：
        1. 主な研究テーマ
        2. 重要な結果や発見
        3. 臨床的意義

        {' '.join(publication_summaries)}

        回答は箇条書きで、日本語でお願いします。
        """

        with st.spinner("関連文献の要約を生成中..."):
            response = llm.invoke(publication_prompt)
            publication_analysis = response.content

        st.write(publication_analysis)
    else:
        st.write("関連文献が見つかりませんでした。")

# 複数の試験の横断的な比較分析
st.header("複数の試験の横断的な比較分析")

if len(structured_studies) >= 2:
    selected_studies = st.multiselect(
        "比較分析する試験を2つ以上選択してください：",
        options=[f"{study['nct_id']}: {study['title']}" for study in structured_studies],
        default=[f"{structured_studies[0]['nct_id']}: {structured_studies[0]['title']}",
                 f"{structured_studies[1]['nct_id']}: {structured_studies[1]['title']}"]
    )

    if len(selected_studies) >= 2:
        comparison_data = []
        for selected in selected_studies:
            nct_id = selected.split(":")[0].strip()
            study = next((s for s in structured_studies if s['nct_id'] == nct_id), None)
            if study:
                comparison_data.append(f"""
                NCT ID: {study['nct_id']}
                タイトル: {study['title']}
                状態: {study['status']}
                介入: {', '.join([i['name'] for i in study['interventions']])}
                主要評価項目: {', '.join(study['outcomes']['primary'])}
                副次評価項目: {', '.join(study['outcomes']['secondary'])}
                包含基準: {', '.join(study['eligibility']['inclusion_criteria'])}
                除外基準: {', '.join(study['eligibility']['exclusion_criteria'])}
                """)

        comparison_prompt = f"""
        以下の臨床試験を比較分析し、以下の点について要約してください：
        1. 試験デザインの類似点と相違点
        2. 介入方法の比較
        3. 評価項目の違い
        4. 対象患者の選択基準の違い
        5. 各試験の強みと弱み

        {' '.join(comparison_data)}

        回答は箇条書きで、日本語でお願いします。
        """

        with st.spinner("試験の比較分析を生成中..."):
            response = llm.invoke(comparison_prompt)
            comparison_analysis = response.content

        st.write(comparison_analysis)
    else:
        st.write("比較するには2つ以上の試験を選択してください。")

# プロトコルドラフト生成支援
st.header("プロトコルドラフト生成支援")

if structured_studies:
    st.write("収集した情報を基に、新しい臨床試験のプロトコルドラフトを生成します。")
    
    target_condition = st.text_input("対象疾患：")
    intervention = st.text_input("介入方法：")
    primary_outcome = st.text_input("主要評価項目：")

    if st.button("プロトコルドラフトを生成"):
        protocol_prompt = f"""
        以下の情報を基に、新しい臨床試験のプロトコルドラフトを生成してください：

        対象疾患: {target_condition}
        介入方法: {intervention}
        主要評価項目: {primary_outcome}

        既存の臨床試験データ:
        {' '.join([f"NCT ID: {s['nct_id']}, タイトル: {s['title']}, 状態: {s['status']}, 介入: {', '.join([i['name'] for i in s['interventions']])}, 主要評価項目: {', '.join(s['outcomes']['primary'])}" for s in structured_studies[:5]])}

        プロトコルドラフトには以下の項目を含めてください：
        1. 試験の背景と目的
        2. 試験デザイン
        3. 対象患者の選択基準（包含基準と除外基準）
        4. 介入方法の詳細
        5. 評価項目（主要評価項目と副次評価項目）
        6. 統計学的考慮事項

        回答は日本語で、各項目を簡潔にまとめてください。
        """

        with st.spinner("プロトコルドラフトを生成中..."):
            response = llm.invoke(protocol_prompt)
            protocol_draft = response.content

        st.subheader("生成されたプロトコルドラフト")
        st.write(protocol_draft)
