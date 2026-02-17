"""
AWS Lambda handler for Finalis Contract Engine API.

This is the production entry point for AWS Lambda deployments.
For local development, use main.py (Flask app) instead.
"""

import json
import logging
import os

from engine import DealProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment (dev, staging, prod)
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# Initialize processor (reused across warm invocations)
processor = DealProcessor()

# CORS headers for API Gateway
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def lambda_handler(event, context):
    """
    Main Lambda entry point.

    Handles API Gateway events for:
    - GET /health
    - POST /process_deal
    - OPTIONS (CORS preflight)
    """
    # Handle CORS preflight
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    # Get path (supports both REST API and HTTP API formats)
    path = event.get("path") or event.get("rawPath", "")

    # Route to appropriate handler
    if path == "/health" and http_method == "GET":
        return handle_health()
    elif path == "/process_deal" and http_method == "POST":
        return handle_process_deal(event)
    elif path == "/api" and http_method == "GET":
        return handle_api_info()
    else:
        return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "Not found", "path": path})}


def handle_health():
    """Health check endpoint."""
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"status": "healthy", "environment": ENVIRONMENT}),
    }


def handle_api_info():
    """API information endpoint."""
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(
            {
                "status": "ok",
                "message": "Finalis Commission Calculator API",
                "version": "3.0",
                "environment": ENVIRONMENT,
                "runtime": "AWS Lambda",
                "endpoints": {"process_deal": "/process_deal [POST]", "health": "/health [GET]"},
            }
        ),
    }


def handle_process_deal(event):
    """Process a deal through the Finalis contract engine."""
    try:
        # Parse request body
        body = event.get("body", "")
        if isinstance(body, str):
            if not body:
                return {
                    "statusCode": 400,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({"error": "No input data provided", "status": "failed"}),
                }
            # Handle base64 encoded body (API Gateway)
            if event.get("isBase64Encoded"):
                import base64

                body = base64.b64decode(body).decode("utf-8")
            input_data = json.loads(body)
        else:
            input_data = body

        # Log request
        deal_name = input_data.get("deal", {}).get("deal_name", "Unknown")
        logger.info(f"Processing deal: {deal_name}")

        # Process through engine
        result = processor.process_from_dict(input_data)

        logger.info(f"Deal processed successfully: {deal_name}")

        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(result)}

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": f"Invalid JSON: {str(e)}", "status": "failed"}),
        }

    except (ValueError, KeyError, TypeError) as e:
        # Validation errors from engine (missing fields, invalid types, etc.)
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": f"Validation error: {str(e)}", "status": "validation_failed"}),
        }

    except Exception as e:
        # Unexpected errors - log details but return generic message to avoid information disclosure
        logger.error(f"Unexpected processing error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "An unexpected error occurred during processing", "status": "failed"}),
        }
