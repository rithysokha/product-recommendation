#!/usr/bin/env python3

import os
import pandas as pd
import glob

def load_csv_from_spark_output(csv_dir_path):
    """Load CSV data from Spark output directory (contains part files)"""
    print(f"Trying to load: {csv_dir_path}")
    print(f"Path exists: {os.path.exists(csv_dir_path)}")
    print(f"Is directory: {os.path.isdir(csv_dir_path)}")
    
    if not os.path.exists(csv_dir_path):
        print("Path does not exist")
        return None
    
    part_files = glob.glob(os.path.join(csv_dir_path, "part-*.csv"))
    print(f"Found part files: {part_files}")
    
    if not part_files:
        print("No part files found")
        return None
    
    dataframes = []
    for part_file in part_files:
        try:
            print(f"Reading: {part_file}")
            df = pd.read_csv(part_file)
            print(f"Loaded {len(df)} rows from {part_file}")
            dataframes.append(df)
        except Exception as e:
            print(f"Could not read part file {part_file}: {e}")
            continue
    
    if not dataframes:
        print("No dataframes loaded")
        return None
    
    combined_df = pd.concat(dataframes, ignore_index=True)
    print(f"Combined dataframe shape: {combined_df.shape}")
    return combined_df

if __name__ == "__main__":
    results_path = "results"
    
    edges_path = os.path.join(results_path, "edges.csv")
    print("=== Testing edges loading ===")
    edges_df = load_csv_from_spark_output(edges_path)
    if edges_df is not None:
        print("Edges loaded successfully!")
        print(f"Columns: {edges_df.columns.tolist()}")
        print(f"First 5 rows:\n{edges_df.head()}")
    else:
        print("Failed to load edges")
    
    print("\n=== Testing vertices loading ===")
    vertices_path = os.path.join(results_path, "vertices.csv")
    vertices_df = load_csv_from_spark_output(vertices_path)
    if vertices_df is not None:
        print("Vertices loaded successfully!")
        print(f"Columns: {vertices_df.columns.tolist()}")
        print(f"First 5 rows:\n{vertices_df.head()}")
    else:
        print("Failed to load vertices")
