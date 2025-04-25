# app.py
from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import datetime
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Function to fetch data from municipal website
def fetch_data(from_date, to_date):
    try:
        logger.info(f"Fetching data for date range: {from_date} to {to_date}")
        session = requests.Session()
        url = "https://tirupati.emunicipal.ap.gov.in/ptis/report/dailyCollection"
        
        # First request to get CSRF token
        logger.info("Making initial request to get CSRF token")
        response = session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        csrf_token = soup.find('meta', {'name': '_csrf'})
        if not csrf_token:
            logger.error("CSRF token not found in response")
            return {"error": "CSRF token not found"}
            
        csrf_token = csrf_token['content']
        
        csrf_header = soup.find('meta', {'name': '_csrf_header'})
        if not csrf_header:
            logger.error("CSRF header not found in response")
            return {"error": "CSRF header not found"}
            
        csrf_header = csrf_header['content']
        
        logger.info(f"CSRF token obtained: {csrf_token[:10]}...")

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            csrf_header: csrf_token,
            "x-requested-with": "XMLHttpRequest"
        }

        data = {
            "fromDate": from_date,
            "toDate": to_date,
            "collectionMode": "",
            "collectionOperator": "",
            "status": "",
            "revenueWard": ""
        }

        logger.info("Making POST request to fetch collection data")
        response = session.post(url, headers=headers, data=data, timeout=15)
        
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"Successfully fetched data. Items: {len(result) if isinstance(result, list) else 'Not a list'}")
                return result
            except Exception as e:
                logger.error(f"Error parsing JSON response: {str(e)}")
                return {"error": f"Failed to parse response: {str(e)}"}
        else:
            logger.error(f"Request failed with status code: {response.status_code}")
            return {"error": f"Failed to fetch data: {response.status_code}"}
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return {"error": "Request timed out. The server is taking too long to respond."}
    except requests.exceptions.ConnectionError:
        logger.error("Connection error")
        return {"error": "Connection error. Unable to connect to the municipal website."}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": str(e)}

# Process data for display
def process_data(data):
    if isinstance(data, dict) and "error" in data:
        logger.error(f"Error in data: {data['error']}")
        return {"error": data["error"]}
    
    if not isinstance(data, list):
        logger.error(f"Unexpected data format: {type(data)}")
        return {"error": "Unexpected data format received from server"}
    
    if not data:
        logger.info("No data found for the selected date")
        return {}
    
    try:
        grouped_data = defaultdict(lambda: {"count": 0, "totalAmount": 0, "owners": []})
        for entry in data:
            ward = entry.get('secretariatWard', 'Unknown')
            grouped_data[ward]['count'] += 1
            grouped_data[ward]['totalAmount'] += entry.get('totalAmount', 0)
            consumer_name = entry.get('consumerName', 'Unknown')
            consumer_code = entry.get('consumerCode', 'Unknown')
            grouped_data[ward]['owners'].append(f"{consumer_name} ({consumer_code})")
        
        logger.info(f"Processed data into {len(grouped_data)} groups")
        return dict(grouped_data)
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return {"error": f"Error processing data: {str(e)}"}

# Route for main page
@app.route('/')
def index():
    # Generate date options for the last 30 days
    today = datetime.datetime.now()
    date_options = []
    for i in range(30):
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime('%d/%m/%Y')
        date_options.append(date_str)
    
    logger.info("Rendering index page")
    return render_template_string(HTML_TEMPLATE, date_options=date_options)

# API endpoint to fetch data
@app.route('/fetch-data', methods=['POST'])
def get_data():
    selected_date = request.form.get('date')
    if not selected_date:
        logger.warning("No date provided in request")
        return jsonify({"error": "Date is required"})
    
    logger.info(f"Fetching data for date: {selected_date}")
    data = fetch_data(selected_date, selected_date)
    processed_data = process_data(data)
    return jsonify(processed_data)

# Health check endpoint for Render
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

# HTML template with embedded CSS and JavaScript
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Daily Collection Report</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #2980b9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }
        .error {
            color: red;
            padding: 10px;
            background-color: #ffebee;
            border-radius: 4px;
            margin-top: 10px;
            display: none;
        }
        .results-container {
            margin-top: 30px;
        }
        .owner-cell {
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Daily Collection Report</h1>
        <div class="form-group">
            <label for="date-select">Select Date:</label>
            <select id="date-select">
                <option value="">-- Select a date --</option>
                {% for date in date_options %}
                <option value="{{ date }}">{{ date }}</option>
                {% endfor %}
            </select>
        </div>
        <button id="fetch-btn">Fetch Report</button>
        <div id="loading" class="loading">Loading data... This may take a few moments.</div>
        <div id="error" class="error"></div>
        <div id="results" class="results-container"></div>
    </div>

    <script>
        document.getElementById('fetch-btn').addEventListener('click', function() {
            const selectedDate = document.getElementById('date-select').value;
            if (!selectedDate) {
                showError('Please select a date');
                return;
            }

            // Show loading indicator
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('results').innerHTML = '';

            // Fetch data
            const formData = new FormData();
            formData.append('date', selectedDate);

            fetch('/fetch-data', {
                method: 'POST',
                body: formData,
                timeout: 60000 // 60 second timeout
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                
                if (data.error) {
                    showError(data.error);
                    return;
                }

                displayResults(data, selectedDate);
            })
            .catch(error => {
                document.getElementById('loading').style.display = 'none';
                showError('An error occurred: ' + error.message);
                console.error('Error:', error);
            });
        });

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }

        function displayResults(data, date) {
            const resultsDiv = document.getElementById('results');
            let html = `<h2>Collection Report for ${date}</h2>`;
            
            if (Object.keys(data).length === 0) {
                html += '<p>No data found for this date.</p>';
                resultsDiv.innerHTML = html;
                return;
            }

            html += `
                <table>
                    <thead>
                        <tr>
                            <th>Secretariat Ward</th>
                            <th>Number of Bills</th>
                            <th>Total Amount</th>
                            <th>Owner Details</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            for (const ward in data) {
                const details = data[ward];
                html += `
                    <tr>
                        <td>${ward || 'Unknown'}</td>
                        <td>${details.count}</td>
                        <td>₹${details.totalAmount.toFixed(2)}</td>
                        <td class="owner-cell">${details.owners.join('<br>')}</td>
                    </tr>
                `;
            }

            html += `
                    </tbody>
                </table>
            `;

            resultsDiv.innerHTML = html;
        }
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 10000))
    # Bind to 0.0.0.0 to make the app accessible externally
    app.run(host="0.0.0.0", port=port)
