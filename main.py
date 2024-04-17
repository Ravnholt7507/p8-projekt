import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import torch
from dataloader import load_single_file, load_bulk
from compression_models import pmc_midrange
from r_tree import init_rtree, make_all_mbrs
from queries import time_query, count_elements, range_query
import time
from RLTS.simplify import simplify
from RLTS.train import train
from RLTS.policy import PolicyNetwork
from RLTS.buffer import TrajectoryEnv
from benchmarks import range_query_no_compression_no_indexing
from ui import plot_query, plot_mbrs


def main():
    mbr_points = 10

    df = pd.read_csv("release/taxi_log_2008_by_id/1.txt",
                     sep=",",
                     names=["taxi_id", "datetime", "longitude", "latitude"])
    """    
    env = TrajectoryEnv(df)
    policy_network = PolicyNetwork(input_size=env.k, hidden_size=15, output_size=env.k)
    train(env, policy_network, 1) # resultate bliver lagt i RLTS/models/test_model som bliver hentet på næste linje
    policy_network.load_state_dict(torch.load("RLTS/models/test_model"))
    policy_network.eval()
    simplify(df, policy_network, env)
    """

    final_df = pmc_midrange(df, 0.02)

    # r_tree with compression
    rectangles = make_all_mbrs(final_df, mbr_points)

    rtree = init_rtree(rectangles)

    # r_tree without compression
    rectangles = make_all_mbrs(df, mbr_points)

    no_comp_rtree = init_rtree(rectangles)
    # examples of time queries
    # start_time = "2008-02-02 15:00:00"
    # end_time = "2008-02-03 15:36:10"
    # results = time_query(start_time, end_time, rtree)
    
    # example of query for range search
    coordinates = [39.9, 116.4, 39.95, 116.6]
    # coordinates = [39.5, 116, 40, 117]
    print("WITH PMC-COMPRESSION AND WITH R-TREE INDEXING:")
    start = time.time()
    results = range_query(coordinates, rtree)
    end = time.time()
    print("Query with PMC-midrange compression and r-tree indexing took ", end - start, " seconds to execute.")

    print("\nWITHOUT PMC-COMPRESSION AND WITH R-TREE INDEXING")
    start = time.time()
    results = range_query(coordinates, no_comp_rtree)
    end = time.time()
    print("Query without PMC-midrange compression and with r-tree indexing took ", end - start, " seconds to execute.")

    print("\nWITHOUT PMC-COMPRESSION AND WITHOUT R-TREE INDEXING:")
    start = time.time()
    bench_results = range_query_no_compression_no_indexing(coordinates, df)
    end = time.time()
    print("Query without compression and r-tree indexing took ", end - start, "seconds to execute.")

    # print("\nWITH RLTS AND WITH R-TREE INDEXING:")
    # start = time.time()
    # bench_results = range_query()
    # end = time.time()
    # print("Query without compression and r-tree indexing took ", end - start, "seconds to execute.")

    plot_mbrs(df["longitude"], df["latitude"], rtree)
    #plot_query(df["longitude"], df["latitude"], coordinates)

main()
