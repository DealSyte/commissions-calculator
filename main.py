from flask import Flask, request, jsonify
from flask_cors import CORS
from engine import DealProcessor
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all routes (permite que N8N y Lovable llamen a la API)
CORS(app)

# Initialize the deal processor
processor = DealProcessor()


@app.route("/", methods=["GET"])
def healthcheck():
    return jsonify({
        "status": "ok",
        "message": "Finalis Engine API running",
        "version": "3.0",
        "endpoints": {
            "process_deal": "/process_deal [POST]",
            "health": "/health [GET]"
        }
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check for monitoring"""
    return jsonify({"status": "healthy"}), 200


@app.route("/process_deal", methods=["POST"])
def process_deal():
    """
    Process a deal through the Finalis contract engine
    """
    try:
        # Get input data
        input_data = request.get_json(force=True)

        if not input_data:
            return jsonify({
                "error": "No input data provided",
                "status": "failed"
            }), 400

        # Log request
        deal_name = input_data.get('deal', {}).get('deal_name', 'Unknown')
        logger.info(f"Processing deal: {deal_name}")

        # Process through engine
        result = processor.process_from_dict(input_data)

        logger.info(f"Deal processed successfully: {deal_name}")

        return jsonify(result), 200

    except ValueError as e:
        # Validation errors from engine
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "validation_failed"
        }), 400

    except Exception as e:
        # Unexpected errors
        logger.error(f"Processing error: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), 500


@app.route("/process", methods=["POST"])
def process_legacy():
    """Legacy endpoint - redirects to /process_deal"""
    return process_deal()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)