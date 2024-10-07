import requests
from utils import structure_clinical_trial

class APIHandler:
    def __init__(self, api_url):
        self.api_url = api_url

    def fetch_studies(self, params):
        all_studies = []
        total_count = 0

        while True:
            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code}\n{response.text}")

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

    def structure_data(self, studies):
        return [structure_clinical_trial(study) for study in studies if study is not None]

    def fetch_and_structure_studies(self, query_params):
        params = {
            'format': 'json',
            'pageSize': 100,  # 1ページあたりの結果数
            'countTotal': 'true',  # 総結果数を取得
        }
        params.update(query_params)

        studies, total_count = self.fetch_studies(params)
        structured_studies = self.structure_data(studies)

        return structured_studies, total_count