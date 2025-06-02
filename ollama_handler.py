# ollama_handler.py

# ollama_handler.py

import subprocess
import requests
import os
import logging
import time
import traceback
from utils import logger

# Global flag to indicate whether to use CLI or API
# Define this at the module level
USE_API = True  # Default to API as it's more reliable

def is_ollama_running():
    """
    Check if Ollama is running and accessible
    
    Returns:
        Boolean indicating whether Ollama is running
    """
    global USE_API  # Declare global at the start of the function
    
    # Try API first
    try:
        logger.debug("Checking if Ollama API is running")
        response = requests.get('http://localhost:11434/api/version', timeout=2)
        if response.status_code == 200:
            USE_API = True
            logger.info("Ollama API is running")
            return True
    except requests.exceptions.RequestException as e:
        logger.debug(f"Ollama API check failed: {str(e)}")
    
    # Fall back to CLI check
    try:
        logger.debug("Checking if Ollama CLI is accessible")
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, 
                              text=True, 
                              timeout=3)
        if result.returncode == 0:
            USE_API = False
            logger.info("Ollama CLI is accessible")
            return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug(f"Ollama CLI check failed: {str(e)}")
    
    logger.warning("Ollama is not running or not accessible")
    return False
def query_ollama_api(prompt: str, model: str = "deepseek-r1:1.5b"):
    """
    Query Ollama using REST API
    
    Args:
        prompt: The text prompt to send to Ollama
        model: The Ollama model to use
        
    Returns:
        String response from Ollama
    """
    url = 'http://localhost:11434/api/generate'
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False
    }
    
    try:
        logger.debug(f"Sending API request to Ollama with model: {model}")
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        end_time = time.time()
        
        logger.debug(f"Ollama API request completed in {end_time - start_time:.2f} seconds")
        return response.json().get('response', 'No response from model.')
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if len(error_msg) > 500:
            error_msg = error_msg[:497] + "..."
        logger.error(f"Ollama API error: {error_msg}")
        raise Exception(f"Ollama API Error: {error_msg}")

def query_ollama_cli(prompt: str, model: str = "deepseek-r1:1.5b"):
    """
    Query Ollama using CLI
    
    Args:
        prompt: The text prompt to send to Ollama
        model: The Ollama model to use
        
    Returns:
        String response from Ollama
    """
    try:
        logger.debug(f"Using CLI to query Ollama with model: {model}")
        start_time = time.time()
        
        process = subprocess.Popen(
            ['ollama', 'run', model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        response, error = process.communicate(input=prompt, timeout=60)
        end_time = time.time()
        
        logger.debug(f"Ollama CLI request completed in {end_time - start_time:.2f} seconds")
        
        if error and error.strip():
            # Truncate long error messages
            if len(error) > 500:
                error = error[:497] + "..."
            logger.error(f"Ollama CLI error: {error}")
            raise Exception(f"Ollama CLI Error: {error}")
            
        return response.strip()
        
    except subprocess.TimeoutExpired:
        logger.error("Ollama CLI request timed out")
        raise Exception("Ollama request timed out. The operation took too long to complete.")
    except FileNotFoundError:
        logger.error("Ollama executable not found")
        raise Exception("Ollama is not installed or not in PATH. Please install Ollama.")
    except Exception as e:
        logger.error(f"Unexpected error with Ollama CLI: {str(e)}")
        if "Ollama Error" in str(e):
            raise e
        raise Exception(f"Unexpected error: {str(e)}")

def query_ollama(prompt: str, model: str = "deepseek-r1:1.5b", max_retries=2):
    """
    Main function to query Ollama, using either API or CLI
    
    Args:
        prompt: The text prompt to send to Ollama
        model: The Ollama model to use
        max_retries: Maximum number of retry attempts
        
    Returns:
        String response from Ollama
    """
    global USE_API  # Declare global at the start
    
    logger.info(f"Querying Ollama with prompt length: {len(prompt)} chars")
    
    # Check if Ollama is running
    if not is_ollama_running():
        logger.error("Ollama is not running or installed")
        raise Exception("Ollama is not running or installed. Please start Ollama service.")
    
    # Truncate prompt if it's too long
    if len(prompt) > 4000:
        logger.warning(f"Truncating prompt from {len(prompt)} to 4000 characters")
        prompt = prompt[:3997] + "..."
    
    # Track retry attempts
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            # Use API by default, fall back to CLI if needed
            if USE_API:
                try:
                    logger.debug("Attempting to use Ollama API")
                    return query_ollama_api(prompt, model)
                except Exception as api_error:
                    logger.warning(f"API call failed: {str(api_error)}. Falling back to CLI.")
                    last_error = api_error
                    # If API fails, try CLI as fallback within the same retry attempt
                    USE_API = False  # Switch to CLI for this and future attempts
                    return query_ollama_cli(prompt, model)
            else:
                logger.debug("Using Ollama CLI directly")
                return query_ollama_cli(prompt, model)
                
        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count <= max_retries:
                wait_time = retry_count * 2  # Exponential backoff: 2s, 4s
                logger.warning(f"Retrying Ollama query in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                break
    
    # If we get here, all retries failed
    logger.error(f"All Ollama query attempts failed after {max_retries} retries.")
    if last_error:
        logger.error(f"Last error: {str(last_error)}")
        logger.error(traceback.format_exc())
        raise last_error
    else:
        raise Exception("Failed to query Ollama after multiple attempts")
