#!/usr/bin/env python3
# Copyright (c) 2024 Blockchain at Berkeley.  All rights reserved.
# SPDX-License-Identifier: MIT

import os
import csv
import json
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from tqdm import tqdm
from experiment_framework import PromptTestingFramework
import numpy as np

PROMPT_CATEGORIES = [
    "direct",
    "polite",
    "conversational",
    "question",
    "synonyms",
    "reordered",
    "symbols",
    "verbose",
    "technical",
    "implicit",
    "spelled_number",
    "decimal_number",
    "missing_amount",
    "missing_chain",
    "ambiguous_amount",
    "approximate_amount",
]

INTENT_TYPES = ["swap", "transfer", "remittance"]


def filter_test_cases(test_cases, category=None, intent_type=None):
    """
    Filter test cases by category and/or intent type.

    Args:
        test_cases: List of test case dictionaries
        category: Optional category to filter by
        intent_type: Optional intent type to filter by

    Returns:
        Filtered list of test cases
    """
    filtered_cases = test_cases

    if category:
        filtered_cases = [
            case
            for case in filtered_cases
            if "Category" in case and case["Category"] == category
        ]

    if intent_type:
        filtered_cases = [
            case
            for case in filtered_cases
            if "Expected Intent" in case
            # FIX: Don't try to parse the value again since it's already a dictionary
            and case["Expected Intent"]["transaction_type"] == intent_type
        ]

    return filtered_cases


def run_category_experiments(framework, test_cases_file, results_dir):
    """
    Run experiments for each prompt category.

    Args:
        framework: PromptTestingFramework instance
        test_cases_file: Path to the CSV file with test cases
        results_dir: Directory to save results
    """
    # Create results directory
    os.makedirs(results_dir, exist_ok=True)

    # Load all test cases
    all_test_cases = framework.load_test_cases(test_cases_file)

    # Dictionary to store results for each category
    category_results = {}

    # Run experiment for each category
    for category in tqdm(PROMPT_CATEGORIES, desc="Testing prompt categories"):
        category_test_cases = filter_test_cases(all_test_cases, category=category)

        if not category_test_cases:
            print(f"No test cases found for category: {category}")
            continue

        # Run the test suite
        summary = framework.run_test_suite(
            test_cases=category_test_cases,
            suite_name=f"category_{category}",
            use_test_tokens=False,
        )

        # Store results
        category_results[category] = summary

    # Generate comparison visualization
    generate_category_comparison(category_results, results_dir)

    return category_results


def run_intent_type_experiments(framework, test_cases_file, results_dir):
    """
    Run experiments for each intent type.

    Args:
        framework: PromptTestingFramework instance
        test_cases_file: Path to the CSV file with test cases
        results_dir: Directory to save results
    """
    # Create results directory
    os.makedirs(results_dir, exist_ok=True)

    # Load all test cases
    all_test_cases = framework.load_test_cases(test_cases_file)

    # Dictionary to store results for each intent type
    intent_results = {}

    # Run experiment for each intent type
    for intent_type in tqdm(INTENT_TYPES, desc="Testing intent types"):
        # Filter test cases for this intent type
        intent_test_cases = filter_test_cases(all_test_cases, intent_type=intent_type)

        if not intent_test_cases:
            print(f"No test cases found for intent type: {intent_type}")
            continue

        # Run the test suite
        summary = framework.run_test_suite(
            test_cases=intent_test_cases,
            suite_name=f"intent_{intent_type}",
            use_test_tokens=False,
        )

        # Store results
        intent_results[intent_type] = summary

    # Generate comparison visualization
    generate_intent_comparison(intent_results, results_dir)

    return intent_results


def run_cross_experiments(framework, test_cases_file, results_dir):
    """
    Run cross-experiments for each category and intent type combination.

    Args:
        framework: PromptTestingFramework instance
        test_cases_file: Path to the CSV file with test cases
        results_dir: Directory to save results
    """
    # Create results directory
    os.makedirs(results_dir, exist_ok=True)

    # Load all test cases
    all_test_cases = framework.load_test_cases(test_cases_file)

    # Dictionary to store results for each combination
    cross_results = {}

    # Initialize results matrix
    results_matrix = pd.DataFrame(index=PROMPT_CATEGORIES, columns=INTENT_TYPES)

    # Run experiment for each combination
    for category in tqdm(
        PROMPT_CATEGORIES, desc="Cross-testing categories and intents"
    ):
        for intent_type in INTENT_TYPES:
            # Filter test cases for this combination
            filtered_cases = filter_test_cases(
                all_test_cases, category=category, intent_type=intent_type
            )

            if not filtered_cases:
                print(f"No test cases found for {category} + {intent_type}")
                results_matrix.loc[category, intent_type] = None
                continue

            # Run the test suite
            summary = framework.run_test_suite(
                test_cases=filtered_cases,
                suite_name=f"cross_{category}_{intent_type}",
                use_test_tokens=False,
            )

            # Store results
            cross_key = f"{category}_{intent_type}"
            cross_results[cross_key] = summary

            # Update results matrix
            results_matrix.loc[category, intent_type] = summary["accuracy"]

    # Generate heatmap visualization
    generate_heatmap(results_matrix, results_dir)

    return cross_results, results_matrix


def generate_category_comparison(category_results, results_dir):
    """
    Generate comparison visualization for prompt categories.

    Args:
        category_results: Dictionary with results for each category
        results_dir: Directory to save visualizations
    """
    categories = list(category_results.keys())
    accuracies = [category_results[cat]["accuracy"] * 100 for cat in categories]
    response_times = [category_results[cat]["avg_response_time"] for cat in categories]

    # Sort by accuracy
    sorted_indices = sorted(
        range(len(accuracies)), key=lambda i: accuracies[i], reverse=True
    )
    sorted_categories = [categories[i] for i in sorted_indices]
    sorted_accuracies = [accuracies[i] for i in sorted_indices]
    sorted_times = [response_times[i] for i in sorted_indices]

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot accuracy
    ax1.bar(sorted_categories, sorted_accuracies, color="#2196F3")
    ax1.set_title("Accuracy by Prompt Category")
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_ylim(0, 100)
    ax1.set_xticklabels(sorted_categories, rotation=45, ha="right")

    # Plot response time
    ax2.bar(sorted_categories, sorted_times, color="#4CAF50")
    ax2.set_title("Average Response Time by Prompt Category")
    ax2.set_ylabel("Response Time (seconds)")
    ax2.set_xticklabels(sorted_categories, rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(f"{results_dir}/category_comparison.png", dpi=300)
    plt.close()


def generate_intent_comparison(intent_results, results_dir):
    """
    Generate comparison visualization for intent types.

    Args:
        intent_results: Dictionary with results for each intent type
        results_dir: Directory to save visualizations
    """
    intent_types = list(intent_results.keys())
    accuracies = [intent_results[intent]["accuracy"] * 100 for intent in intent_types]
    response_times = [
        intent_results[intent]["avg_response_time"] for intent in intent_types
    ]

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Plot accuracy
    ax1.bar(intent_types, accuracies, color="#9C27B0")
    ax1.set_title("Accuracy by Intent Type")
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_ylim(0, 100)

    # Plot response time
    ax2.bar(intent_types, response_times, color="#FF9800")
    ax2.set_title("Average Response Time by Intent Type")
    ax2.set_ylabel("Response Time (seconds)")

    plt.tight_layout()
    plt.savefig(f"{results_dir}/intent_comparison.png", dpi=300)
    plt.close()


def generate_heatmap(results_matrix, results_dir):
    """
    Generate heatmap visualization for category-intent combinations.

    Args:
        results_matrix: DataFrame with accuracy results
        results_dir: Directory to save visualizations
    """
    # Convert to percentage
    heat_data = results_matrix.fillna(0) * 100

    plt.figure(figsize=(12, 10))
    plt.title("Accuracy by Prompt Category and Intent Type (%)")

    # Create heatmap
    cmap = plt.cm.YlGnBu
    heatmap = plt.pcolor(heat_data, cmap=cmap, vmin=0, vmax=100)

    # Add color bar
    cbar = plt.colorbar(heatmap)
    cbar.set_label("Accuracy (%)")

    # Add labels
    plt.xticks(np.arange(0.5, len(heat_data.columns)), heat_data.columns)
    plt.yticks(np.arange(0.5, len(heat_data.index)), heat_data.index)

    # Rotate x labels
    plt.xticks(rotation=0)

    # Add text annotations
    for i in range(len(heat_data.index)):
        for j in range(len(heat_data.columns)):
            value = heat_data.iloc[i, j]
            if not pd.isnull(value) and value > 0:
                plt.text(
                    j + 0.5,
                    i + 0.5,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    color="black" if value > 50 else "white",
                )

    plt.tight_layout()
    plt.savefig(f"{results_dir}/category_intent_heatmap.png", dpi=300)
    plt.close()


def export_results_to_csv(results, filename):
    """
    Export experiment results to CSV.

    Args:
        results: Dictionary with experiment results
        filename: Path to save the CSV file
    """
    with open(filename, "w", newline="") as csvfile:
        fieldnames = [
            "experiment",
            "total_tests",
            "correct_tests",
            "accuracy",
            "avg_response_time",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for experiment, summary in results.items():
            writer.writerow(
                {
                    "experiment": experiment,
                    "total_tests": summary["total_tests"],
                    "correct_tests": summary["correct_tests"],
                    "accuracy": summary["accuracy"],
                    "avg_response_time": summary["avg_response_time"],
                }
            )


def main():
    """Main entry point for running experiments."""
    parser = argparse.ArgumentParser(description="Run prompt testing experiments")

    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://127.0.0.1:8000/answer",
        help="API endpoint URL",
    )

    parser.add_argument(
        "--test-file",
        type=str,
        default="./prompt_variations.csv",
        help="Path to CSV file with test cases",
    )

    parser.add_argument(
        "--results-dir",
        type=str,
        default="./experiment_results",
        help="Directory to store results",
    )

    parser.add_argument(
        "--experiment",
        type=str,
        choices=["category", "intent", "cross", "all"],
        default="all",
        help="Type of experiment to run",
    )

    args = parser.parse_args()

    # Initialize the framework
    framework = PromptTestingFramework(
        endpoint=args.endpoint, results_dir=args.results_dir, verbose=True
    )

    # Run the selected experiment
    if args.experiment == "category" or args.experiment == "all":
        print("\n=== Running Category Experiments ===")
        category_results = run_category_experiments(
            framework, args.test_file, args.results_dir
        )
        export_results_to_csv(
            category_results, f"{args.results_dir}/category_results.csv"
        )

    if args.experiment == "intent" or args.experiment == "all":
        print("\n=== Running Intent Type Experiments ===")
        intent_results = run_intent_type_experiments(
            framework, args.test_file, args.results_dir
        )
        export_results_to_csv(intent_results, f"{args.results_dir}/intent_results.csv")

    if args.experiment == "cross" or args.experiment == "all":
        print("\n=== Running Cross Experiments ===")
        cross_results, results_matrix = run_cross_experiments(
            framework, args.test_file, args.results_dir
        )
        export_results_to_csv(cross_results, f"{args.results_dir}/cross_results.csv")

        # Save matrix as CSV
        results_matrix.to_csv(f"{args.results_dir}/cross_matrix.csv")

    print(f"\nAll experiments completed. Results saved to {args.results_dir}/")


if __name__ == "__main__":
    main()
