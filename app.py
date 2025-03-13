from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import datetime
import os

app = Flask(__name__)

# Function to fetch data from municipal website
def fetch_data(from_date, to_date):
    try:
        session = requests.Session()
        url = "https://tirupati.emunicipal.ap.gov.in/ptis/report/dailyCollection"
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': '_csrf'})['content']
        csrf_header = soup.find('meta', {'name': '_csrf_header'})['content']

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
            "revenueWard": "Revenue Ward No  18"
        }

        response = session.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch data: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# Process data for display
def process_data(data):
    if "error" in data:
        return {"error": data["error"]}
    
    grouped_data = defaultdict(lambda: {"count": 0, "totalAmount": 0, "owners": []})
    for entry in data:
        ward = entry['secretariatWard']
        grouped_data[ward]['count'] += 1
        grouped_data[ward]['totalAmount'] += entry['totalAmount']
        grouped_data[ward]['owners'].append(f"{entry['consumerName']} ({entry['consumerCode']})")
    
    return dict(grouped_data)

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
    
    return render_template_string(HTML_TEMPLATE, date_options=date_options)

# API endpoint to fetch data
@app.route('/fetch-data', methods=['POST'])
def get_data():
    selected_date = request.form.get('date')
    if not selected_date:
        return jsonify({"error": "Date is required"})
    
    data = fetch_data(selected_date, selected_date)
    processed_data = process_data(data)
    return jsonify(processed_data)

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
        <div id="loading" class="loading">Loading data...</div>
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
                body: formData
            })
            .then(response => response.json())
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
                        <td>${ward}</td>
                        <td>${details.count}</td>
                        <td>₹${details.totalAmount.toFixed(2)}</td>
                        <td>${details.owners.join('<br>')}</td>
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)