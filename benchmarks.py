from queries import range_query, grid_index_range_query, within, knn_query_grid_index
from DOTS.run_dots import dots
from RLTS.run_rlts import rlts
from compression_models import pmc_midrange
import pandas as pd
from squish import squish, SquishE
import os
import csv
from pympler import asizeof
import random
import heapq
from haversine import haversine
import time


def test_query(coordinates, rtree):
    start = time.perf_counter()
    results = range_query(coordinates, rtree)
    end = time.perf_counter()
    print("Query took ", end - start, " seconds to execute.\n")

def test_query_grid_index(coordinates, grid_index):
    start = time.perf_counter()
    results = grid_index_range_query(coordinates, grid_index)
    end = time.perf_counter()
    print("Query took ", end - start, " seconds to execute.\n")


def range_query_no_compression_no_indexing(coordinates, points):
    start = time.perf_counter()
    results = []
    for index, row in points.iterrows():
        point = (row["latitude"], row["longitude"])
        if within(coordinates, point):
            results.append(row)
    end = time.perf_counter()
    print("Query took ", end - start, " seconds to execute.\n")
    return results

def knn_no_indexing(poi, df):
    closest_point = df.iloc[0]
    for index, row in df.iterrows():
        if haversine((row["latitude"], row["longitude"]), poi) < haversine((closest_point["latitude"], closest_point["longitude"]), poi):
            closest_point = row
    return closest_point

def knn_grid_index(point, grid_index):
    start = time.perf_counter()
    results = knn_query_grid_index(grid_index, point, 2)
    end = time.perf_counter()
    print("Query took ", end - start, " seconds to execute.\n")


def compression_ratio(df, simplified_df):
    return len(df) / len(simplified_df)


def calculate_range_query_accuracy(bbox, original_df, simplified_df):
    min_y, min_x, max_y, max_x = bbox

    def points_in_bbox(df):
        return df[(df['longitude'] >= min_x) & (df['longitude'] <= max_x) & (df['latitude'] >= min_y) & (df['latitude'] <= max_y)]

    original_in_bbox = points_in_bbox(original_df)
    simplified_in_bbox = points_in_bbox(simplified_df)
    count_original_in_bbox = len(original_in_bbox)
    count_simplified_in_bbox = len(simplified_in_bbox)

    if count_original_in_bbox != 0:
        accuracy = (count_simplified_in_bbox / count_original_in_bbox)
    else:
        accuracy = 1

    return accuracy

def print_full_size(grid_index, label):
    print(f"Full memory size of {label}: {asizeof.asizeof(grid_index)} bytes")

# Function to print full memory usage of an object
def print_full_size(obj, label):
    print(f"Full memory size of {label}: {asizeof.asizeof(obj)} bytes")

def get_random_bbox(min_lat, min_lon, max_lat, max_lon):
    lat1 = random.uniform(min_lat, max_lat)
    lat2 = random.uniform(min_lat, max_lat)
    lon1 = random.uniform(min_lon, max_lon)
    lon2 = random.uniform(min_lon, max_lon)
    min_lat = min(lat1, lat2)
    max_lat = max(lat1, lat2)
    min_lon = min(lon1, lon2)
    max_lon = max(lon1, lon2)
    return [min_lat, min_lon, max_lat, max_lon]

def get_random_trajectory(min_rows=1000, max_rows=10000):
    folder_path = "release/taxi_log_2008_by_id"
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path)]
    random.shuffle(files)

    for file_path in files:
        df = pd.read_csv(file_path, names=["taxi_id", "datetime", "longitude", "latitude"])
        if len(df) > min_rows and len(df) < max_rows:
            return df

    return None

def get_trajectories(min_rows=0, max_rows=20000):
    folder_path = "release/taxi_log_2008_by_id"
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path)]
    random.shuffle(files)
    dfs = []

    for file_path in files:
        df = pd.read_csv(file_path, names=["taxi_id", "datetime", "longitude", "latitude"])
        if len(df) > min_rows and len(df) < max_rows:
            dfs.append(df)
        if len(dfs) > 41:
            break

    return dfs

def eval_accuracy(test_count):
    i = 0
    rlts_values = []
    pmc = []
    dag = []

    while i < test_count:
        print("round: ", i)
        df = get_random_trajectory()
        bbox = get_random_bbox(df["latitude"].min(), df["longitude"].min(), df["latitude"].max(), df["longitude"].max())

        dag_df, _ = dots(df, 0.05, 1.5)
        dag.append(calculate_range_query_accuracy(bbox, df, dag_df))

        rlts_df, _ = rlts(df, 0.05)
        rlts_values.append(calculate_range_query_accuracy(bbox, df, rlts_df))

        pmc_df = pmc_midrange(df, 0.02)
        pmc.append(calculate_range_query_accuracy(bbox, df, pmc_df))
        i += 1
    dict = {"rlts": rlts_values, "pmc": pmc, "dag": dag}
    df = pd.DataFrame(dict)
    df.to_csv("eval_accuracy.csv")


def eval_time(min_points, max_points, output_file='timing_results.csv'):
    time_DOTS = 0
    time_RLTS = 0
    trajectories = get_trajectories(min_points, max_points)
    if len(trajectories) > 100: #we want max hundred trajectories
        trajectories = trajectories[:100]
    n_of_trajectories = len(trajectories)
    print(n_of_trajectories)

    with open(output_file, 'a', newline='') as f:
        writer = csv.writer(f)
        # Write the header row

        for df in trajectories:
            start = time.perf_counter()
            result, _ = dots(df, 0.1, 1)
            end = time.perf_counter()
            dots_time = end - start
            time_DOTS += dots_time

            compression = len(result)
            print(len(df))
            print(compression)
            if compression < 10:
                compression = 10

            start = time.perf_counter()
            rlts(df, compression)
            end = time.perf_counter()
            rlts_time = end - start
            time_RLTS += rlts_time

            # start = time.perf_counter()
            # squish(df, (len(df)/compression))
            # end = time.perf_counter()
            # squish_time = end - start

            # Write the times for each run to the CSV file
            writer.writerow([dots_time, rlts_time, max_points])

    avg_DOTS_time = (time_DOTS / n_of_trajectories)
    avg_RLTS_time = (time_RLTS / n_of_trajectories)
    return avg_DOTS_time, avg_RLTS_time

def compression_time_test():
    print("Running compression time test")
    eval_time(100, 500) #min and max points in the trajectory
    eval_time(500, 1000)
    eval_time(1000, 1500)
    eval_time(1500, 2000)
    eval_time(2000, 3000)
    eval_time(3000, 4000)
    eval_time(4000, 5000)


def _error_vs_ratio_test(error_bound):
    total_error_dots = 0
    total_error_rlts = 0
    i= 0
    compression_rates = 0
    trajectories = get_trajectories(1700, 2000)
    trajectories = trajectories[:5]
    #sample the overall error for 20 trajectories
    for df in trajectories:
        print(i)
        dots_df, dots_error = dots(df, error_bound, 1.5)
        total_error_dots += dots_error
        rlts_df, rlts_error = rlts(df, len(dots_df))
        total_error_rlts += rlts_error
        compr_rate = len(df) / len(dots_df)
        compression_rates += compr_rate
        i += 1
    #We find the average error over all trajectories
    total_error_dots = (total_error_dots / len(trajectories))
    total_error_rlts = (total_error_rlts / len(trajectories))
    avg_compression_rate = compression_rates / len(trajectories)
    return total_error_rlts, total_error_dots, avg_compression_rate

def error_vs_ratio_test():
    print("Running Error vs ratio test for RLTS and DOTS")
    rlts_errors = []
    dots_errors = []
    compr_rates = []
    error_bounds = [0.1, 1, 2, 3, 4, 5]
    for x in error_bounds:
        total_error_rlts, total_error_dots, avg_comp_rate = _error_vs_ratio_test(x)
        rlts_errors.append(total_error_rlts)
        dots_errors.append(total_error_dots)
        compr_rates.append(avg_comp_rate)
    print(rlts_errors, dots_errors, compr_rates)

#error_vs_ratio_test()
#compression_time_test()
eval_accuracy(100)
