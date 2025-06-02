import os
from flask import Flask, request, jsonify
from functools import wraps
from pytrends.request import TrendReq
import pandas as pd
import datetime

app = Flask(__name__)
pytrends = TrendReq(hl='en-US', tz=360)

API_KEY = os.environ.get('API_KEY')

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-KEY') or request.args.get('api_key')
        if not key or key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def convert_timestamp_to_string(df):
    # If date is datetime already
    if pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        # If date is timestamp in ms (int)
        df['date'] = df['date'].apply(
            lambda ts: datetime.datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
        )
    return df

@app.route('/')
def home():
    return 'Google Trends API is running!'

@app.route('/trends')
@require_api_key
def get_trends():
    keywords = request.args.get('keyword')
    geo_codes = request.args.get('geo', '')
    timeframe = request.args.get('time', 'today 12-m')

    if not keywords:
        return jsonify({'error': 'Missing keyword'}), 400

    keyword_list = [kw.strip() for kw in keywords.split(',')]
    if len(keyword_list) > 5:
        return jsonify({'error': 'Google Trends only supports up to 5 keywords at a time'}), 400

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
    final_df = convert_timestamp_to_string(final_df)

    return final_df.to_json(orient='records')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
