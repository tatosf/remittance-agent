# Brinco Prompt Testing Framework

This directory contains a comprehensive framework for testing and evaluating the natural language processing capabilities of the Brinco txt2txn system. The framework allows for systematic evaluation of different prompt types, intent categories, and parameter extraction accuracy.

## Overview

The prompt testing framework enables:

1. Testing how different prompt variations affect NLP accuracy
2. Analyzing performance across different transaction types (swap, transfer, remittance)
3. Measuring parameter extraction accuracy
4. Generating visualizations and reports for thesis inclusion
5. Comparing results across different experiment configurations

## Files

- `experiment_framework.py`: Core testing framework with metrics gathering and analysis
- `prompt_variations.csv`: Test cases with different prompt formulations categorized by type
- `run_experiments.py`: Script to run experiments with different configurations
- `test_cases.csv`: Basic test cases for the system (legacy)
- `try_test_cases.py`: Simple test runner (legacy)

## Prompt Categories

The test framework includes the following prompt categories:

- `direct`: Simple, direct commands ("swap 1 DAI for USDC")
- `polite`: Commands with polite phrases ("please swap 1 DAI for USDC")
- `conversational`: Natural language requests ("I want to swap 1 DAI for USDC")
- `question`: Interrogative requests ("Can you swap 1 DAI for USDC?")
- `synonyms`: Using synonyms for key actions ("exchange 1 DAI for USDC")
- `reordered`: Reordering parameters ("to 0x123... send 5 USDC")
- `symbols`: Using symbols and abbreviations ("DAI → USDC, 1 token")
- `verbose`: Lengthy, detailed requests
- `technical`: Function-like syntax ("swap(DAI, USDC, 1)")
- `implicit`: Implied intent without explicit commands
- `spelled_number`: Numbers spelled out as words ("one DAI")
- `decimal_number`: Numbers with decimal points ("1.5 DAI")
- `missing_amount`: Omitting the amount parameter
- `missing_chain`: Omitting the chain parameter
- `ambiguous_amount`: Using vague quantity descriptors
- `approximate_amount`: Using approximation terms

## Usage

### Basic Usage

To run all experiments with default settings:

```bash
python run_experiments.py
```

### Specific Experiment Types

To run only category-based experiments:

```bash
python run_experiments.py --experiment category
```

Available experiment types:

- `category`: Test performance across different prompt categories
- `intent`: Test performance across different intent types
- `cross`: Cross-test categories and intent types
- `all`: Run all experiment types (default)

### Custom Configuration

You can customize the endpoint and test file:

```bash
python run_experiments.py --endpoint "http://localhost:8000/answer" --test-file "./prompt_variations.csv" --results-dir "./my_results"
```

## Creating Custom Test Cases

To create your own test cases, follow the format in `prompt_variations.csv`:

```
Prompt,Expected Intent,Category
"swap 1 DAI for USDC on sepolia","{ ""transaction_type"": ""swap"", ""response"": { ""fromAsset"": ""0xB4F...""","direct"
```

Where:

- `Prompt`: The test prompt text
- `Expected Intent`: JSON representation of the expected API response
- `Category`: Categorization of the prompt type

## Analyzing Results

Results are saved in the specified results directory (default: `./experiment_results`):

- CSV files with metrics summaries
- PNG visualizations comparing different dimensions
- Detailed JSON files with per-test results
- Markdown reports with analysis

## Visualizations

The framework generates several visualizations:

1. Bar charts comparing accuracy across prompt categories
2. Bar charts comparing accuracy across intent types
3. Heatmaps showing accuracy for category-intent combinations
4. Error type breakdowns

## Using in Your Thesis

The results and visualizations from this framework are designed to be directly includable in research papers and theses. The markdown reports can be converted to LaTeX, and the visualizations are publication-quality.

## Requirements

- Python 3.7+
- pandas
- matplotlib
- tqdm
- requests

## Adding to the Framework

To extend the framework with new features:

1. Add new categories to `PROMPT_CATEGORIES` in `run_experiments.py`
2. Create new test cases in the appropriate CSV file
3. Add new visualization functions as needed
4. Extend the `PromptTestingFramework` class in `experiment_framework.py`
