import re
from datetime import datetime
from collections import Counter

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
        "eligibility": {},
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

    # 適格基準の処理
    eligibility_module = protocol_section.get('eligibilityModule', {})
    structured_data["eligibility"] = {
        "criteria": clean_html(eligibility_module.get('eligibilityCriteria', '')),
        "healthy_volunteers": eligibility_module.get('healthyVolunteers'),
        "sex": eligibility_module.get('sex'),
        "gender_based": eligibility_module.get('genderBased'),
        "minimum_age": eligibility_module.get('minimumAge'),
        "maximum_age": eligibility_module.get('maximumAge'),
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

def get_top_items(items, n=5):
    counter = Counter(items)
    return counter.most_common(n)

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')