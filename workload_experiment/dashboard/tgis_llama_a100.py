import os
from datetime import timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import warnings
warnings.filterwarnings('ignore')

def get_tgi_metrics(metric_name, columns, filter_pod, folder):
    files = os.listdir(folder)
    dataframes = []
    for i in files:
        if i.startswith(metric_name):
            temp = pd.read_csv(f'{folder}{i}')
            temp = temp[columns]
            dataframes.append(temp)
    result = pd.concat(dataframes)
    for key in filter_pod:
        result = result[result[key].isin(filter_pod[key])]
    result.drop_duplicates(inplace=True)
    return result.reset_index(drop=True)

def get_tgi_df(metrics, tgi_columns, tgi_merge_columns, tgi_filter, folder):
    tgi_df = get_tgi_metrics(metrics[0], tgi_columns, tgi_filter, folder)
    tgi_df.rename(columns={"value":metrics[0]}, inplace=True)
    for metric in metrics[1:]:
        temp_df = get_tgi_metrics(metric, tgi_columns, tgi_filter, folder)
        tgi_df = pd.merge(tgi_df, temp_df, on=tgi_merge_columns)
        tgi_df.rename(columns={"value":metric}, inplace=True)
    return tgi_df

def clean_data(df, counter_list):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df.reset_index(inplace=True, drop=True)
    return df

def analyze_model(model_name):
    request_rates = {
        'llama': [10,12,15,20,25,35,55]
    }

    tgi_metrics = [
        "tgi_request_generated_tokens_sum",
        "tgi_request_generated_tokens_count",
        "tgi_batch_current_size",
        "tgi_request_duration_sum",
        "tgi_request_duration_count",
        "tgi_request_queue_duration_sum",
        "tgi_request_queue_duration_count",
        "tgi_queue_size",
        "tgi_request_failure",
        "tgi_request_input_length_sum",
        "tgi_request_input_length_count",
        "tgi_request_count"
    ]

    tgi_metrics_with_user = [
   
    "tgi_request_duration_sum",
    "tgi_request_duration_count",
    "tgi_request_inference_duration_count",
    "tgi_request_inference_duration_sum",
    "tgi_request_generated_tokens_sum",
    "tgi_request_generated_tokens_count"]


    tgi_columns = ['timestamp', 'job', "namespace", "pod", "value"]
    tgi_merge_columns = ['timestamp', 'job', "namespace", "pod"]

    tgi_user_columns = ['timestamp', 'job', "namespace", "pod", "value", "user"]
    tgi_user_merge_columns = ['timestamp', 'job', "namespace", "pod", "user"]




    tgi_filters = {
        'llama': {'pod': ['llama3-v3']}
    }

    results = []
    tgi_data_dict = {}
    exclude_rates = {
        'llama': [1000]
    }

    for rate in request_rates[model_name]:
        # folder = f'metrics_data/a100/tgis/llama-a100/{rate}/'
        folder = f'no_priority_exps_op_60/llama3_a100_no_priority/rr_{rate}_op_60/tgis/'
        tgi_df = get_tgi_df(tgi_metrics, tgi_columns, tgi_merge_columns, tgi_filters[model_name], folder)
        tgi_df = clean_data(tgi_df, tgi_metrics)

        tgi_df_user_llama = clean_data(get_tgi_df(tgi_metrics_with_user, tgi_user_columns, tgi_user_merge_columns, tgi_filters[model_name],folder),tgi_metrics_with_user)

        
        tgi_data = tgi_df[['timestamp', 'tgi_request_queue_duration_sum', 'tgi_request_queue_duration_count', 
                           'tgi_batch_current_size', 'tgi_queue_size', 'tgi_request_generated_tokens_sum', 
                           'tgi_request_generated_tokens_count', 'tgi_request_duration_sum', 'tgi_request_duration_count', 
                           'tgi_request_input_length_sum', 'tgi_request_input_length_count','tgi_request_failure','tgi_request_count']]

        columns = ['tgi_request_duration_count', 'tgi_request_generated_tokens_sum', 'tgi_request_duration_sum',
                   'tgi_request_input_length_sum', 'tgi_request_input_length_count', 'tgi_request_generated_tokens_count']

        temp = tgi_data[columns]

        for col in columns:
            temp[col] = pd.to_numeric(temp[col])

        tgi_failure_count = tgi_data['tgi_request_failure'].diff().sum()
        tgi_total_count = tgi_data['tgi_request_count'].diff().sum()


        tgi_queue_size_values = tgi_data['tgi_queue_size']
        average_tgi_queue_size = tgi_queue_size_values.mean()
        percentile_95_queue_size = tgi_queue_size_values.quantile(0.95)

        tgi_batch_size_values = tgi_data['tgi_batch_current_size']
        average_tgi_batch_size = tgi_batch_size_values.mean()
        percentile_95_batch_size = tgi_batch_size_values.quantile(0.95)

        temp['queue_duration_count'] = tgi_data['tgi_request_queue_duration_count'].diff()
        temp['queue_duration_sum'] = tgi_data['tgi_request_queue_duration_sum'].diff()
        tgi_data['mean_queue_time'] = temp['queue_duration_sum'] / temp['queue_duration_count']
        mean_queue_time = tgi_data['mean_queue_time'].mean()
        percentile_95_queue_waiting_time = tgi_data['mean_queue_time'].quantile(0.95)

        # temp['request_duration_sum'] = tgi_data['tgi_request_duration_sum'].diff()
        # temp['request_duration_count'] = tgi_data['tgi_request_duration_count'].diff()

        tmp_llama = tgi_df_user_llama[tgi_df_user_llama['user'] == 'Alan']

        tgi_data['e2e_latency'] = tmp_llama['tgi_request_duration_sum'].diff() / tmp_llama['tgi_request_duration_count'].diff()


        # tgi_data['e2e_latency'] = temp['request_duration_sum'] / temp['request_duration_count']
        mean_e2e_latency = tgi_data['e2e_latency'].mean()
        percentile_95_e2e_latency = tgi_data['e2e_latency'].quantile(0.95)

        results.append({
            'rate': rate,
            'average_tgi_batch_size': average_tgi_batch_size,
            'percentile_95_batch_size': percentile_95_batch_size,
            'mean_queue_time': mean_queue_time,
            'percentile_95_queue_waiting_time': percentile_95_queue_waiting_time,
            'mean_e2e_latency': mean_e2e_latency,
            'percentile_95_e2e_latency': percentile_95_e2e_latency,
            'tgi_failure_count': tgi_failure_count,
            'tgi_total_count': tgi_total_count
        })

        if rate not in exclude_rates[model_name]:
            tgi_data_dict[rate] = {
                'mean_queue_time': tgi_data['mean_queue_time'],
                'e2e_latency': tgi_data['e2e_latency']
            }

    return results, tgi_data_dict

def print_results(results):
    for result in results:
        print(f"Request Rate: {result['rate']} RPM")
        print(f"95 percentile Mean Batch Size: {result['percentile_95_batch_size']}")
        print(f"Mean Batch Size: {result['average_tgi_batch_size']}")
        print(f"Mean TGIS Queue Waiting Time: {result['mean_queue_time']}")
        print(f"95 percentile Mean TGIS Queue Waiting Time: {result['percentile_95_queue_waiting_time']}")
        print(f"Mean E2E Latency: {result['mean_e2e_latency']}")
        print(f"95 percentile E2E Latency: {result['percentile_95_e2e_latency']}")
        print(f"TGIS Failure Count: {result['tgi_failure_count']}")
        print(f"TGIS Total Count: {result['tgi_total_count']}")
        print()

def plot_cdf(data, metric_name, xlabel, title, filename):
    plt.figure(figsize=(10, 6))
    for rate, values in data.items():
        sorted_data = np.sort(values.dropna())
        yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
        plt.plot(sorted_data, yvals, label=f'{rate} RPM')
    plt.xlabel(xlabel)
    plt.ylabel("CDF")
    plt.legend(loc='lower right')
    plt.title(title)
    plt.grid(True)
    plt.savefig(filename)
    plt.close()  # Close the figure to avoid memory leaks

def plot_results(tgi_data_dict, model):
    plot_cdf({rate: data['mean_queue_time'] for rate, data in tgi_data_dict.items()},
             "mean_queue_time", "Queue Time (s)", "CDF of Queue Time for Different Request Rates",
            "images/" + model + "_tgis_mean_queue_time.png")
    
    plot_cdf({rate: data['e2e_latency'] for rate, data in tgi_data_dict.items()},
             "e2e_latency", "End-to-End Latency (s)", "CDF of End-to-End Latency for Different Request Rates",
             "images/" + model + "_tgis_e2e_latency.png")

if __name__ == "__main__":
    models = ['llama']
    for model_name in models:
        print(f'Analyzing {model_name}...')
        results, tgi_data_dict = analyze_model(model_name)
        print_results(results)
        plot_results(tgi_data_dict, model_name)
