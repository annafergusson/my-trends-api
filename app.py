from flask import Flask, request, jsonify
from pytrends.request import TrendReq
import pandas as pd

app = Flask(__name__)
pytrends = TrendReq(hl='en-US', tz=360)

@app.route('/')
def home():
    return 'Google Trends API is running!'

@app.route('/trends')
def get_trends():
    keywords = request.args.get('keyword')
    geo_codes = request.args.get('geo', '')
    timeframe = request.args.get('time', 'today 12-m')

    if not keywords:
        return jsonify({'error': 'Missing keyword'}), 400

    keyword_list = [kw.strip() for kw in keywords.split(',')]
    if len(keyword_list) > 5:
        return jsonify({'error': 'Google Trends only supports 5 keywords at a time'}), 400

    geo_list = [g.strip() for g in geo_codes.split(',')] if geo_codes else ['']

    combined_results = []

    for geo in geo_list:
        try:
            pytrends.build_payload(keyword_list, geo=geo, timeframe=timeframe)
            df = pytrends.interest_over_time()

            if df.empty:
                continue

            df = df.reset_index()
            df['geo'] = geo
            df = df[['date'] + keyword_list + ['geo']]
            combined_results.append(df)
        except Exception as e:
            print(f"Error with geo={geo}: {e}")

    if not combined_results:
        return jsonify({'error': 'No data found'}), 404

    final_df = pd.concat(combined_results)
    return final_df.to_json(orient='records')
