
from flask import Flask, request, jsonify
from pytrends.request import TrendReq
import pandas as pd
from functools import wraps
import os
from datetime import datetime

app = Flask(__name__)

API_KEY = os.environ.get('API_KEY')

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-KEY') or request.args.get('api_key')
        if not key or key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

pytrends = TrendReq(hl='en-US', tz=360)

def convert_timestamp_to_string(df):
    df['date'] = df['date'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S"))
    return df

@app.route('/trends', methods=['GET'])
@require_api_key
def get_trends():
    keywords = request.args.get('keyword')
    geo = request.args.get('geo', '')  # e.g. 'US' or multiple separated by comma
    timeframe = request.args.get('timeframe', 'today 12-m')  # default 12 months

    if not keywords:
        return jsonify({'error': 'keyword parameter required'}), 400

    keyword_list = [k.strip() for k in keywords.split(',')]
    geo_list = [g.strip() for g in geo.split(',')] if geo else ['']

    combined_results = []

    for geo_code in geo_list:
        try:
            pytrends.build_payload(keyword_list, geo=geo_code, timeframe=timeframe)
            df = pytrends.interest_over_time()
            if df.empty:
                continue

            df = df.reset_index()
            df['geo'] = geo_code

            # Melt wide df with keywords columns into long format
            df_long = df.melt(id_vars=['date', 'geo'], value_vars=keyword_list,
                              var_name='keyword', value_name='value')
            combined_results.append(df_long)

        except Exception as e:
            print(f"Error fetching trends for geo={geo_code}: {e}")

    if not combined_results:
        return jsonify({'error': 'No data found'}), 404

    final_df = pd.concat(combined_results)
    final_df = convert_timestamp_to_string(final_df)

    # Convert DataFrame to list of dicts (JSON)
    result = final_df.to_dict(orient='records')

    return jsonify(result)
