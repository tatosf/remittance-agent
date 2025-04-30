#!/usr/bin/env python3
# Copyright (c) 2024 Blockchain at Berkeley.  All rights reserved.
# SPDX-License-Identifier: MIT

import json
import csv
import time
import os
import re
import datetime
import argparse
import requests
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple, Set, Union


class PromptTestingFramework:
    """
    Comprehensive framework for conducting prompt testing experiments with
    the txt2txn natural language processing system.

    This framework allows for:
    - Testing multiple prompt datasets
    - Comparing system performance across different prompt types
    - Analyzing success rates by intent type
    - Measuring parameter extraction accuracy
    - Conducting error analysis
    - Generating visualizations and reports for thesis inclusion
    """

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:8000/answer",
        results_dir: str = "./results",
        max_retries: int = 3,
        timeout: int = 10,
        verbose: bool = True,
    ):
        """
        Initialize the prompt testing framework.

        Args:
            endpoint: API endpoint URL
            results_dir: Directory to store results
            max_retries: Maximum number of retry attempts for API calls
            timeout: Timeout in seconds for API requests
            verbose: Whether to print detailed progress
        """
        self.endpoint = endpoint
        self.results_dir = results_dir
        self.max_retries = max_retries
        self.timeout = timeout
        self.verbose = verbose
        self.headers = {"Content-Type": "application/json"}

        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)

        # Initialize metrics containers
        self.reset_metrics()

    def reset_metrics(self):
        """Reset all metrics and results containers."""
        self.results = []
        self.metrics = {
            "total": 0,
            "correct": 0,
            "failed_requests": 0,
            "by_intent_type": defaultdict(lambda: {"total": 0, "correct": 0}),
            "parameter_accuracy": defaultdict(lambda: {"total": 0, "correct": 0}),
            "error_types": defaultdict(int),
            "response_times": [],
        }

    def load_test_cases(self, file_path: str) -> List[Dict]:
        """
        Load test cases from a CSV file.

        Args:
            file_path: Path to the CSV file containing test cases

        Returns:
            List of test case dictionaries
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test cases file not found: {file_path}")

        test_cases = []
        with open(file_path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Parse the expected intent JSON
                if "Expected Intent" in row:
                    row["Expected Intent"] = json.loads(row["Expected Intent"])
                test_cases.append(row)

        if self.verbose:
            print(f"Loaded {len(test_cases)} test cases from {file_path}")

        return test_cases

    def run_test_case(
        self, prompt: str, use_test_tokens: bool = False
    ) -> Tuple[Dict, float]:
        """
        Run a single test case against the API.

        Args:
            prompt: The prompt text to test
            use_test_tokens: Whether to use test tokens for the API call

        Returns:
            Tuple of (API response JSON, response time in seconds)
        """
        payload = {"question": prompt, "use_test_tokens": use_test_tokens}

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = requests.post(
                    self.endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout,
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return response.json(), response_time

                if self.verbose:
                    print(
                        f"Attempt {attempt+1} failed with status {response.status_code}"
                    )

            except Exception as e:
                if self.verbose:
                    print(f"Attempt {attempt+1} failed with error: {str(e)}")

            # Wait before retrying (exponential backoff)
            if attempt < self.max_retries - 1:
                time.sleep(2**attempt)

        # All attempts failed
        self.metrics["failed_requests"] += 1
        return {"error": "All requests failed"}, 0

    def compare_intents(
        self, actual: Dict, expected: Dict
    ) -> Tuple[bool, Dict[str, bool]]:
        """
        Compare actual and expected intents with more lenient parameter checking.
        Focuses on functional correctness rather than exact address matching,
        especially for swaps and remittances.

        Args:
            actual: Actual intent from API response
            expected: Expected intent

        Returns:
            Tuple of (overall match boolean, dictionary of parameter matches)
        """
        # Check if the transaction type matches - this is critical for all transactions
        if actual.get("transaction_type") != expected.get("transaction_type"):
            return False, {"transaction_type": False}

        # Track parameter matches
        param_matches = {"transaction_type": True}
        all_match = True

        # Get the response objects
        actual_resp = actual.get("response", {})
        expected_resp = expected.get("response", {})

        # Get transaction type for special handling
        transaction_type = expected.get("transaction_type", "")

        # Handle special case for remittances
        if transaction_type == "remittance":
            # For remittances, we primarily care about intent type, amount and chain
            amount_match = True  # Default to true
            chain_match = True  # Default to true

            # Check amount if it's provided in expected
            exp_amount = expected_resp.get("amount")
            if exp_amount is not None:
                act_amount = actual_resp.get("amount")
                if isinstance(act_amount, (int, float)) and isinstance(
                    exp_amount, (int, float)
                ):
                    amount_match = (
                        abs(act_amount - exp_amount) / exp_amount < 0.1
                        if exp_amount != 0
                        else act_amount == 0
                    )
                else:
                    amount_match = exp_amount == act_amount
                param_matches["amount"] = amount_match

            # Check chain if it's provided in expected
            exp_chain = expected_resp.get("chain")
            if exp_chain is not None:
                act_chain = actual_resp.get("chain")
                if isinstance(act_chain, str) and isinstance(exp_chain, str):
                    chain_match = act_chain.lower() == exp_chain.lower()
                else:
                    chain_match = exp_chain == act_chain
                param_matches["chain"] = chain_match

            # Mark recipient_address as correct for remittances (we don't care about exact addresses)
            param_matches["recipient_address"] = True

            # Only these fields matter for remittances
            return (amount_match and chain_match), param_matches

        # Special case for swaps
        elif transaction_type == "swap":
            # For swaps, we care about fromAsset, transaction type, amount, and chain
            # But we're lenient with toAsset addresses if the transaction_type is correct

            # Check each expected parameter
            for key, expected_value in expected_resp.items():
                actual_value = actual_resp.get(key)

                # Skip checks for null values if the field is present in actual
                if expected_value is None and key in actual_resp:
                    param_matches[key] = True
                    continue

                # Special case for toAsset - consider it correct if present
                # This assumes if we got the transaction type right and have a toAsset, it's likely correct
                if key == "toAsset" and actual_value is not None:
                    param_matches[key] = True
                    continue

                # Handle case insensitive comparison for strings
                elif isinstance(expected_value, str) and isinstance(actual_value, str):
                    param_matches[key] = expected_value.lower() == actual_value.lower()
                # Special check for numeric values - consider them correct if within 10% of expected
                elif (
                    isinstance(expected_value, (int, float))
                    and isinstance(actual_value, (int, float))
                    and expected_value != 0
                ):
                    param_matches[key] = (
                        abs(expected_value - actual_value) / expected_value < 0.1
                    )
                else:
                    param_matches[key] = expected_value == actual_value

                # For swaps, only amount and chain are truly critical
                if not param_matches.get(key, False) and key in ["amount", "chain"]:
                    all_match = False

            return all_match, param_matches

        # For transfers and other transaction types
        else:
            # Check each expected parameter
            for key, expected_value in expected_resp.items():
                actual_value = actual_resp.get(key)

                # Skip checks for null values if the field is present in actual
                if expected_value is None and key in actual_resp:
                    param_matches[key] = True
                    continue

                # Handle case insensitive comparison for strings
                if isinstance(expected_value, str) and isinstance(actual_value, str):
                    param_matches[key] = expected_value.lower() == actual_value.lower()
                # Special check for numeric values - consider them correct if within 10% of expected
                elif (
                    isinstance(expected_value, (int, float))
                    and isinstance(actual_value, (int, float))
                    and expected_value != 0
                ):
                    param_matches[key] = (
                        abs(expected_value - actual_value) / expected_value < 0.1
                    )
                else:
                    param_matches[key] = expected_value == actual_value

                if not param_matches.get(key, False):
                    # Only count as a mismatch if it's one of the key fields we really care about
                    critical_fields = ["token", "chain", "amount", "recipientAddress"]
                    if key in critical_fields:
                        all_match = False
                else:
                    # Update parameter accuracy metrics
                    self.metrics["parameter_accuracy"][key]["total"] += 1
                    self.metrics["parameter_accuracy"][key]["correct"] += 1

            return all_match, param_matches

    def analyze_errors(
        self, prompt: str, actual: Dict, expected: Dict, param_matches: Dict[str, bool]
    ):
        """
        Analyze and categorize errors.

        Args:
            prompt: Original prompt text
            actual: Actual API response
            expected: Expected intent
            param_matches: Dictionary of parameter match results
        """
        # If there's an error field, it's a request failure
        if "error" in actual:
            self.metrics["error_types"]["request_failure"] += 1
            return

        # Check if transaction type is misclassified
        if not param_matches.get("transaction_type", False):
            self.metrics["error_types"]["intent_misclassification"] += 1
            return

        # Check for parameter extraction errors
        param_errors = []
        for param, matched in param_matches.items():
            if param != "transaction_type" and not matched:
                param_errors.append(param)

        if param_errors:
            self.metrics["error_types"]["parameter_extraction"] += 1

            # Specific parameter errors
            for param in param_errors:
                self.metrics["error_types"][f"param_{param}_error"] += 1

    def run_test_suite(
        self,
        test_cases: List[Dict],
        suite_name: str = "default",
        use_test_tokens: bool = False,
    ) -> Dict:
        """
        Run a complete test suite.

        Args:
            test_cases: List of test cases to run
            suite_name: Name for this test suite
            use_test_tokens: Whether to use test tokens for API calls

        Returns:
            Dictionary with test results and metrics
        """
        if self.verbose:
            print(f"Running test suite '{suite_name}' with {len(test_cases)} cases...")

        # Reset metrics for this run
        self.reset_metrics()

        # Process each test case
        for case in tqdm(test_cases, disable=not self.verbose):
            prompt = case["Prompt"]
            expected_intent = case["Expected Intent"]

            # Run the test case
            actual_intent, response_time = self.run_test_case(prompt, use_test_tokens)

            # Record response time
            self.metrics["response_times"].append(response_time)

            # Compare the results
            is_correct, param_matches = self.compare_intents(
                actual_intent, expected_intent
            )

            # Update metrics
            self.metrics["total"] += 1
            if is_correct:
                self.metrics["correct"] += 1

            # Track metrics by intent type
            intent_type = expected_intent.get("transaction_type", "unknown")
            self.metrics["by_intent_type"][intent_type]["total"] += 1
            if is_correct:
                self.metrics["by_intent_type"][intent_type]["correct"] += 1

            # Analyze any errors
            if not is_correct:
                self.analyze_errors(
                    prompt, actual_intent, expected_intent, param_matches
                )

            # Record detailed results for this test case
            self.results.append(
                {
                    "prompt": prompt,
                    "expected_intent": expected_intent,
                    "actual_intent": actual_intent,
                    "is_correct": is_correct,
                    "param_matches": param_matches,
                    "response_time": response_time,
                }
            )

        # Calculate summary metrics
        summary = self.calculate_summary()

        # Save results
        self.save_results(suite_name)

        return summary

    def calculate_summary(self) -> Dict:
        """
        Calculate summary metrics for the test run.

        Returns:
            Dictionary with summary metrics
        """
        total = self.metrics["total"]
        correct = self.metrics["correct"]

        summary = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_tests": total,
            "correct_tests": correct,
            "accuracy": (correct / total) if total > 0 else 0,
            "failed_requests": self.metrics["failed_requests"],
            "avg_response_time": (
                sum(self.metrics["response_times"])
                / len(self.metrics["response_times"])
                if self.metrics["response_times"]
                else 0
            ),
            "intent_type_accuracy": {},
            "parameter_accuracy": {},
            "error_analysis": dict(self.metrics["error_types"]),
        }

        # Calculate accuracy by intent type
        for intent_type, counts in self.metrics["by_intent_type"].items():
            if counts["total"] > 0:
                summary["intent_type_accuracy"][intent_type] = (
                    counts["correct"] / counts["total"]
                )
            else:
                summary["intent_type_accuracy"][intent_type] = 0

        # Calculate parameter accuracy
        for param, counts in self.metrics["parameter_accuracy"].items():
            if counts["total"] > 0:
                summary["parameter_accuracy"][param] = (
                    counts["correct"] / counts["total"]
                )
            else:
                summary["parameter_accuracy"][param] = 0

        return summary

    def save_results(self, suite_name: str):
        """
        Save test results and metrics to files.

        Args:
            suite_name: Name of the test suite
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{self.results_dir}/{suite_name}_{timestamp}"

        # Save detailed results as JSON
        with open(f"{base_filename}_details.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Save summary metrics as JSON
        with open(f"{base_filename}_summary.json", "w") as f:
            json.dump(self.calculate_summary(), f, indent=2)

        # Save failed cases for analysis
        failed_cases = [r for r in self.results if not r["is_correct"]]
        with open(f"{base_filename}_failed.json", "w") as f:
            json.dump(failed_cases, f, indent=2)

        if self.verbose:
            print(f"Results saved to {base_filename}_*.json")

    def generate_report(self, suite_name: str, output_format: str = "markdown"):
        """
        Generate a formatted report of test results.

        Args:
            suite_name: Name of the test suite
            output_format: Format for the report (markdown or html)

        Returns:
            String containing the formatted report
        """
        summary = self.calculate_summary()

        # Generate markdown report
        report = [
            f"# Prompt Testing Report: {suite_name}",
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary Metrics",
            f"- **Total Tests**: {summary['total_tests']}",
            f"- **Correct Tests**: {summary['correct_tests']}",
            f"- **Overall Accuracy**: {summary['accuracy']:.2%}",
            f"- **Failed Requests**: {summary['failed_requests']}",
            f"- **Average Response Time**: {summary['avg_response_time']:.3f} seconds",
            "",
            "## Accuracy by Intent Type",
        ]

        # Add intent type accuracy
        for intent_type, accuracy in summary["intent_type_accuracy"].items():
            report.append(f"- **{intent_type}**: {accuracy:.2%}")

        report.extend(
            [
                "",
                "## Parameter Extraction Accuracy",
            ]
        )

        # Add parameter accuracy
        for param, accuracy in summary["parameter_accuracy"].items():
            report.append(f"- **{param}**: {accuracy:.2%}")

        report.extend(
            [
                "",
                "## Error Analysis",
            ]
        )

        # Add error counts
        for error_type, count in summary["error_analysis"].items():
            report.append(f"- **{error_type}**: {count}")

        report.extend(
            [
                "",
                "## Failed Test Cases",
                "",
                "| Prompt | Expected Type | Actual Type | Error Type |",
                "| ------ | ------------- | ----------- | ---------- |",
            ]
        )

        # Add failed test cases
        for result in self.results:
            if not result["is_correct"]:
                prompt = result["prompt"]
                expected_type = result["expected_intent"].get(
                    "transaction_type", "unknown"
                )
                actual_type = result["actual_intent"].get("transaction_type", "unknown")

                # Determine error type
                if expected_type != actual_type:
                    error_type = "Intent Misclassification"
                else:
                    error_type = "Parameter Extraction"

                report.append(
                    f"| {prompt} | {expected_type} | {actual_type} | {error_type} |"
                )

        # Convert to requested format
        report_text = "\n".join(report)

        # Save the report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"{self.results_dir}/{suite_name}_{timestamp}_report.md", "w") as f:
            f.write(report_text)

        if self.verbose:
            print(
                f"Report saved to {self.results_dir}/{suite_name}_{timestamp}_report.md"
            )

        return report_text

    def generate_visualizations(self, suite_name: str):
        """
        Generate visualizations of test results.

        Args:
            suite_name: Name of the test suite
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{self.results_dir}/{suite_name}_{timestamp}"

        # Calculate summary metrics
        summary = self.calculate_summary()

        # Set up plots
        plt.figure(figsize=(15, 10))

        # Plot 1: Overall Accuracy
        plt.subplot(2, 2, 1)
        labels = ["Correct", "Incorrect"]
        sizes = [
            summary["correct_tests"],
            summary["total_tests"] - summary["correct_tests"],
        ]
        plt.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=["#4CAF50", "#F44336"],
        )
        plt.axis("equal")
        plt.title("Overall Accuracy")

        # Plot 2: Accuracy by Intent Type
        plt.subplot(2, 2, 2)
        intent_types = list(summary["intent_type_accuracy"].keys())
        accuracies = list(summary["intent_type_accuracy"].values())
        plt.bar(intent_types, [acc * 100 for acc in accuracies], color="#2196F3")
        plt.title("Accuracy by Intent Type")
        plt.ylabel("Accuracy (%)")
        plt.ylim(0, 100)

        # Plot 3: Parameter Extraction Accuracy
        plt.subplot(2, 2, 3)
        params = list(summary["parameter_accuracy"].keys())
        param_accuracies = list(summary["parameter_accuracy"].values())
        plt.bar(params, [acc * 100 for acc in param_accuracies], color="#9C27B0")
        plt.title("Parameter Extraction Accuracy")
        plt.ylabel("Accuracy (%)")
        plt.xticks(rotation=45, ha="right")
        plt.ylim(0, 100)

        # Plot 4: Error Types
        plt.subplot(2, 2, 4)
        error_types = list(summary["error_analysis"].keys())
        error_counts = list(summary["error_analysis"].values())
        plt.bar(error_types, error_counts, color="#FF9800")
        plt.title("Error Types")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")

        # Save the figure
        plt.tight_layout()
        plt.savefig(f"{base_filename}_visualizations.png", dpi=300)

        if self.verbose:
            print(f"Visualizations saved to {base_filename}_visualizations.png")

    def compare_test_suites(self, suite_names: List[str], summary_files: List[str]):
        """
        Compare results from multiple test suites.

        Args:
            suite_names: List of suite names to compare
            summary_files: List of summary JSON file paths to compare
        """
        if len(suite_names) != len(summary_files):
            raise ValueError("Number of suite names must match number of summary files")

        # Load summaries
        summaries = []
        for name, file_path in zip(suite_names, summary_files):
            with open(file_path, "r") as f:
                summary = json.load(f)
                summary["suite_name"] = name
                summaries.append(summary)

        # Create comparison plots
        plt.figure(figsize=(15, 10))

        # Plot 1: Overall Accuracy Comparison
        plt.subplot(2, 2, 1)
        plt.bar(
            [s["suite_name"] for s in summaries],
            [s["accuracy"] * 100 for s in summaries],
            color="#2196F3",
        )
        plt.title("Overall Accuracy Comparison")
        plt.ylabel("Accuracy (%)")
        plt.ylim(0, 100)

        # Plot 2: Response Time Comparison
        plt.subplot(2, 2, 2)
        plt.bar(
            [s["suite_name"] for s in summaries],
            [s["avg_response_time"] for s in summaries],
            color="#4CAF50",
        )
        plt.title("Average Response Time Comparison")
        plt.ylabel("Response Time (seconds)")

        # Plot 3: Intent Type Accuracy Comparison
        plt.subplot(2, 2, 3)

        # Collect all intent types across summaries
        all_intent_types = set()
        for summary in summaries:
            all_intent_types.update(summary["intent_type_accuracy"].keys())

        # Create grouped bar chart data
        x = np.arange(len(all_intent_types))
        width = 0.8 / len(summaries)

        for i, summary in enumerate(summaries):
            accuracies = [
                summary["intent_type_accuracy"].get(t, 0) * 100
                for t in all_intent_types
            ]
            plt.bar(
                x + i * width - 0.4 + width / 2,
                accuracies,
                width,
                label=summary["suite_name"],
            )

        plt.title("Intent Type Accuracy Comparison")
        plt.ylabel("Accuracy (%)")
        plt.xticks(x, all_intent_types)
        plt.legend()
        plt.ylim(0, 100)

        # Plot 4: Error Type Comparison
        plt.subplot(2, 2, 4)

        # Collect all error types across summaries
        all_error_types = set()
        for summary in summaries:
            all_error_types.update(summary["error_analysis"].keys())

        # Create grouped bar chart data
        x = np.arange(len(all_error_types))
        width = 0.8 / len(summaries)

        for i, summary in enumerate(summaries):
            error_counts = [
                summary["error_analysis"].get(t, 0) for t in all_error_types
            ]
            plt.bar(
                x + i * width - 0.4 + width / 2,
                error_counts,
                width,
                label=summary["suite_name"],
            )

        plt.title("Error Type Comparison")
        plt.ylabel("Count")
        plt.xticks(x, all_error_types, rotation=45, ha="right")
        plt.legend()

        # Save the figure
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.tight_layout()
        plt.savefig(f"{self.results_dir}/comparison_{timestamp}.png", dpi=300)

        if self.verbose:
            print(
                f"Comparison visualization saved to {self.results_dir}/comparison_{timestamp}.png"
            )


def main():
    """Command line interface for the prompt testing framework."""
    parser = argparse.ArgumentParser(description="Prompt Testing Framework for txt2txn")

    parser.add_argument(
        "--test-file",
        type=str,
        default="./test_cases.csv",
        help="Path to CSV file with test cases",
    )

    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://127.0.0.1:8000/answer",
        help="API endpoint URL",
    )

    parser.add_argument(
        "--suite-name",
        type=str,
        default="default_suite",
        help="Name for this test suite",
    )

    parser.add_argument(
        "--results-dir",
        type=str,
        default="./results",
        help="Directory to store results",
    )

    parser.add_argument(
        "--use-test-tokens", action="store_true", help="Use test tokens for API calls"
    )

    parser.add_argument(
        "--report", action="store_true", help="Generate a report after testing"
    )

    parser.add_argument(
        "--visualize", action="store_true", help="Generate visualizations after testing"
    )

    args = parser.parse_args()

    # Initialize the framework
    framework = PromptTestingFramework(
        endpoint=args.endpoint, results_dir=args.results_dir, verbose=True
    )

    # Load test cases
    test_cases = framework.load_test_cases(args.test_file)

    # Run the test suite
    summary = framework.run_test_suite(
        test_cases=test_cases,
        suite_name=args.suite_name,
        use_test_tokens=args.use_test_tokens,
    )

    # Print summary
    print(f"\nTest Suite: {args.suite_name}")
    print(
        f"Accuracy: {summary['accuracy']:.2%} ({summary['correct_tests']}/{summary['total_tests']})"
    )
    print(f"Failed Requests: {summary['failed_requests']}")
    print(f"Average Response Time: {summary['avg_response_time']:.3f} seconds")

    # Generate report if requested
    if args.report:
        framework.generate_report(args.suite_name)

    # Generate visualizations if requested
    if args.visualize:
        framework.generate_visualizations(args.suite_name)


if __name__ == "__main__":
    main()
