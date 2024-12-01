# utils/utils.py
"""
このモジュールは、臨床試験データの処理に必要な汎用的なユーティリティ関数を提供します。
主な機能：
- HTMLタグの除去
- 日付文字列の標準化
- 臨床試験データの構造化
- データの集計と分析
- DataFrameのCSV変換

clean_html関数は、文字列からHTMLタグを除去し、プレーンテキストを返します。
主に臨床試験の説明文やサマリーからHTMLマークアップを取り除くために使用されます。

parse_date関数は、"Month DD, YYYY"形式の日付文字列を"YYYY-MM-DD"形式に
標準化します。日付形式が異なる場合や無効な場合はエラー処理を行います。

structure_clinical_trial関数は、APIから取得した生の臨床試験データを
構造化された辞書形式に変換します。以下の情報を抽出・整理します：
- 試験ID、タイトル、概要
- 試験の状態や日程
- 適格基準
- 介入内容
- アウトカム指標
- スポンサー情報
- 実施場所
- 関連文献

get_top_items関数は、項目のリストから出現頻度の高いものをカウントし、
上位n件を返します。データの傾向分析に使用されます。

convert_df_to_csvは、pandasのDataFrameをUTF-8エンコードのCSV形式に
変換します。データのエクスポートに使用されます。
"""
import re
import urllib.parse
from datetime import datetime
from collections import Counter

def clean_html(raw_html):
    """
    HTMLタグを文字列から除去する
    
    Args:
        raw_html (str): HTMLタグを含む文字列
    
    Returns:
        str: HTMLタグを除去した文字列
    """
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def parse_date(date_string):
    """
    日付文字列を標準形式に変換する
    
    Args:
        date_string (str): "Month DD, YYYY"形式の日付文字列
    
    Returns:
        str: "YYYY-MM-DD"形式の日付文字列、または変換できない場合は元の文字列
        None: 入力がNoneの場合
    """
    if date_string:
        try:
            return datetime.strptime(date_string, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return date_string
    return None

def structure_clinical_trial(study):
    """
    臨床試験データを構造化された形式に変換する
    
    Args:
        study (dict): APIから取得した生の臨床試験データ
    
    Returns:
        dict: 構造化された臨床試験データ
        None: 入力データが無効な場合
    """
    if not isinstance(study, dict):
        print(f"Warning: Unexpected study data type: {type(study)}")
        return None

    protocol_section = study.get('protocolSection', {})
    derived_section = study.get('derivedSection', {})

    if not isinstance(protocol_section, dict) or not isinstance(derived_section, dict):
        print(f"Warning: Unexpected data structure in study")
        return None

    # 適格基準モジュールの取得
    eligibility_module = protocol_section.get('eligibilityModule', {})

    structured_data = {
        "nct_id": protocol_section.get('identificationModule', {}).get('nctId'),
        "title": protocol_section.get('identificationModule', {}).get('officialTitle'),
        "brief_summary": clean_html(protocol_section.get('descriptionModule', {}).get('briefSummary', '')),
        "detailed_description": clean_html(protocol_section.get('descriptionModule', {}).get('detailedDescription', '')),
        "status": protocol_section.get('statusModule', {}).get('overallStatus'),
        "start_date": parse_date(protocol_section.get('statusModule', {}).get('startDateStruct', {}).get('date')),
        "end_date": parse_date(protocol_section.get('statusModule', {}).get('completionDateStruct', {}).get('date')),

        # 従来のeligibilityを保持
        "eligibility": {
            "criteria": clean_html(eligibility_module.get('eligibilityCriteria', '')),
            "healthy_volunteers": eligibility_module.get('healthyVolunteers'),
            "sex": eligibility_module.get('sex'),
            "gender_based": eligibility_module.get('genderBased'),
            "minimum_age": eligibility_module.get('minimumAge'),
            "maximum_age": eligibility_module.get('maximumAge'),
        },

        # 適格基準関連のフィールドを個別のカラムとして定義
        "inclusion_criteria": parse_criteria(eligibility_module.get('eligibilityCriteria', ''), 'Inclusion'),
        "exclusion_criteria": parse_criteria(eligibility_module.get('eligibilityCriteria', ''), 'Exclusion'),
        "healthy_volunteers_eligible": eligibility_module.get('healthyVolunteers'),
        "sex_eligible": eligibility_module.get('sex'),
        "minimum_age": eligibility_module.get('minimumAge'),
        "maximum_age": eligibility_module.get('maximumAge'),

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

    # 場所情報の処理
    locations_module = protocol_section.get('contactsLocationsModule', {})
    locations = locations_module.get('locations', [])

    if isinstance(locations, list):
        structured_data["locations"] = [
            {
                "facility": location.get('facility', {}).get('name') if isinstance(location.get('facility'), dict) else location.get('facility'),
                "city": location.get('city'),
                "country": location.get('country')
            }
            for location in locations if isinstance(location, dict)
        ]
    elif isinstance(locations, str):
        structured_data["locations"] = [{"facility": locations, "city": None, "country": None}]

    return structured_data

def parse_criteria(criteria_text, criteria_type):
    """
    選択・除外基準のテキストを解析する
    
    Args:
        criteria_text (str): 生の基準テキスト
        criteria_type (str): 'Inclusion' または 'Exclusion'
    
    Returns:
        str: 整形された基準テキスト
    """
    if not criteria_text:
        return None
        
    # 基準テキストを行に分割
    lines = criteria_text.split('\n')
    criteria_section = []
    in_target_section = False
    
    for line in lines:
        if f"{criteria_type} Criteria:" in line:
            in_target_section = True
            continue
        elif "Criteria:" in line and criteria_type not in line:
            in_target_section = False
        elif in_target_section and line.strip():
            criteria_section.append(line.strip())
    
    return '\n'.join(criteria_section) if criteria_section else None

def get_top_items(items, n=5):
    """
    リスト内の要素の出現頻度を集計し、上位n件を返す
    
    Args:
        items (list): 集計対象のリスト
        n (int): 返す上位件数（デフォルト: 5）
    
    Returns:
        list: (item, count)のタプルを含むリスト
    """
    counter = Counter(items)
    return counter.most_common(n)

def convert_df_to_csv(df):
    """
    DataFrameをCSV形式に変換する

    Args:
        df (pandas.DataFrame): 変換対象のDataFrame

    Returns:
        bytes: UTF-8エンコードされたCSVデータ
    """
    return df.to_csv(index=False).encode('utf-8')