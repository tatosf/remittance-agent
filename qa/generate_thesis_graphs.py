#!/usr/bin/env python3
# Copyright (c) 2024 Blockchain at Berkeley.  All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec

# Set the style for the plots
plt.style.use("ggplot")
sns.set_theme(style="whitegrid")
COLORS = {
    "swap": "#9C27B0",  # Purple
    "transfer": "#2196F3",  # Blue
    "remittance": "#FF9800",  # Orange
}


def load_experiment_data(results_dir):
    """
    Load experiment data from CSV files.

    Args:
        results_dir: Directory containing experiment results

    Returns:
        cross_matrix: DataFrame with the accuracy matrix
        cross_results: DataFrame with detailed experiment results
    """
    cross_matrix_path = os.path.join(results_dir, "cross_matrix.csv")
    cross_results_path = os.path.join(results_dir, "cross_results.csv")

    cross_matrix = pd.read_csv(cross_matrix_path, index_col=0)
    cross_results = pd.read_csv(cross_results_path)

    return cross_matrix, cross_results


def generate_intent_boxplots(cross_results, output_dir):
    """
    Generate boxplots for accuracy and response time by intent type.

    Args:
        cross_results: DataFrame with experiment results
        output_dir: Directory to save the output
    """
    # Create a figure with two subplots
    fig, axes = plt.subplots(2, 1, figsize=(10, 12))

    # Process data for plotting
    data = {}

    for intent_type in ["swap", "transfer", "remittance"]:
        # Filter results for this intent type
        intent_data = cross_results[
            cross_results["experiment"].str.endswith(f"_{intent_type}")
        ]

        # Store accuracy and response time data
        data[intent_type] = {
            "accuracy": intent_data["accuracy"].values * 100,  # Convert to percentage
            "response_time": intent_data["avg_response_time"].values,
        }

    # Plot accuracy boxplot
    accuracy_data = [
        data[intent]["accuracy"] for intent in ["swap", "transfer", "remittance"]
    ]
    axes[0].boxplot(
        accuracy_data,
        patch_artist=True,
        boxprops=dict(facecolor=COLORS["swap"]),
        medianprops=dict(color="black"),
    )
    axes[0].set_title("Accuracy by Intent Type", fontsize=16)
    axes[0].set_ylabel("Accuracy (%)", fontsize=14)
    axes[0].set_ylim(0, 110)
    axes[0].set_xticklabels(["Swap", "Transfer", "Remittance"], fontsize=12)

    # Add individual data points for accuracy
    for i, intent in enumerate(["swap", "transfer", "remittance"]):
        x = np.random.normal(i + 1, 0.04, size=len(data[intent]["accuracy"]))
        axes[0].scatter(
            x, data[intent]["accuracy"], alpha=0.6, c=COLORS[intent], edgecolors="white"
        )

    # Plot response time boxplot
    response_data = [
        data[intent]["response_time"] for intent in ["swap", "transfer", "remittance"]
    ]
    axes[1].boxplot(
        response_data,
        patch_artist=True,
        boxprops=dict(facecolor=COLORS["remittance"]),
        medianprops=dict(color="black"),
    )
    axes[1].set_title("Response Time by Intent Type", fontsize=16)
    axes[1].set_ylabel("Response Time (seconds)", fontsize=14)
    axes[1].set_xticklabels(["Swap", "Transfer", "Remittance"], fontsize=12)

    # Add individual data points for response time
    for i, intent in enumerate(["swap", "transfer", "remittance"]):
        x = np.random.normal(i + 1, 0.04, size=len(data[intent]["response_time"]))
        axes[1].scatter(
            x,
            data[intent]["response_time"],
            alpha=0.6,
            c=COLORS[intent],
            edgecolors="white",
        )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "intent_boxplots.png"), dpi=300)
    plt.close()


def generate_overall_accuracy_charts(cross_matrix, cross_results, output_dir):
    """
    Generate charts showing overall accuracy across all categories and intents.

    Args:
        cross_matrix: DataFrame with the accuracy matrix
        cross_results: DataFrame with experiment results
        output_dir: Directory to save the output
    """
    # Calculate overall accuracy
    total_tests = cross_results["total_tests"].sum()
    correct_tests = cross_results["correct_tests"].sum()
    overall_accuracy = (correct_tests / total_tests) * 100

    # Create figure with 2 subplots
    fig = plt.figure(figsize=(15, 12))
    gs = GridSpec(2, 2, figure=fig)

    # Pie chart for overall accuracy
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.pie(
        [overall_accuracy, 100 - overall_accuracy],
        explode=(0.1, 0),
        labels=["Correct", "Incorrect"],
        colors=["#4CAF50", "#F44336"],
        autopct="%1.1f%%",
        startangle=90,
        shadow=True,
    )
    ax1.set_title("Overall Accuracy", fontsize=16)

    # Bar chart for accuracy by intent type
    ax2 = fig.add_subplot(gs[0, 1])
    intent_accuracy = cross_matrix.mean() * 100
    ax2.bar(
        intent_accuracy.index,
        intent_accuracy.values,
        color=[COLORS[i] for i in intent_accuracy.index],
    )
    ax2.set_title("Average Accuracy by Intent Type", fontsize=16)
    ax2.set_ylabel("Accuracy (%)", fontsize=14)
    ax2.set_ylim(0, 100)

    for i, v in enumerate(intent_accuracy.values):
        ax2.text(i, v + 3, f"{v:.1f}%", ha="center", fontsize=12)

    # Heatmap for accuracy by category and intent
    ax3 = fig.add_subplot(gs[1, :])
    sns.heatmap(
        cross_matrix * 100,
        annot=True,
        cmap="YlGnBu",
        fmt=".1f",
        linewidths=0.5,
        ax=ax3,
        vmin=0,
        vmax=100,
        cbar_kws={"label": "Accuracy (%)"},
    )
    ax3.set_title("Accuracy by Category and Intent Type", fontsize=16)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "overall_accuracy.png"), dpi=300)
    plt.close()


def generate_error_analysis(cross_matrix, cross_results, output_dir):
    """
    Generate visualizations for error analysis.

    Args:
        cross_matrix: DataFrame with the accuracy matrix
        cross_results: DataFrame with experiment results
        output_dir: Directory to save the output
    """
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))

    # Filter for failed tests
    failed_data = cross_results[cross_results["accuracy"] < 1]

    # Count failures by intent type
    intent_failures = {}
    for intent in ["swap", "transfer", "remittance"]:
        intent_failures[intent] = sum(
            1 for exp in failed_data["experiment"] if exp.endswith(f"_{intent}")
        )

    # Plot failures by intent type
    ax1.bar(
        intent_failures.keys(),
        intent_failures.values(),
        color=[COLORS[i] for i in intent_failures.keys()],
    )
    ax1.set_title("Error Count by Intent Type", fontsize=16)
    ax1.set_ylabel("Number of Errors", fontsize=14)

    for i, (intent, count) in enumerate(intent_failures.items()):
        ax1.text(i, count + 0.1, str(count), ha="center", fontsize=12)

    # Count failures by category
    category_failures = {}
    for index, row in cross_matrix.iterrows():
        category_failures[index] = sum(1 for val in row if val < 1)

    # Sort categories by error count
    sorted_categories = sorted(
        category_failures.items(), key=lambda x: x[1], reverse=True
    )
    categories = [c[0] for c in sorted_categories]
    counts = [c[1] for c in sorted_categories]

    # Plot failures by category
    ax2.barh(categories, counts, color="#E91E63")
    ax2.set_title("Error Count by Prompt Category", fontsize=16)
    ax2.set_xlabel("Number of Errors", fontsize=14)

    for i, count in enumerate(counts):
        if count > 0:
            ax2.text(count + 0.1, i, str(count), va="center", fontsize=12)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "error_analysis.png"), dpi=300)
    plt.close()


def main():
    """Main function to generate all thesis graphs."""
    # Set paths
    results_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "experiment_results"
    )
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "thesis_graphs"
    )

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    cross_matrix, cross_results = load_experiment_data(results_dir)

    # Generate visualizations
    generate_intent_boxplots(cross_results, output_dir)
    generate_overall_accuracy_charts(cross_matrix, cross_results, output_dir)
    generate_error_analysis(cross_matrix, cross_results, output_dir)

    print(f"All thesis graphs generated and saved to {output_dir}")


if __name__ == "__main__":
    main()
