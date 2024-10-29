from flask import Flask, request, Response
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TARGET_URL = "http://18.142.2.45:8080"


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    # Construct the target URL
    url = f"{TARGET_URL}/{path}"

    # Forward the request headers
    headers = {key: value for key, value in request.headers.items()}
    headers['Host'] = '18.142.2.45:8080'  # Set the host header

    try:
        # Make the request to the target server
        response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=5  # 5 seconds timeout
        )

        # Create the response
        proxy_response = Response(
            response.content,
            status=response.status_code
        )

        # Forward the response headers
        for key, value in response.headers.items():
            if key.lower() not in ['content-length', 'content-encoding', 'transfer-encoding']:
                proxy_response.headers[key] = value

        # Add CORS headers
        proxy_response.headers['Access-Control-Allow-Origin'] = '*'
        proxy_response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        proxy_response.headers['Access-Control-Allow-Headers'] = '*'

        return proxy_response

    except requests.exceptions.RequestException as e:
        return {
            'error': 'Proxy Error',
            'message': str(e)
        }, 500


@app.errorhandler(404)
def not_found(e):
    return {
        'error': 'Not Found',
        'message': 'The requested resource was not found'
    }, 404


@app.errorhandler(500)
def server_error(e):
    return {
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)