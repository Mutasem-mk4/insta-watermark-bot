import json

def parse():
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be']
    data = None
    for enc in encodings:
        try:
            with open('services.json', 'r', encoding=enc) as f:
                data = f.read()
            # Clean up potential BOM or null bytes
            data = data.replace('\x00', '')
            services = json.loads(data)
            
            found = False
            for item in services:
                service = item.get('service', {})
                if service.get('name') == 'insta-watermark-bot':
                    res = {
                        "id": service.get('id'),
                        "status": service.get('status'),
                        "envVars": service.get('envVars', [])
                    }
                    print(json.dumps(res, indent=2))
                    found = True
                    break
            if not found:
                print("Service not found")
            return
        except Exception:
            continue
    print("Failed to parse with any encoding")

parse()
