import subprocess
import sys
import os
import csv
import csv

csv_file = "commits.csv"

# Open the CSV file
with open(csv_file, "r") as file:
    # Create a CSV reader object
    csv_reader = csv.reader(file)

    # Iterate over each row in the CSV file
    for row in csv_reader:
        # Print each row
        print(row)
