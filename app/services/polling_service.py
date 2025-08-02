import json


class PollingService:
    def __init__(self, polling_interval: int = 60):
        self.polling_interval = polling_interval

    def poll(self, user_input_link: str, req_type: str):
    
        specific_key = f"{req_type}_{user_input_link[-30:]}"

        # Load the saved data
        with open('data.json', 'r') as f:
            all_data = json.load(f)

        print('all_data', all_data)
        
        # Retrieve by specific key
        if specific_key in all_data:
            data = all_data[specific_key]
            print("Key found:", specific_key)
            print("Data:", data)
            # Here you can implement the logic to process the data as needed
            if req_type == "REPO":
                output_json = {
                    "data": [],
                    "req_type": data["req_type"],
                    "status": data["status"],
                    "user_input_link": data["user_input_link"],
                    "pdf_link": data.get("pdf_content", None)
                }

                if "data" not in data or "files" not in data["data"]:
                    return {"error": "No files found in the data.", data: ""}

                for file in data["data"]["files"]:
                    analysis = file["analysis"]
                    analysis["path"] = file["path"]
                    output_json["data"].append(analysis)

                return output_json
            else: 
                return data    
        else:
            return {"error": "Key not found in the data."}