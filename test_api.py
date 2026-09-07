"""Smoke-test the configured OpenRouter API and model.

Usage:
    $env:OPENROUTER_API_KEY = 'your-key'
    python test_api.py

Set OPENROUTER_API_KEY and optionally OPENROUTER_MODEL before running.
"""
import os
import sys

import requests

API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b').strip()
ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'


def main():
    if not API_KEY:
        print('ERROR: OPENROUTER_API_KEY is not set.')
        return 2
    payload = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content': 'Reply with exactly: API test successful.'}],
        'temperature': 0,
        'max_tokens': 30,
    }
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': os.getenv('APP_BASE_URL', 'http://localhost:5000'),
        'X-Title': '3D ULPIN Demo API Test',
    }
    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=40)
    except requests.RequestException as error:
        print(f'ERROR: Could not reach OpenRouter: {error}')
        return 1
    if response.status_code >= 400:
        print(f'ERROR: OpenRouter returned HTTP {response.status_code}: {response.text[:1000]}')
        return 1
    try:
        result = response.json()
        message = result['choices'][0]['message']['content']
    except (ValueError, KeyError, IndexError, TypeError):
        print(f'ERROR: Unexpected response: {response.text[:1000]}')
        return 1
    print(f'Model: {MODEL}')
    print(f'Response: {message}')
    print('API test successful.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
