import json
import requests

class JsonRpcProxy:
  def __init__(self, url, user, password, path=""):
    self.url = url
    self.path = path
    self.user = user
    self.password = password

  def send(self, method, params):
    headers = {'content-type': 'application/json'}
    # Log the request
    print(f"Sending request {self.path}: {method} {params}")

    data = {
      "jsonrpc": "1.0",
      "id": "curltest",
      "method": method,
      "params": params
    }
    
    try:
      response = requests.post(self.url+self.path, headers=headers, data=json.dumps(data), auth=(self.user, self.password))
      # Log the response
      # print(f"Received response: {response.status_code} {response.json()}")
      if 'error' in response.json() and response.json()['error'] is not None:
        raise Exception(response.json()['error'])
      return response.json()['result']
    except Exception as e:
      # Log the error
      print(f"Error occurred: {e}")
      raise e
    
  def proxy(self, path):
    return JsonRpcProxy(self.url, self.user, self.password, path)