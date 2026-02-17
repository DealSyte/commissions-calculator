"""Tests for AWS Lambda handler."""

import json

from lambda_handler import lambda_handler


class TestLambdaHandler:
    """Test the Lambda handler routes and responses."""

    def test_health_check(self):
        """GET /health returns healthy status."""
        event = {"httpMethod": "GET", "path": "/health"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"

    def test_api_info(self):
        """GET /api returns API information."""
        event = {"httpMethod": "GET", "path": "/api"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"
        assert "endpoints" in body

    def test_cors_preflight(self):
        """OPTIONS requests return CORS headers."""
        event = {"httpMethod": "OPTIONS", "path": "/process_deal"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in response["headers"]
        assert "Access-Control-Allow-Methods" in response["headers"]

    def test_not_found(self):
        """Unknown paths return 404."""
        event = {"httpMethod": "GET", "path": "/unknown"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 404

    def test_process_deal_success(self):
        """POST /process_deal processes a valid deal."""
        payload = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.03,
                "accumulated_success_fees_before_this_deal": 0,
                "contract_start_date": "2025-01-01",
                "is_pay_as_you_go": False,
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0,
                "future_subscription_fees": [],
                "deferred_schedule": [],
            },
            "deal": {
                "deal_name": "Lambda Test Deal",
                "success_fees": 1000000,
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": True,
                "external_retainer": 0,
                "has_external_retainer": False,
                "include_retainer_in_fees": False,
            },
        }

        event = {"httpMethod": "POST", "path": "/process_deal", "body": json.dumps(payload)}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "calculations" in body
        assert "updated_contract_state" in body

    def test_process_deal_empty_body(self):
        """POST /process_deal with empty body returns 400."""
        event = {"httpMethod": "POST", "path": "/process_deal", "body": ""}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_process_deal_invalid_json(self):
        """POST /process_deal with invalid JSON returns 400."""
        event = {"httpMethod": "POST", "path": "/process_deal", "body": "not valid json"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_process_deal_validation_error(self):
        """POST /process_deal with invalid data returns 400."""
        payload = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 1.5,  # Invalid: > 1.0
                "contract_start_date": "2025-01-01",
            },
            "state": {},
            "deal": {"success_fees": 1000000, "deal_date": "2025-06-15"},
        }

        event = {"httpMethod": "POST", "path": "/process_deal", "body": json.dumps(payload)}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "validation_failed"

    def test_http_api_format(self):
        """Supports HTTP API v2 event format."""
        event = {"requestContext": {"http": {"method": "GET"}}, "rawPath": "/health"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
