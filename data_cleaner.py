# data_cleaner.py

import pandas as pd
import os
import time
import traceback
from ollama_handler import query_ollama
from utils import logger

def clean_and_summarize(file_path: str, output_dir: str = "outputs"):
    """
    Clean and summarize a CSV file using pandas and Ollama AI
    
    Args:
        file_path: Path to the CSV file
        output_dir: Directory to save the cleaned file
        
    Returns:
        Tuple of (cleaned_file_path, cleaning_summary)
    """
    logger.info(f"Starting processing of file: {file_path}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Check file size (limit to 100MB to prevent memory issues)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 100:
        logger.error(f"File too large: {file_size_mb:.1f} MB")
        raise ValueError(f"File is too large ({file_size_mb:.1f} MB). Maximum size for processing is 100 MB.")
    
    # Read CSV file safely
    try:
        # Try different encodings if default fails
        encodings = ['utf-8', 'latin1', 'cp1252']
        df = None
        last_error = None
        
        for encoding in encodings:
            try:
                logger.debug(f"Trying to read CSV with encoding: {encoding}")
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                break
            except Exception as e:
                last_error = e
                logger.debug(f"Failed to read with encoding {encoding}: {str(e)}")
                continue
                
        if df is None:
            error_msg = f"Failed to read CSV with any encoding: {str(last_error)}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        # Check if dataframe is empty
        if df.empty:
            logger.error("CSV file is empty")
            raise ValueError("The CSV file is empty.")
            
        # Check if dataframe is too large
        if df.shape[0] > 1000000 or df.shape[1] > 100:
            logger.error(f"Dataset too large: {df.shape[0]} rows × {df.shape[1]} columns")
            raise ValueError(f"Dataset too large: {df.shape[0]} rows × {df.shape[1]} columns. Maximum is 1,000,000 rows and 100 columns.")
            
    except pd.errors.EmptyDataError:
        logger.error("CSV file is empty")
        raise ValueError("The CSV file is empty.")
    except pd.errors.ParserError:
        logger.error("Unable to parse CSV file")
        raise ValueError("Unable to parse the CSV file. Please check the file format.")
    except Exception as e:
        error_msg = f"Error reading CSV file: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Get basic statistics
    try:
        logger.info("Generating dataset statistics")
        # Generate comprehensive statistics
        numeric_stats = df.describe().to_string() if not df.select_dtypes(include=['number']).empty else "No numeric columns"
        non_numeric_stats = df.describe(include=['object']).to_string() if not df.select_dtypes(include=['object']).empty else "No non-numeric columns"
        missing_values = df.isnull().sum().to_string() if df.isnull().sum().sum() > 0 else "No missing values"
        duplicate_rows = f"Found {df.duplicated().sum()} duplicate rows" if df.duplicated().sum() > 0 else "No duplicate rows"
        
        summary = f"""Dataset Summary:
Shape: {df.shape[0]} rows × {df.shape[1]} columns
Columns: {', '.join(df.columns.tolist())}

Numeric Statistics:
{numeric_stats}

Non-numeric Statistics:
{non_numeric_stats}

Missing Values:
{missing_values}

{duplicate_rows}
"""
        logger.debug("Statistics generated successfully")
    except Exception as e:
        logger.warning(f"Could not generate complete statistics: {str(e)}")
        summary = f"Could not generate complete statistics: {str(e)}\nBasic info: {df.shape[0]} rows × {df.shape[1]} columns"
    
    # Create prompt for Ollama
    ollama_response = "AI analysis not available - Ollama connection failed"
    try:
        logger.info("Querying Ollama for data cleaning recommendations")
        # Limit sample size to prevent oversized prompts
        sample = df.head(5).to_string()
        columns_info = "\n".join([f"{col}: {df[col].dtype}" for col in df.columns])
        
        prompt = f"""You are a data cleaning assistant. Clean the following dataset:

Dataset Info:
{df.shape[0]} rows × {df.shape[1]} columns
Column types:
{columns_info}

Sample data:
{sample}

Identify and handle missing values, invalid entries, or duplicates if present.
Return only the steps you would perform and why."""

        # Query Ollama for cleaning suggestions
        ollama_response = query_ollama(prompt)
        logger.info("Received response from Ollama")
    except Exception as e:
        logger.error(f"Error querying Ollama: {str(e)}")
        logger.error(traceback.format_exc())
        # Provide a fallback if Ollama fails
        ollama_response = f"Could not get AI suggestions: {str(e)}\nPerforming basic cleaning only."
    
    # Basic cleaning based on assumptions
    try:
        logger.info("Performing data cleaning")
        # Store original row and column counts
        original_rows = df.shape[0]
        original_cols = df.shape[1]
        cleaning_steps = []
        
        # Remove duplicates
        if df.duplicated().sum() > 0:
            duplicate_count = df.duplicated().sum()
            df = df.drop_duplicates()
            cleaning_steps.append(f"Removed {duplicate_count} duplicate rows")
            logger.info(f"Removed {duplicate_count} duplicate rows")
            
        # Handle missing values
        # For columns with < 10% missing values, drop those rows
        # For columns with >= 10% missing values, fill with appropriate values
        for column in df.columns:
            missing_pct = df[column].isnull().mean() * 100
            if missing_pct > 0:
                if missing_pct < 10:
                    rows_before = df.shape[0]
                    df = df.dropna(subset=[column])
                    rows_dropped = rows_before - df.shape[0]
                    if rows_dropped > 0:
                        cleaning_steps.append(f"Dropped {rows_dropped} rows with missing values in column '{column}'")
                        logger.info(f"Dropped {rows_dropped} rows with missing values in column '{column}'")
                else:
                    # Fill numeric columns with median, categorical with mode
                    if pd.api.types.is_numeric_dtype(df[column]):
                        median_value = df[column].median()
                        df[column] = df[column].fillna(median_value)
                        cleaning_steps.append(f"Filled {int(missing_pct * original_rows / 100)} missing values in numeric column '{column}' with median ({median_value})")
                        logger.info(f"Filled missing values in numeric column '{column}' with median")
                    else:
                        mode_value = df[column].mode()[0] if not df[column].mode().empty else "Unknown"
                        df[column] = df[column].fillna(mode_value)
                        cleaning_steps.append(f"Filled {int(missing_pct * original_rows / 100)} missing values in non-numeric column '{column}' with mode ({mode_value})")
                        logger.info(f"Filled missing values in non-numeric column '{column}' with mode")
        
        # Additional cleaning steps summary
        cleaning_summary = "\n".join(cleaning_steps) if cleaning_steps else "No automatic cleaning steps were necessary"
        
        # Generate timestamp for filename
        timestamp = int(time.time())
        base_filename = os.path.basename(file_path)
        output_file = os.path.join(output_dir, f"cleaned_{timestamp}_{base_filename}")
        
        # Save cleaned file
        logger.info(f"Saving cleaned file to {output_file}")
        df.to_csv(output_file, index=False)
        
        # Combine AI suggestions with actual cleaning steps
        full_summary = f"""
{ollama_response}

ACTUAL CLEANING PERFORMED:
{cleaning_summary}

RESULTS:
Original dataset: {original_rows} rows × {original_cols} columns
Cleaned dataset: {df.shape[0]} rows × {df.shape[1]} columns
"""
        logger.info(f"Cleaning complete. Original: {original_rows} rows, Cleaned: {df.shape[0]} rows")
        
        return output_file, full_summary
    except Exception as e:
        logger.error(f"Error during data cleaning: {str(e)}")
        logger.error(traceback.format_exc())
        raise Exception(f"Error during data cleaning: {str(e)}")
