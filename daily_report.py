import requests
import pandas as pd
from datetime import datetime

url = "https://tirupati.emunicipal.ap.gov.in/ptis/report/dailyCollection"

payload = {
    "fromDate": (datetime.now().strftime("%d/%m/%Y")),
    "toDate": (datetime.now().strftime("%d/%m/%Y")),
    "collectionMode": "",
    "collectionOperator": "",
    "status": "",
    "revenueWard": "Revenue Ward No 18"
}

headers = {
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8"
}

def fetch_and_generate_report():
    response = requests.post(url, data=payload, headers=headers)
    print(type(response), response.content)
    if response.status_code == 200:
        response_json = response.json()
        if len(response_json) == 0:
            print("No data available for the selected date.")
            return None
        
        df = pd.DataFrame(response_json)
        
        df.rename(columns={
            "id": "Id",
            "receiptNumber": "Receipt Number",
            "cityName": "City",
            "totalAmount": "Total Amount",
            "consumerName": "Consumer Name",
            "consumerCode": "Consumer Code",
            "secretariatWard": "Secretariat Ward",
            "receiptDate": "Receipt Date"
        }, inplace=True)
        
        df['Date'] = pd.to_datetime(df['Receipt Date']).dt.date
        df['Consumer Info'] = df['Consumer Name'].str.strip() + " (" + df['Consumer Code'] + ")"
        
        grouped_df = df.groupby(['Date', 'Secretariat Ward']).agg(
            Total_Amount=('Total Amount', 'sum'),
            No_of_Bills=('Receipt Number', 'count'),
            Consumers=('Consumer Info', lambda x: ', '.join(x))
        ).reset_index()
        
        excel_file = f"Daily_Collection_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            grouped_df.to_excel(writer, sheet_name='Summary', index=False)
            df.to_excel(writer, sheet_name='Details', index=False)
        
        print(f"Report generated successfully: {excel_file}")
        return excel_file
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None

if __name__ == "__main__":
    fetch_and_generate_report()
